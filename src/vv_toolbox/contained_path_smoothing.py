"""Bounded polyline fairing with whole-interval containment at every step."""
import numpy as np
from .centerline_containment import inspect_centerline_containment
from .path_metrics import polyline_metrics


def smooth_contained_path(mesh,points,*,fixed_indices,max_displacement_mm,iterations=10):
    original=np.asarray(points,float);fixed=np.asarray(fixed_indices)
    polyline_metrics(original)
    if (len(original)<3 or fixed.ndim!=1 or not np.issubdtype(fixed.dtype,np.integer)
            or np.any(fixed<0) or np.any(fixed>=len(original)) or len(set(fixed.tolist()))!=len(fixed)
            or not {0,len(original)-1}<=set(fixed) or not np.isfinite(max_displacement_mm)
            or max_displacement_mm<=0 or type(iterations) is not int or not 1<=iterations<=100):
        raise ValueError('Fixed endpoints, finite movement limit and bounded iterations required')
    initial=inspect_centerline_containment(mesh,original)
    if initial['status']!='PASS':raise ValueError('Initially contained whole path required')
    current=original.copy();history=[];inspection=initial
    def energy(p):return float(np.sum(np.diff(p,n=2,axis=0)**2))
    for iteration in range(iterations):
        delta=np.zeros_like(current)
        delta[1:-1]=(current[:-2]+current[2:])/2-current[1:-1]
        delta[fixed]=0
        accepted=False
        for backtrack in range(9):
            step=2.**(-backtrack);proposed=current+step*delta
            if np.linalg.norm(proposed-original,axis=1).max()>max_displacement_mm:continue
            if np.any(np.linalg.norm(np.diff(proposed,axis=0),axis=1)<=1e-9):continue
            if energy(proposed)>=energy(current)-1e-14:continue
            check=inspect_centerline_containment(mesh,proposed)
            if check['status']!='PASS':continue
            current=proposed;inspection=check;accepted=True
            history.append(dict(iteration=iteration+1,step=step,second_difference_energy_mm2=energy(current)))
            break
        if not accepted:break
    return current,dict(schema='vv-toolbox.contained-path-smoothing/1',status='CANDIDATE',
        fixed_indices=fixed.tolist(),maximum_displacement_mm=float(np.linalg.norm(current-original,axis=1).max()),
        displacement_limit_mm=max_displacement_mm,accepted_steps=history,
        before=polyline_metrics(original),after=polyline_metrics(current),containment=inspection,
        source_modified=False,accepted_for_generation=False,
        limitation='Discrete polyline smoothing; no radius, medial-axis or differential curvature acceptance.')
