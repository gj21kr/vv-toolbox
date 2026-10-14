"""Local, illustrative atlas deformation in original source units (assumed mm).

This preserves topology and anchor collars, not anatomical validity or freedom
from collisions. Research use only, not for clinical decision.
"""
from copy import deepcopy

import numpy as np
from scipy.spatial import cKDTree


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


def _anchor_weight(points, anchors, collars):
    # A common spatial collar for mesh and paths protects all incident branches.
    weight = np.ones(len(points))
    for anchor, collar in zip(anchors, collars):
        distance = np.linalg.norm(points - anchor, axis=1)
        weight = np.minimum(weight, _smoothstep((distance - collar) / collar))
    return weight


def deform_part(part, edges, parameters):
    """Return a deformed mesh dict and matching edge list without editing input.

    Radius is a local radial scale with fixed junction/end collars. Tortuosity
    adjusts deviation from each endpoint chord; positive values add a smooth
    bend even to straight paths. Torsion rotates that deviation around the chord
    by a tapered angle, in degrees. Closed paths have no unique chord and their
    shape is preserved (radius can still change). Nearest-path blending is an
    approximation, especially at crowded branches; no remeshing is performed.
    Always call against original geometry, never the previous edited result.
    """
    params = validate_parameters(parameters)
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
                                    method='anchor-preserving-centerline-field-v1',
                                    clinical_validation=False)
    if params == DEFAULT_PARAMETERS:
        return new_part, new_edges

    anchors, collars = [], []
    for points, radii, lengths in validated:
        anchors.extend((points[0], points[-1]))
        # At least the endpoint radius is protected; short edges may stay fixed.
        collars.extend(np.maximum(radii[[0, -1]] * 1.5, min(lengths[-1] * .04, 2.)))
    anchors, collars = np.asarray(anchors), np.asarray(collars)
    samples, shifts, tangents, scales = [], [], [], []
    for edge, (points, radii, lengths) in zip(new_edges, validated):
        chord = points[-1] - points[0]
        chord_length = np.linalg.norm(chord)
        t = lengths / lengths[-1]
        taper = _anchor_weight(points, anchors, collars) * np.sin(np.pi * t) ** 2
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
    tree = cKDTree(samples)
    output = vertices.copy()
    # Bound temporary allocations for large source meshes.
    for start in range(0, len(vertices), 8192):
        v = vertices[start:start + 8192]
        distances, indices = tree.query(v, k=min(8, len(samples)))
        weights = 1. / np.maximum(distances, 1e-6) ** 2
        weights /= weights.sum(axis=1, keepdims=True)
        delta = v[:, None, :] - samples[indices]
        radial = delta - np.sum(delta * tangents[indices], axis=2)[..., None] * tangents[indices]
        field = shifts[indices] + radial * (scales[indices] - 1.)[..., None]
        field = np.sum(field * weights[..., None], axis=1)
        # Explicitly fix the entire collar, including surface vertices off-axis.
        field *= _anchor_weight(v, anchors, collars)[:, None]
        output[start:start + len(v)] += field
    if not np.isfinite(output).all():
        raise ValueError('Atlas deformation produced non-finite coordinates')
    new_part['vertices'] = output
    return new_part, new_edges
