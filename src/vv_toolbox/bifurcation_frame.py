"""Engineering frame from the incident capsule envelope along a supplied ray."""
from copy import deepcopy
import numpy as np
from scipy.optimize import brentq
from .bifurcation_saccular import validate_bifurcation_saccular_spec
from .saccular_surface import _parent_field


def propose_bifurcation_frame(case,spec,*,search_mm,step_mm,gradient_step_mm):
    validate_bifurcation_saccular_spec(case,spec)
    for value in (search_mm,step_mm,gradient_step_mm):
        if type(value) not in (int,float) or not np.isfinite(value) or value<=0:
            raise ValueError('Positive finite search, sampling and gradient steps required')
    count=int(np.ceil(search_mm/step_mm))
    if count<1 or count>10000:raise ValueError('Ray sampling budget exceeded')
    ids={b['edge_id'] for b in spec['branch_constraints']}
    paths=[(np.asarray(e['centerline_mm']),np.asarray(e['radii_mm'])) for e in case['edges'] if e['id'] in ids]
    def field(points):return np.minimum.reduce([_parent_field(np.atleast_2d(points),*p) for p in paths])
    origin=np.asarray(spec['junction']['position_mm']);ray=np.asarray(spec['neck']['normal'])
    stations=np.linspace(0,search_mm,count+1);values=field(origin+stations[:,None]*ray)
    if values[0]>=0:raise ValueError('Junction ray origin must lie inside incident envelope')
    exits=np.flatnonzero((values[:-1]<0)&(values[1:]>=0))
    if not len(exits):raise ValueError('No sampled envelope exit in explicit search distance')
    index=int(exits[0])
    distance=brentq(lambda t:float(field(origin+t*ray)[0]),stations[index],stations[index+1],xtol=1e-10)
    point=origin+distance*ray
    gradients=[]
    for h in (gradient_step_mm,gradient_step_mm/2):
        offsets=np.eye(3)*h
        gradient=(field(point+offsets)-field(point-offsets))/(2*h)
        if np.linalg.norm(gradient)<1e-8:raise ValueError('Degenerate envelope gradient')
        gradients.append(gradient/np.linalg.norm(gradient))
    if np.linalg.norm(gradients[0]-gradients[1])>.01:
        raise ValueError('Envelope gradient unstable across requested sampling scales')
    normal=gradients[-1]
    if normal@ray<=0:raise ValueError('Proposed normal does not face supplied exit direction')
    reference=np.asarray(spec['neck']['width_axis'])
    width=reference-normal*(reference@normal)
    if np.linalg.norm(width)<1e-8:raise ValueError('Width reference is parallel to envelope normal')
    width/=np.linalg.norm(width)
    parameters=deepcopy(spec['parameters'])
    parameters.update(neck_center_mm=point.tolist(),outward_normal=normal.tolist(),width_direction=width.tolist())
    return dict(schema='vv-toolbox.bifurcation-frame/1',status='CANDIDATE',case_revision=spec['case_revision'],
        parameters=parameters,ray_origin_mm=origin.tolist(),ray_direction=ray.tolist(),
        search_mm=float(search_mm),step_mm=float(step_mm),gradient_step_mm=float(gradient_step_mm),
        sampled_exit_count=len(exits),exit_distance_mm=float(distance),field_residual_mm=float(field(point)[0]),
        gradient_direction_difference=float(np.linalg.norm(gradients[0]-gradients[1])),
        accepted_for_generation=False,attachment='NOT RUN',anatomical_placement='UNKNOWN',
        limitation='Centerline-radius envelope, not atlas mesh. First sampled ray exit; unsampled exits may exist. '
                   'Finite differences do not prove differentiability. Dimensions retained; all geometry checks required.')
