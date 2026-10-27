"""Experimental single-parent sac union; does not publish an accepted case."""
import hashlib
import json
import math
from copy import deepcopy

import numpy as np
from scipy.ndimage import label
from skimage.measure import marching_cubes
import trimesh

from .saccular import validate_saccular_spec


def _parent_field(world, points, radii):
    field = np.full(len(world), np.inf)
    for a, b, r0, r1 in zip(points, points[1:], radii, radii[1:]):
        direction = b-a
        t = np.clip((world-a) @ direction / (direction @ direction), 0, 1)
        field = np.minimum(field, np.linalg.norm(world-a-t[:, None]*direction, axis=1)
                           - r0-t*(r1-r0))
    return field


def _point_segment_distance(point, a, b):
    a, b = np.asarray(a), np.asarray(b)
    direction = b-a
    t = np.clip((point-a) @ direction / (direction @ direction), 0, 1)
    return float(np.linalg.norm(point-a-t*direction))


def _remote_parent_clearance(points, radii, index, fraction, support_center,
                             support_radius, spacing):
    """Screen the parent outside an explicit arc-length attachment neighborhood.

    The neighborhood is an engineering exclusion, not an anatomical neck.
    Clip segments at its boundaries so sampling density cannot hide a return.
    """
    lengths = np.linalg.norm(np.diff(points, axis=0), axis=1)
    stations = np.r_[0., np.cumsum(lengths)]
    anchor_station = stations[index] + fraction*lengths[index]
    anchor = points[index] + fraction*(points[index+1]-points[index])
    half_window = (np.linalg.norm(support_center-anchor) + support_radius
                   + radii.max() + 3*spacing)
    lower, upper = anchor_station-half_window, anchor_station+half_window
    checks = []
    for i, length in enumerate(lengths):
        for start, end in ((stations[i], min(stations[i+1], lower)),
                           (max(stations[i], upper), stations[i+1])):
            if end <= start:
                continue
            t0, t1 = (start-stations[i])/length, (end-stations[i])/length
            a = points[i] + t0*(points[i+1]-points[i])
            b = points[i] + t1*(points[i+1]-points[i])
            r0, r1 = radii[i]+np.array([t0,t1])*(radii[i+1]-radii[i])
            clearance = _point_segment_distance(support_center, a, b)-max(r0,r1)-support_radius
            if clearance <= 2*spacing:
                raise ValueError('remote parent clearance unresolved; sac support overlaps returning parent')
            checks.append(dict(interval_index=i, station_range_mm=[float(start),float(end)],
                               clearance_lower_bound_mm=clearance))
    return dict(status='PASS' if checks else 'NOT RUN',
                reason='screened remote intervals' if checks else 'no parent outside attachment neighborhood',
                excluded_station_range_mm=[float(max(0,lower)),float(min(stations[-1],upper))],
                exclusion_half_length_mm=float(half_window), intervals=checks,
                limitation='Local excluded parent and parent-parent self-contact are not assessed.')


def _measure_dome(mesh, neck):
    """Linear triangle clipping at the unchanged neck plane, in its local frame.

    Parent triangles that only touch the plane have no positive-side area and
    are excluded. Crossing triangles contribute their plane-intersection points.
    This does not infer an anatomical ostium or pick a different plane.
    """
    center = np.asarray(neck['center_mm'])
    basis = np.column_stack([neck['width_axis'],neck['depth_axis'],neck['normal']])
    local = (np.asarray(mesh.vertices)-center) @ basis
    faces = mesh.faces[np.max(local[mesh.faces,2],axis=1) > 1e-8]
    if not len(faces):
        raise ValueError('no generated dome surface above declared neck plane')
    ids = np.unique(faces)
    retained = local[ids[local[ids,2] >= 0]]
    pairs = np.concatenate([faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]]])
    a,b = local[pairs[:,0]],local[pairs[:,1]]
    crossing = ((a[:,2] < 0) & (b[:,2] > 0)) | ((a[:,2] > 0) & (b[:,2] < 0))
    a,b = a[crossing],b[crossing]
    if len(a):
        t = -a[:,2]/(b[:,2]-a[:,2])
        retained = np.vstack([retained,a+t[:,None]*(b-a)])
    return np.r_[np.ptp(retained[:,:2],axis=0),np.max(retained[:,2])]


def _neck_grid_bounds(points, radii, neck, parameters, spacing):
    """Bound tapered parent capsules directly in the sampling frame.

    A linearly interpolated center +/- radius reaches coordinate extrema at
    endpoints. Avoid rotating an already expanded world-axis bounding box.
    The field-boundary check still rejects any clipped implicit union.
    """
    basis = np.column_stack([neck['width_axis'],neck['depth_axis'],neck['normal']])
    local = (points-np.asarray(neck['center_mm'])) @ basis
    p = parameters
    blend = p['blending_extent_mm']
    sac_low = np.array([-p['dome_width_mm']/2,-p['dome_depth_mm']/2,-blend])-blend
    sac_high = np.array([p['dome_width_mm']/2,p['dome_depth_mm']/2,p['height_perpendicular_mm']])+blend
    low = np.minimum(np.min(local-radii[:,None],axis=0),sac_low)-3*spacing
    high = np.maximum(np.max(local+radii[:,None],axis=0),sac_high)+3*spacing
    # Suppress only floating-point noise at exact grid multiples.
    low = np.floor(low/spacing+1e-10)*spacing
    high = np.ceil(high/spacing-1e-10)*spacing
    return low, high


def _sac_field(world, spec):
    p, neck = spec['parameters'], spec['neck']
    local = world - np.asarray(neck['center_mm'])
    x, y, z = (local @ np.asarray(neck[key]) for key in ('width_axis', 'depth_axis', 'normal'))
    h, blend = p['height_perpendicular_mm'], p['blending_extent_mm']
    axes = []
    # Each dome axis follows an ellipsoidal profile above the declared neck.
    # Below the plane the neck extends into the parent before the smooth union.
    for key in ('width', 'depth'):
        a, r = p[f'dome_{key}_mm']/2, p[f'neck_{key}_mm']/2
        q = math.sqrt(max(0., 1-(r/a)**2))
        c = h/(1+q)
        center = c*q
        radius = a*np.sqrt(np.maximum(0., 1-((np.maximum(z, 0)-center)/c)**2))
        derivative = a*a*q/(c*r)
        u = np.clip((z+blend)/blend, 0, 1)
        extension = r*np.exp((derivative/r)*blend*(u**3-u**2))
        radius = np.where(z < 0, extension, radius)
        axes.append(np.maximum(radius, 1e-12))
    a, b = axes
    radial = (np.sqrt((x/a)**2+(y/b)**2)-1)*np.minimum(a, b)
    return np.maximum.reduce([radial, z-h, -z-blend])


def build_saccular_candidate(case, spec, *, spacing_mm, max_grid_voxels=2_000_000):
    """Return a connected closed union candidate for one interior sidewall sac.

    A design plane must be on the local circular-profile wall with a radial
    outward normal. Arbitrary attachment planes and bifurcations are not yet
    supported. Explicit status/limits prevent this from being accepted output.
    """
    validate_saccular_spec(spec, case)
    if case.get('lesions'):
        raise ValueError('existing lesions require integrated multi-lesion support')
    if (type(spacing_mm) not in (int, float) or not math.isfinite(spacing_mm)
            or spacing_mm <= 0):
        raise ValueError('positive finite grid spacing required')
    if type(max_grid_voxels) is not int or not 1 <= max_grid_voxels <= 20_000_000:
        raise ValueError('explicit grid budget between 1 and 20000000 required')
    p, neck = spec['parameters'], spec['neck']
    edge = next(e for e in case['edges'] if e['id'] == p['edge_id'])
    points, radii = np.asarray(edge['centerline_mm']), np.asarray(edge['radii_mm'])
    index, t = spec['parent_anchor']['interval_index'], spec['parent_anchor']['fraction']
    radius = radii[index]*(1-t)+radii[index+1]*t
    anchor, normal = np.asarray(spec['parent_anchor']['position_mm']), np.asarray(neck['normal'])
    center = np.asarray(neck['center_mm'])
    tangent = points[index+1]-points[index]
    tangent = tangent/np.linalg.norm(tangent)
    if abs(float(tangent @ normal)) > 1e-6 or not np.allclose(center, anchor+radius*normal, atol=1e-6, rtol=0):
        raise ValueError('neck must lie on the local circular parent wall with radial normal')
    minimum = min(float(radii.min()), p['neck_width_mm']/2, p['neck_depth_mm']/2,
                  p['blending_extent_mm'])
    if spacing_mm > minimum/3:
        raise ValueError('grid must resolve parent/neck radii and blending extent with at least three cells')
    # Union cannot preserve a declared external neck contour already inside
    # the baseline parent. This is a sampled necessary condition, not proof
    # that the entire contour is clear or that an anatomical ostium is valid.
    rim_parent = _parent_field(np.asarray(neck['curve_mm']), points, radii)
    invaded = int(np.count_nonzero(rim_parent < -1e-6))
    if invaded:
        raise ValueError(f'declared neck rim intersects baseline parent interior '
                         f'({invaded}/{len(rim_parent)} samples); attachment redesign required')
    h, blend = p['height_perpendicular_mm'], p['blending_extent_mm']
    buried_rim = np.asarray(neck['curve_mm'])-normal*blend
    if np.any(_parent_field(buried_rim, points, radii) >= -spacing_mm):
        raise ValueError('neck extension rim must be buried inside parent lumen by one grid cell')
    # Oriented box conservatively contains the complete loft and smooth-min support.
    extent = (np.abs(neck['width_axis'])*p['dome_width_mm']/2
              + np.abs(neck['depth_axis'])*p['dome_depth_mm']/2)
    a, b = center-normal*blend, center+normal*h
    sac_low, sac_high = np.minimum(a, b)-extent-blend, np.maximum(a, b)+extent+blend
    support_center = (sac_low+sac_high)/2
    support_radius = float(np.linalg.norm(sac_high-sac_low)/2)
    remote_parent = _remote_parent_clearance(points, radii, index, t, support_center,
                                             support_radius, spacing_mm)
    context_checks = []
    for other in case['edges']:
        if other['id'] == edge['id']:
            continue
        if other['centerline_mm'] is None:
            raise ValueError('unresolved context vessel prevents sac clearance screening')
        clearance = min(_point_segment_distance(support_center, x, y)
                        - max(r, s)-support_radius
                        for x, y, r, s in zip(other['centerline_mm'], other['centerline_mm'][1:],
                                             other['radii_mm'], other['radii_mm'][1:]))
        if clearance <= 2*spacing_mm:
            raise ValueError('sac context clearance unresolved; conservative support overlaps another vessel')
        context_checks.append(dict(edge_id=other['id'], clearance_lower_bound_mm=clearance))
    # Sample in the declared neck frame so the unchanged neck plane is an
    # actual grid layer, rather than an interpolation between oblique layers.
    basis = np.column_stack([neck['width_axis'], neck['depth_axis'], neck['normal']])
    low, high = _neck_grid_bounds(points,radii,neck,p,spacing_mm)
    shape_values = np.rint((high-low)/spacing_mm)+1
    if not np.isfinite(shape_values).all() or any(v > max_grid_voxels for v in shape_values):
        raise ValueError('sac grid budget exceeded')
    shape = tuple(int(v) for v in shape_values)
    count = math.prod(shape)
    if count > max_grid_voxels:
        raise ValueError('sac grid budget exceeded')
    values = np.empty(count, dtype=np.float32)
    for offset in range(0, count, 16384):
        ids = np.arange(offset, min(offset+16384, count))
        local = np.asarray(np.unravel_index(ids, shape)).T*spacing_mm+low
        world = local @ basis.T+center
        parent = _parent_field(world, points, radii)
        sac = _sac_field(world, spec)
        # Keep the declared neck plane and dome untouched by the blend.
        # C1 taper confines smooth-min expansion to the buried extension.
        depth = (world-center) @ normal
        # At the tangent plane, the parent alone has zero-volume contact along
        # a line. Treat that tie as outside, avoiding spurious long contours
        # from float32 isosurface vertices. The sac field remains unchanged.
        tangent_ties = (np.abs(local[:,2]) < spacing_mm*1e-8) & (np.abs(parent) < spacing_mm*1e-8)
        parent[tangent_ties] = spacing_mm*1e-3
        u = np.clip(-depth/blend, 0, 1)
        local_blend = blend*u*u*(3-2*u)
        weight = np.divide(np.maximum(local_blend-np.abs(parent-sac), 0), local_blend,
                           out=np.zeros_like(parent), where=local_blend > 0)
        values[ids] = np.minimum(parent, sac)-weight*weight*local_blend/4
    field = values.reshape(shape)
    if (not np.isfinite(field).all() or
            any(np.any(np.take(field, i, axis=d) <= 0) for d in range(3) for i in (0, -1))):
        raise ValueError('nonfinite field or clipped surface')
    components, component_count = label(field < 0)  # face-connected lumen voxels
    if component_count != 1:
        raise ValueError('generated lumen is disconnected')
    probes = np.vstack([anchor, center, center+normal*(h*.5)])
    probe_ids = np.rint(((probes-center) @ basis-low)/spacing_mm).astype(int)
    if not all(components[tuple(i)] == 1 for i in probe_ids):
        raise ValueError('parent, neck and sac do not share sampled lumen')
    vertices, faces, _, _ = marching_cubes(field, level=0, spacing=(spacing_mm,)*3,
                                         allow_degenerate=False)
    vertices = (vertices+low) @ basis.T+center
    mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
    if mesh.volume < 0:
        faces = faces[:, ::-1].copy()
        mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
    if not mesh.is_volume or np.any(mesh.area_faces <= 0) or len(mesh.split(only_watertight=False)) != 1:
        raise ValueError('sac union is not one positive closed surface')
    section = mesh.section(plane_origin=center, plane_normal=normal)
    if section is None or len(section.discrete) != 1:
        raise ValueError('declared neck plane does not have one output contour')
    local_section = (section.discrete[0]-center) @ basis
    measured = np.ptp(local_section, axis=0)[:2]
    requested = np.asarray([p['neck_width_mm'],p['neck_depth_mm']])
    tolerance = 2*spacing_mm
    if np.any(np.abs(measured-requested) > tolerance):
        raise ValueError(f'generated neck dimensions {measured.tolist()} exceed two-grid-spacing engineering tolerance')
    dome_measured = _measure_dome(mesh, neck)
    dome_requested = np.asarray([p['dome_width_mm'],p['dome_depth_mm'],p['height_perpendicular_mm']])
    if np.any(np.abs(dome_measured-dome_requested) > tolerance):
        raise ValueError(f'generated dome dimensions {dome_measured.tolist()} exceed two-grid-spacing engineering tolerance')
    return vertices, faces, dict(
        schema='vv-toolbox.saccular-candidate/1', status='CANDIDATE',
        generator_version='saccular-sidewall-6',
        determinism='no random sampling',
        case_revision=spec['case_revision'],
        source_case_id=case['case_id'], base_model_id=case['base_model_id'],
        sources=deepcopy(case['sources']), specification=deepcopy(spec),
        specification_sha256=hashlib.sha256(json.dumps(spec, sort_keys=True, separators=(',', ':'),
                                                    allow_nan=False).encode()).hexdigest(),
        edge_ids=[edge['id']], frame=case['frame'].copy(), spacing_mm=spacing_mm,
        grid_shape_xyz=list(shape), grid_origin_mm=(low @ basis.T+center).tolist(),
        grid_bounds_method='parent endpoint radius envelopes and sac bounds directly in neck frame',
        grid_direction_columns=basis.tolist(),
        grid_axis_names=['neck_width','neck_depth','neck_normal'],
        tangent_plane_tie_policy='parent-only zero-volume contacts treated outside at spacing/1000 field value',
        neck_rim_parent_screen=dict(sample_count=len(rim_parent), interior_sample_count=invaded,
                                    numerical_tolerance_mm=1e-6, status='PASS',
                                    scope='sampled necessary condition only'),
        neck_measurement=dict(requested_width_depth_mm=requested.tolist(),
                              measured_width_depth_mm=measured.tolist(),
                              tolerance_mm=tolerance,
                              method='actual triangle-plane contour spans in declared neck frame',
                              status='PASS'),
        dome_measurement=dict(requested_width_depth_height_mm=dome_requested.tolist(),
                              measured_width_depth_height_mm=dome_measured.tolist(),
                              tolerance_mm=tolerance,
                              method='triangle surface clipped above declared neck plane; local axis spans and perpendicular height',
                              tangent_parent_exclusion_mm=1e-8, status='PASS'),
        method='ellipsoidal-axis loft; buried-only tapered smooth union; neck-aligned grid; selected parent only',
        checks=dict(single_closed_surface='PASS', sampled_lumen_connectivity='PASS',
                    context_support_clearance='PASS', neck_dimensions='PASS',
                    dome_dimensions='PASS', surface_dimensions='PASS: declared neck and dome axis dimensions',
                    remote_parent_self_contact='NOT RUN', clinical_validity='NOT RUN'),
        remote_parent_support_clearance=remote_parent,
        context_clearance=context_checks, neck_probe_positions_mm=probes.tolist(),
        limitations='Candidate only. Sampling is not a continuous lumen proof. Dimension tolerance is engineering-only. '
                    'No accepted case lesion, bifurcation support or clinical acceptance.')
