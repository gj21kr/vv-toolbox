"""Bounded section-centroid proposal, independently checked against the wall."""
import numpy as np
from .source_sections import extract_source_sections
from .centerline_containment import inspect_centerline_containment
from .path_metrics import polyline_metrics


def center_section_path(mesh,points,*,fixed_indices,max_displacement_mm,max_turn_degrees):
    original=np.asarray(points,float);metrics=polyline_metrics(original);fixed=np.asarray(fixed_indices)
    if (len(original)<3 or fixed.ndim!=1 or not np.issubdtype(fixed.dtype,np.integer)
            or np.any(fixed<0) or np.any(fixed>=len(original)) or not {0,len(original)-1}<=set(fixed)
            or not np.isfinite([max_displacement_mm,max_turn_degrees]).all()
            or max_displacement_mm<=0 or not 0<max_turn_degrees<180):
        raise ValueError('Fixed endpoints and finite movement/turn bounds required')
    if inspect_centerline_containment(mesh,original)['status']!='PASS':raise ValueError('Contained input required')
    sections=extract_source_sections(mesh,original)
    if sections['counts']['UNKNOWN']:raise ValueError('All interior sections must be measured')
    free=[s for s in sections['profiles'] if s['index'] not in fixed]
    if not free:raise ValueError('Movable section stations required')
    def score(profiles):
        return float(sum(np.sum((np.asarray(s['centroid_xyz_mm'])-s['origin_mm'])**2)
                         for s in profiles if s['index'] not in fixed))
    initial_score=score(sections['profiles']);delta=np.zeros_like(original)
    for s in free:delta[s['index']]=np.asarray(s['centroid_xyz_mm'])-original[s['index']]
    attempts=[]
    for scale in (1.,.5,.25,.125):
        candidate=original+scale*delta;maximum=float(np.linalg.norm(candidate-original,axis=1).max())
        attempt=dict(scale=scale,maximum_displacement_mm=maximum,status='REJECTED')
        attempts.append(attempt)
        if maximum>max_displacement_mm:attempt['reason']='displacement limit';continue
        if np.any(np.linalg.norm(np.diff(candidate,axis=0),axis=1)<=1e-9):attempt['reason']='collapsed segment';continue
        after=polyline_metrics(candidate)
        if after['maximum_turn_deg']>max_turn_degrees:attempt['reason']='turn limit';continue
        containment=inspect_centerline_containment(mesh,candidate)
        if containment['status']!='PASS':attempt['reason']='whole-path containment';continue
        measured=extract_source_sections(mesh,candidate)
        if measured['counts']['UNKNOWN']:attempt['reason']='ambiguous new section';continue
        residual=score(measured['profiles'])
        if residual>=initial_score-1e-12:attempt['reason']='centroid residual not improved';continue
        attempt['status']='CANDIDATE'
        return candidate,dict(schema='vv-toolbox.section-centering/1',status='CANDIDATE',attempts=attempts,
            before=metrics,after=after,before_residual_mm2=initial_score,after_residual_mm2=residual,
            containment=containment,source_sections=measured,fixed_indices=fixed.tolist(),
            displacement_limit_mm=max_displacement_mm,turn_limit_degrees=max_turn_degrees,
            accepted_for_generation=False,limitation='Section centroid is not a medial-axis guarantee; radius and branch preservation remain separate.')
    return original.copy(),dict(schema='vv-toolbox.section-centering/1',status='NO_ACCEPTED_CHANGE',attempts=attempts,
                               accepted_for_generation=False)
