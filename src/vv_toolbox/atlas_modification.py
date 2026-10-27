"""Local, illustrative atlas deformation in original source units (assumed mm).

This preserves topology and anchor collars, not anatomical validity or freedom
from collisions. Research use only, not for clinical decision.
"""
from copy import deepcopy

import numpy as np
from scipy.spatial import cKDTree
from .atlas_edit_checks import inspect_edit, AtlasEditCheckFailure


DEFAULT_PARAMETERS = dict(radius_scale=1.0, tortuosity=0.0, torsion_deg=0.0)
PARAMETER_LIMITS = dict(radius_scale=(0.5, 2.0), tortuosity=(-1.0, 1.0),
                        torsion_deg=(-180.0, 180.0))


def validate_parameters(parameters):
    """Return complete finite parameters; reject unknown keys and bool values."""
    if not isinstance(parameters, dict) or set(parameters) - set(DEFAULT_PARAMETERS):
        raise ValueError('Unknown atlas modification parameters')
    result = DEFAULT_PARAMETERS.copy()
    for key, value in parameters.items():
        if isinstance(value, (bool, str)):
            raise ValueError(f'{key} must be a finite number')
        try:
            value = float(value)
        except (TypeError, ValueError, OverflowError) as error:
            raise ValueError(f'{key} must be a finite number') from error
        low, high = PARAMETER_LIMITS[key]
        if not np.isfinite(value) or not low <= value <= high:
            raise ValueError(f'{key} must be in [{low}, {high}]')
        result[key] = value
    return result


def _smoothstep(value):
    value = np.clip(value, 0.0, 1.0)
    return value * value * (3.0 - 2.0 * value)


def _anchor_weight(points, anchors, collars, transition_widths=None, *, blend='minimum'):
    # A common spatial collar for mesh and paths protects all incident branches.
    weight = np.ones(len(points))
    for anchor, collar, width in zip(anchors, collars, collars if transition_widths is None else transition_widths):
        distance = np.linalg.norm(points - anchor, axis=1)
        local=_smoothstep((distance - collar) / width)
        weight = weight*local if blend=='product' else np.minimum(weight,local)
    return weight


def _polyline_radial(points, paths):
    """Vector from the nearest source segment, without connecting separate paths."""
    nearest = np.zeros_like(points)
    best = np.full(len(points), np.inf)
    for path in paths:
        for start, end in zip(path[:-1], path[1:]):
            direction = end - start
            length2 = float(direction @ direction)
            if length2 <= 1e-24:
                continue
            t = np.clip((points - start) @ direction / length2, 0., 1.)
            projection = start + t[:, None] * direction
            distance2 = np.sum((points - projection) ** 2, axis=1)
            replace = distance2 < best
            nearest[replace] = projection[replace]
            best[replace] = distance2[replace]
    if not np.isfinite(best).all():
        raise ValueError('No nonzero source segments')
    return points - nearest


def _compact_field(points, samples, shifts, tangents, scales, tree, support, radial_vectors=None):
    """Fixed-support C2 weights; reject unsupported queries instead of extrapolating."""
    if not np.isfinite(support) or support <= 0:
        raise ValueError('Positive finite field support required')
    field = np.zeros_like(points, dtype=float)
    scale_delta = np.zeros(len(points))
    for row, neighbors in enumerate(tree.query_ball_point(points, support)):
        indices = np.asarray(sorted(neighbors), dtype=int)
        delta = points[row] - samples[indices]
        q = np.linalg.norm(delta, axis=1) / support
        weights = np.maximum(1. - q, 0.) ** 4 * (4. * q + 1.)
        total = weights.sum()
        if total <= 1e-12:
            raise ValueError('Insufficient compact field support')
        weights /= total
        radial = delta - np.sum(delta * tangents[indices], axis=1)[:, None] * tangents[indices]
        field[row] = np.sum(weights[:, None] *
                            (shifts[indices] + radial * (scales[indices] - 1.)[:, None]), axis=0)
        scale_delta[row] = np.dot(weights, scales[indices] - 1.)
        if radial_vectors is not None:
            field[row] = np.sum(weights[:, None] * shifts[indices], axis=0) + radial_vectors[row] * scale_delta[row]
    return field, scale_delta


def _integrate_field(points, evaluate, steps):
    """RK4 stationary velocity integration; not a discrete-mesh validity proof."""
    output = points.copy()
    log_scale = np.zeros(len(points))
    dt = 1. / steps
    def velocity(v):
        mapped, scale = evaluate(v)
        return mapped - v, scale - 1.
    for _ in range(steps):
        a, sa = velocity(output)
        b, sb = velocity(output + .5 * dt * a)
        c, sc = velocity(output + .5 * dt * b)
        d, sd = velocity(output + dt * c)
        output += dt / 6. * (a + 2*b + 2*c + d)
        log_scale += dt / 6. * (sa + 2*sb + 2*sc + sd)
    return output, np.exp(log_scale)


def deform_part(part, edges, parameters, *, protected_regions=(), anchor_blend='minimum',
                field_version='v1', radial_mode='tangent', integration_steps=0,
                field_support_mm=None):
    """Return a deformed mesh dict and edge list without editing input.

    Radius is a local radial scale with fixed junction/end collars. Tortuosity
    adjusts deviation from each endpoint chord; positive values add a smooth
    bend even to straight paths. Torsion rotates that deviation around the chord
    by a tapered angle, in degrees. Closed paths have no unique chord and their
    shape is preserved (radius can still change). Nearest-path blending is an
    approximation, especially at crowded branches; no remeshing is performed.
    Always call against original geometry, never the previous edited result.
    Experimental v2 evaluates paths and vertices with one spatial field. It does
    not guarantee injectivity or agreement of reported radii with cross sections.
    """
    params = validate_parameters(parameters)
    if anchor_blend not in ('minimum','product'):
        raise ValueError('Unknown anchor blend')
    if field_version not in ('v1', 'v2', 'v3'):
        raise ValueError('Unknown deformation field version')
    if radial_mode not in ('tangent', 'polyline') or (radial_mode == 'polyline' and field_version != 'v3'):
        raise ValueError('Polyline radial mode requires v3')
    if (type(integration_steps) is not int or integration_steps < 0 or integration_steps > 256
            or (integration_steps and (field_version != 'v3' or radial_mode != 'polyline'))):
        raise ValueError('Integration requires v3/polyline and 1 to 256 integer steps')
    if field_support_mm is not None and (
            field_version != 'v3' or isinstance(field_support_mm, bool)
            or not isinstance(field_support_mm, (int, float))
            or not np.isfinite(field_support_mm) or field_support_mm <= 0):
        raise ValueError('Explicit field support must be positive finite and use v3')
    protected=[]
    for region in protected_regions:
        center=np.asarray(region['center_mm'],dtype=float)
        radius=region['radius_mm']
        if (center.shape!=(3,) or not np.isfinite(center).all() or
                isinstance(radius,bool) or not isinstance(radius,(int,float)) or
                not np.isfinite(radius) or radius<=0):
            raise ValueError('Finite protected centers and positive radii required')
        protected.append(dict(center_mm=center.tolist(),radius_mm=float(radius)))
        if 'transition_width_mm' in region:
            width=region['transition_width_mm']
            if isinstance(width,bool) or not isinstance(width,(int,float)) or not np.isfinite(width) or width<=0:
                raise ValueError('Positive finite transition width required')
            protected[-1]['transition_width_mm']=float(width)
    vertices = np.asarray(part['vertices'], dtype=float)
    if vertices.ndim != 2 or vertices.shape[1] != 3 or not len(vertices) or not np.isfinite(vertices).all():
        raise ValueError('Atlas vertices must be finite Nx3 coordinates')
    if not edges:
        raise ValueError('No centerline available for this atlas part')
    validated = []
    for edge in edges:
        points = np.asarray(edge['points'], dtype=float)
        radii = np.asarray(edge['radii'], dtype=float)
        if (edge.get('part_id') != part['id'] or points.ndim != 2 or points.shape[1] != 3
                or len(points) < 2 or radii.shape != (len(points),)
                or not np.isfinite(points).all() or not np.isfinite(radii).all()
                or np.any(radii <= 0)):
            raise ValueError('Invalid or mismatched atlas centerline')
        lengths = np.r_[0., np.cumsum(np.linalg.norm(np.diff(points, axis=0), axis=1))]
        if lengths[-1] <= 1e-9:
            raise ValueError('Centerline has zero length')
        validated.append((points, radii, lengths))
    new_part, new_edges = deepcopy(part), deepcopy(edges)
    new_part['modification'] = dict(parameters=params, source_part_id=part['id'],
                                    method=f'anchor-preserving-centerline-field-{field_version}',
                                    clinical_validation=False)
    if protected:
        new_part['modification']['protected_regions']=protected
        new_part['modification']['protection_scope']='Geometric constraints, not verified anatomical attachments'
    if anchor_blend!='minimum':
        new_part['modification']['anchor_blend']=anchor_blend
    if radial_mode != 'tangent':
        new_part['modification']['radial_mode'] = radial_mode
    if integration_steps:
        new_part['modification']['integration'] = dict(
            method='stationary-velocity-rk4', steps=integration_steps,
            semantics='Bend/twist displacement interpreted as velocity; logarithmic radial rate')
    if params == DEFAULT_PARAMETERS:
        new_part['edit_checks']=inspect_edit(part,new_part,edges,new_edges)
        return new_part, new_edges

    anchors, collars = [], []
    for points, radii, lengths in validated:
        anchors.extend((points[0], points[-1]))
        # At least the endpoint radius is protected; short edges may stay fixed.
        collars.extend(np.maximum(radii[[0, -1]] * 1.5, min(lengths[-1] * .04, 2.)))
    transition_widths=list(collars)
    for region in protected:
        anchors.append(region['center_mm'])
        collars.append(region['radius_mm'])
        transition_widths.append(region.get('transition_width_mm',region['radius_mm']))
    anchors, collars = np.asarray(anchors), np.asarray(collars)
    if field_version != 'v1':
        constraints = np.column_stack((anchors, collars, transition_widths))
        constraints = np.unique(constraints, axis=0)
        anchors, collars, transition_widths = constraints[:, :3], constraints[:, 3], constraints[:, 4]
    samples, shifts, tangents, scales = [], [], [], []
    for edge, (points, radii, lengths) in zip(new_edges, validated):
        chord = points[-1] - points[0]
        chord_length = np.linalg.norm(chord)
        t = lengths / lengths[-1]
        taper = np.sin(np.pi * t) ** 2
        if field_version == 'v1':
            taper *= _anchor_weight(points, anchors, collars, transition_widths,blend=anchor_blend)
        displacement = np.zeros_like(points)
        if chord_length > 1e-9:
            axis = chord / chord_length
            reference = points[0] + t[:, None] * chord
            deviation = points - reference
            # Preserve the axial component; only the transverse bend is twisted.
            transverse = deviation - np.outer(deviation @ axis, axis)
            normal = transverse[np.argmax(np.linalg.norm(transverse, axis=1))]
            if np.linalg.norm(normal) < 1e-9:
                basis = np.eye(3)[np.argmin(np.abs(axis))]
                normal = np.cross(axis, basis)
            normal = normal / np.linalg.norm(normal)
            bend = params['tortuosity'] * transverse
            if params['tortuosity'] > 0:
                bend += params['tortuosity'] * lengths[-1] * .06 * np.sin(np.pi * t)[:, None] * normal
            curved = transverse + bend
            angle = np.deg2rad(params['torsion_deg']) * np.sin(np.pi * t) ** 2
            rotated = curved * np.cos(angle)[:, None] + np.cross(axis, curved) * np.sin(angle)[:, None]
            displacement = (rotated - transverse) * taper[:, None]
        scale = 1. + (params['radius_scale'] - 1.) * taper
        edge['points'] = (points + displacement).tolist()
        edge['radii'] = (radii * scale).tolist()
        edge['modification'] = dict(parameters=params, source_provenance=edge.get('provenance'))
        # Uniform arc-length samples avoid dense voxel junctions dominating weights.
        count = int(np.clip(np.ceil(lengths[-1] / max(float(np.median(radii)) * .4, .1)) + 1, 16, 512))
        position = np.linspace(0., lengths[-1], count)
        unique = np.r_[True, np.diff(lengths) > 1e-9]
        interpolate = lambda values: np.column_stack([np.interp(position, lengths[unique], values[unique, i]) for i in range(3)])
        sample = interpolate(points)
        tangent = np.gradient(sample, axis=0)
        norm = np.linalg.norm(tangent, axis=1)
        tangent /= np.maximum(norm[:, None], 1e-12)
        samples.append(sample)
        shifts.append(interpolate(displacement))
        tangents.append(tangent)
        scales.append(np.interp(position, lengths[unique], scale[unique]))
    samples, shifts, tangents, scales = map(np.concatenate, (samples, shifts, tangents, scales))
    if integration_steps:
        scales = 1. + np.log(scales)
    tree = cKDTree(samples)
    if field_version == 'v3':
        # Freeze support from source geometry, never from displaced queries.
        source_distance = float(np.max(tree.query(vertices, k=1)[0]))
        support = max(3. * float(np.median(np.concatenate([item[1] for item in validated]))),
                      2. * source_distance)
        if integration_steps:
            # Gronwall envelope: d'(t) <= max_shift + max_rate*d(t).
            # Twice the envelope keeps a source sample away from zero support.
            max_rate = float(np.max(np.abs(scales - 1.)))
            max_shift = float(np.max(np.linalg.norm(shifts, axis=1)))
            support = max(support, 2. * np.exp(max_rate) * (source_distance + max_shift))
        if field_support_mm is not None:
            support = float(field_support_mm)
        new_part['modification']['field_support_mm'] = support
    def evaluate(v):
        if field_version == 'v3':
            radial_vectors = _polyline_radial(v, [item[0] for item in validated]) if radial_mode == 'polyline' else None
            field, scale_delta = _compact_field(v, samples, shifts, tangents, scales, tree, support, radial_vectors)
        else:
            distances, indices = tree.query(v, k=min(8, len(samples)))
            weights = 1. / np.maximum(distances, 1e-6) ** 2
            weights /= weights.sum(axis=1, keepdims=True)
            delta = v[:, None, :] - samples[indices]
            radial = delta - np.sum(delta * tangents[indices], axis=2)[..., None] * tangents[indices]
            field = shifts[indices] + radial * (scales[indices] - 1.)[..., None]
            field = np.sum(field * weights[..., None], axis=1)
            scale_delta = np.sum(weights * (scales[indices] - 1.), axis=1)
        # Explicitly fix the entire collar, including surface vertices off-axis.
        spatial_weight = _anchor_weight(v, anchors, collars, transition_widths,blend=anchor_blend)
        field *= spatial_weight[:, None]
        local_scale = 1. + spatial_weight * scale_delta
        return v + field, local_scale

    transform = (lambda v: _integrate_field(v, evaluate, integration_steps)) if integration_steps else evaluate
    output = vertices.copy()
    # Bound temporary allocations for large source meshes.
    for start in range(0, len(vertices), 8192):
        output[start:start + 8192] = transform(vertices[start:start + 8192])[0]
    if field_version != 'v1':
        for edge, (points, radii, _) in zip(new_edges, validated):
            mapped, local_scale = transform(points)
            edge['points'] = mapped.tolist()
            edge['radii'] = (radii * local_scale).tolist()
    if not np.isfinite(output).all():
        raise ValueError('Atlas deformation produced non-finite coordinates')
    new_part['vertices'] = output
    new_part['edit_checks']=inspect_edit(part,new_part,edges,new_edges)
    if new_part['edit_checks']['basic_invariants']=='FAIL':
        failed=[name for name,status in new_part['edit_checks']['checks'].items() if status=='FAIL']
        raise AtlasEditCheckFailure('Atlas modification failed basic checks: '+', '.join(failed))
    return new_part, new_edges
