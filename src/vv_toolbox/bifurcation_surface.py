"""Experimental multi-branch lumen union; never an accepted case output."""
import math
from copy import deepcopy

import numpy as np
from scipy.ndimage import label
from skimage.measure import marching_cubes
import trimesh

from .bifurcation_attachment import inspect_bifurcation_attachment
from .bifurcation_saccular import validate_bifurcation_saccular_spec
from .bifurcation_clearance import inspect_bifurcation_clearance
from .saccular_surface import _parent_field, _sac_field, _neck_grid_bounds, _measure_dome


def measure_bifurcation_dimensions(mesh, spec, paths, *, spacing_mm):
    """Measure the declared neck/dome only when branches cannot contaminate it."""
    p, neck = spec['parameters'], spec['neck']
    center, normal = np.asarray(neck['center_mm']), np.asarray(neck['normal'])
    basis = np.column_stack([neck['width_axis'],neck['depth_axis'],normal])
    # Linear capsule endpoint envelopes bound the entire interpolated branch.
    # Do not silently count a returning branch as part of the aneurysm dome.
    upper = max(float(np.max((points-center)@normal+radii)) for points,radii in paths)
    if upper > 1e-6:
        raise ValueError('Dome measurement unresolved: branch extends above declared neck plane')
    section = mesh.section(plane_origin=center,plane_normal=normal)
    if section is None or len(section.discrete)!=1:
        raise ValueError('Declared neck plane must have one generated contour')
    neck_measured = np.ptp((section.discrete[0]-center)@basis,axis=0)[:2]
    dome_measured = _measure_dome(mesh,neck)
    tolerance = 2*spacing_mm
    result = {}
    for name,measured,requested in (
            ('neck',neck_measured,[p['neck_width_mm'],p['neck_depth_mm']]),
            ('dome',dome_measured,[p['dome_width_mm'],p['dome_depth_mm'],p['height_perpendicular_mm']])):
        errors = np.abs(measured-requested)
        if not np.isfinite(measured).all() or np.any(errors>tolerance):
            raise ValueError(f'Generated {name} dimensions exceed two-grid-spacing tolerance: {measured.tolist()}')
        result[name] = dict(status='PASS',requested_mm=requested,measured_mm=measured.tolist(),
                            absolute_error_mm=errors.tolist(),tolerance_mm=float(tolerance))
    result['method'] = 'Triangle-plane neck contour and clipped positive-side dome axis spans'
    result['baseline_positive_halfspace_upper_bound_mm'] = upper
    return result


def build_bifurcation_candidate(case, spec, *, spacing_mm, max_grid_voxels=2_000_000):
    if type(spacing_mm) not in (int, float) or not math.isfinite(spacing_mm) or spacing_mm <= 0:
        raise ValueError('Positive finite spacing required')
    if type(max_grid_voxels) is not int or not 1 <= max_grid_voxels <= 20_000_000:
        raise ValueError('Explicit grid budget between 1 and 20000000 required')
    if case.get('lesions'):
        raise ValueError('Existing lesions require integrated multi-lesion support')
    validate_bifurcation_saccular_spec(case, spec)
    p, neck = spec['parameters'], spec['neck']
    ids = {b['edge_id'] for b in spec['branch_constraints']}
    branches = sorted((e for e in case['edges'] if e['id'] in ids), key=lambda e:e['id'])
    paths = [(np.asarray(e['centerline_mm']),np.asarray(e['radii_mm'])) for e in branches]
    minimum = min(p['neck_width_mm']/2, p['neck_depth_mm']/2, p['blending_extent_mm'],
                  *(float(r.min()) for _,r in paths))
    if spacing_mm > minimum/3:
        raise ValueError('Spacing must resolve branch, neck and blend with at least three cells')
    attachment = inspect_bifurcation_attachment(case, spec, burial_margin_mm=spacing_mm)
    if attachment['status'] != 'PASS':
        raise ValueError('Bifurcation attachment or protected outlet screening did not pass')
    clearance=inspect_bifurcation_clearance(case,spec,margin_mm=2*spacing_mm)
    if clearance['status']=='UNKNOWN':
        raise ValueError('Nonincident vessel clearance unresolved; candidate generation refused')
    center = np.asarray(neck['center_mm'])
    normal = np.asarray(neck['normal'])
    basis = np.column_stack([neck['width_axis'],neck['depth_axis'],normal])
    bounds = [_neck_grid_bounds(points,radii,neck,p,spacing_mm) for points,radii in paths]
    low = np.min([b[0] for b in bounds],axis=0)
    high = np.max([b[1] for b in bounds],axis=0)
    counts = np.rint((high-low)/spacing_mm)+1
    if not np.isfinite(counts).all() or np.any(counts>max_grid_voxels):
        raise ValueError('Bifurcation grid budget exceeded')
    shape = tuple(int(n) for n in counts)
    count = math.prod(shape)
    if count > max_grid_voxels:raise ValueError('Bifurcation grid budget exceeded')
    values = np.empty(count,dtype=np.float32)
    for offset in range(0,count,16384):
        index = np.arange(offset,min(offset+16384,count))
        local = np.asarray(np.unravel_index(index,shape)).T*spacing_mm+low
        world = local@basis.T+center
        parent = np.minimum.reduce([_parent_field(world,*path) for path in paths])
        sac = _sac_field(world,spec)
        u = np.clip(-local[:,2]/p['blending_extent_mm'],0,1)
        blend = p['blending_extent_mm']*u*u*(3-2*u)
        weight = np.divide(np.maximum(blend-np.abs(parent-sac),0),blend,
                           out=np.zeros_like(parent),where=blend>0)
        values[index] = np.minimum(parent,sac)-weight*weight*blend/4
    field = values.reshape(shape)
    if not np.isfinite(field).all() or any(
            np.any(np.take(field,i,axis=d)<=0) for d in range(3) for i in (0,-1)):
        raise ValueError('Nonfinite field or clipped bifurcation surface')
    components, number = label(field<0)
    if number!=1:raise ValueError('Disconnected sampled bifurcation lumen')
    probes = [spec['junction']['position_mm'],center,
              center+normal*p['height_perpendicular_mm']/2]
    probes.extend(b['outlet_center_mm'] for b in spec['branch_constraints'])
    probe_ids = np.rint((np.asarray(probes)-center)@basis/spacing_mm-low/spacing_mm).astype(int)
    if np.any(probe_ids<0) or np.any(probe_ids>=np.asarray(shape)) or not all(
            components[tuple(i)]==1 for i in probe_ids):
        raise ValueError('Junction, neck, dome and every outlet must share sampled lumen')
    vertices,faces,_,_ = marching_cubes(field,level=0,spacing=(spacing_mm,)*3,allow_degenerate=False)
    vertices = (vertices+low)@basis.T+center
    mesh = trimesh.Trimesh(vertices=vertices,faces=faces,process=False)
    if mesh.volume<0:
        faces=faces[:,::-1].copy()
        mesh=trimesh.Trimesh(vertices=vertices,faces=faces,process=False)
    if not mesh.is_volume or np.any(mesh.area_faces<=0) or len(mesh.split(only_watertight=False))!=1:
        raise ValueError('Bifurcation union is not one positive closed surface')
    dimensions = measure_bifurcation_dimensions(mesh,spec,paths,spacing_mm=spacing_mm)
    return vertices,faces,dict(schema='vv-toolbox.bifurcation-candidate/1',status='CANDIDATE',
        generator_version='bifurcation-union-3',case_revision=spec['case_revision'],
        specification=deepcopy(spec),frame=deepcopy(case['frame']),edge_ids=sorted(ids),
        provenance='estimated',accepted_for_generation=False,spacing_mm=float(spacing_mm),
        grid_shape_xyz=list(shape),grid_origin_mm=(low@basis.T+center).tolist(),
        grid_direction_columns=basis.tolist(),attachment_screen=attachment,
        lumen_probe_positions_mm=np.asarray(probes).tolist(),
        dimension_measurements=dimensions,
        nonincident_support_clearance=clearance,
        checks=dict(single_closed_surface='PASS',sampled_lumen_connectivity='PASS',
                    protected_outlet_support_clearance='PASS',neck_dimensions='PASS',
                    dome_dimensions='PASS',continuous_branch_patency='NOT RUN',
                    nonincident_clearance=clearance['status'],anatomical_acceptance='NOT RUN'),
        limitation='Centerline-radius reconstruction, not an atlas mesh edit. Branch ends are capped. '
                   'Sampled connectivity is not continuous patency. No case publication or acceptance.')
