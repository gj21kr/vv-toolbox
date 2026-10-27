"""Explicit multi-branch sac design inputs; no generated lumen or acceptance."""
from copy import deepcopy
import numpy as np

from .case_io import case_digest
from .lesions import REGIONS
from .saccular import _vector, _positive


def bifurcation_saccular_spec(case, *, lesion_id, junction_id, region,
        outlet_distances_mm, neck_center_mm, outward_normal, width_direction,
        neck_width_mm, neck_depth_mm, height_perpendicular_mm,
        dome_width_mm, dome_depth_mm, blending_extent_mm):
    revision=case_digest(case)
    if not isinstance(lesion_id,str) or not lesion_id.strip():
        raise ValueError('Explicit lesion ID required')
    if any(item.get('lesion_id')==lesion_id for item in case.get('lesions',[])):
        raise ValueError('Duplicate lesion ID')
    if region not in REGIONS:
        raise ValueError('Explicit supported region required')
    node=case['nodes'].get(junction_id)
    if node is None or node['position_mm'] is None:
        raise ValueError('Resolved junction position required')
    incident=[e for e in case['edges'] if junction_id in (e['start'],e['end'])]
    if len(incident)<3 or any(e['start']==e['end'] for e in incident):
        raise ValueError('At least three incident open branches required')
    if not isinstance(outlet_distances_mm,dict) or set(outlet_distances_mm)!={e['id'] for e in incident}:
        raise ValueError('Explicit outlet distances for every incident branch required')
    dimensions=dict(neck_width_mm=neck_width_mm,neck_depth_mm=neck_depth_mm,
        height_perpendicular_mm=height_perpendicular_mm,dome_width_mm=dome_width_mm,
        dome_depth_mm=dome_depth_mm,blending_extent_mm=blending_extent_mm)
    for name,value in dimensions.items():_positive(value,name)
    if dome_width_mm<neck_width_mm or dome_depth_mm<neck_depth_mm:
        raise ValueError('Dome dimensions must not be smaller than neck dimensions')
    center=_vector(neck_center_mm,'neck center');normal=_vector(outward_normal,'normal')
    width=_vector(width_direction,'width direction')
    if not np.isclose(np.linalg.norm(normal),1,atol=1e-8,rtol=0) or not np.isclose(np.linalg.norm(width),1,atol=1e-8,rtol=0):
        raise ValueError('Unit normal and width direction required')
    if abs(float(normal@width))>1e-8:raise ValueError('Width axis must lie in neck plane')
    depth=np.cross(normal,width);branches=[]
    for edge in sorted(incident,key=lambda e:e['id']):
        distance=outlet_distances_mm[edge['id']];_positive(distance,'outlet distance')
        if edge['centerline_mm'] is None:raise ValueError('Every incident branch needs a centerline')
        reverse=edge['end']==junction_id
        points=np.asarray(edge['centerline_mm'],float);radii=np.asarray(edge['radii_mm'],float)
        if reverse:points=points[::-1];radii=radii[::-1]
        lengths=np.linalg.norm(np.diff(points,axis=0),axis=1)
        if not np.isfinite(lengths).all() or np.any(lengths<=1e-9):raise ValueError('Finite distinct branch stations required')
        stations=np.r_[0.,np.cumsum(lengths)]
        if distance>stations[-1]:raise ValueError('Outlet distance exceeds branch length')
        index=min(int(np.searchsorted(stations,distance,side='right')-1),len(lengths)-1)
        fraction=(distance-stations[index])/lengths[index]
        outlet=points[index]+fraction*(points[index+1]-points[index])
        radius=radii[index]+fraction*(radii[index+1]-radii[index])
        branches.append(dict(edge_id=edge['id'],junction_at_edge_end=bool(reverse),
            distance_from_junction_mm=float(distance),outlet_center_mm=outlet.tolist(),
            outlet_radius_mm=float(radius),outlet_tangent_away=(np.diff(points,axis=0)[index]/lengths[index]).tolist(),
            must_preserve_patent_path=True,source_ids=deepcopy(edge['source_ids'])))
    theta=np.arange(64)*2*np.pi/64
    curve=center+np.cos(theta)[:,None]*width*neck_width_mm/2+np.sin(theta)[:,None]*depth*neck_depth_mm/2
    if not np.isfinite(curve).all():raise ValueError('Nonfinite derived neck curve')
    params=dict(lesion_id=lesion_id,junction_id=junction_id,region=region,
        outlet_distances_mm={k:float(v) for k,v in sorted(outlet_distances_mm.items())},
        neck_center_mm=center.tolist(),outward_normal=normal.tolist(),width_direction=width.tolist(),
        **{k:float(v) for k,v in dimensions.items()})
    return dict(schema='vv-toolbox.bifurcation-saccular-spec/1',mode='manual_synthetic',
        case_revision=revision,base_model_id=case['base_model_id'],frame=deepcopy(case['frame']),parameters=params,
        junction=dict(node_id=junction_id,position_mm=deepcopy(node['position_mm'])),
        branch_constraints=branches,neck=dict(center_mm=center.tolist(),normal=normal.tolist(),
            width_axis=width.tolist(),depth_axis=depth.tolist(),curve_mm=curve.tolist(),
            curve_closed=True,curve_convention='64 ellipse samples; last connects to first'),
        graph_policy='Preserve every incident edge and outlet; sac is a lesion, not a daughter artery',
        geometry_status='NOT GENERATED',accepted_for_generation=False,
        checks={key:'NOT RUN' for key in ('attachment','open_lumen','branch_patency','nonoverlap','anatomical_acceptance')})


def validate_bifurcation_saccular_spec(case,spec):
    if not isinstance(spec,dict) or spec.get('schema')!='vv-toolbox.bifurcation-saccular-spec/1':
        raise ValueError('Bifurcation sac specification required')
    expected=bifurcation_saccular_spec(case,**spec.get('parameters',{}))
    if spec!=expected:raise ValueError('Bifurcation sac specification differs from bound case or parameters')
    return expected
