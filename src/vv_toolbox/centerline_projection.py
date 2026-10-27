"""Explicit bounded inward projection candidate; never modifies the source."""
import numpy as np
import trimesh
from .surface_indexing import exact_vertex_index_copy
from .centerline_containment import inspect_centerline_containment


class ProjectionContainmentError(ValueError):
    """Rejected path with inspection evidence, never an accepted candidate."""
    def __init__(self,inspection,candidate=None):
        super().__init__('Projected whole path containment did not pass: '+inspection['status'])
        self.inspection=inspection
        self.candidate=None if candidate is None else candidate.copy()


def _inward_points(surface,closest,faces,inset_mm,adaptive):
    proposed=closest-inset_mm*surface.face_normals[faces]
    if not adaptive:return proposed
    valid=np.zeros(len(closest),dtype=bool)
    # At a triangle edge, one face normal may point outside the adjacent face.
    # A declared small move into that face avoids choosing an ambiguous edge normal.
    for fraction in (0.,.05):
        anchor=(1-fraction)*closest+fraction*surface.triangles_center[faces]
        for iteration in range(9):
            proposed[~valid]=anchor[~valid]-(inset_mm/(2**iteration))*surface.face_normals[faces[~valid]]
            _,distance,_=trimesh.proximity.closest_point(surface,proposed)
            valid=surface.contains(proposed)&(distance>1e-6)
            if valid.all():return proposed
    raise ValueError('No verified interior inset within backtracking budget')


def project_outside_stations(mesh,points,*,movable_indices,inset_mm,max_displacement_mm,adaptive_inset=False):
    points=np.asarray(points,float)
    indices=np.asarray(movable_indices)
    if type(adaptive_inset) is not bool:raise ValueError('Explicit adaptive inset boolean required')
    if (points.ndim!=2 or points.shape[1]!=3 or len(points)<2 or not np.isfinite(points).all()
            or indices.ndim!=1 or not np.issubdtype(indices.dtype,np.integer)
            or len(set(indices.tolist()))!=len(indices) or np.any(indices<0) or np.any(indices>=len(points))
            or not np.isfinite([inset_mm,max_displacement_mm]).all()
            or not 0<inset_mm<=max_displacement_mm):
        raise ValueError('Explicit movable stations and positive bounded inset required')
    surface,indexing=exact_vertex_index_copy(mesh)
    if not indexing['usable_for_sampled_containment']:raise ValueError('Closed source surface required')
    closest,distance,faces=trimesh.proximity.closest_point(surface,points)
    inside=surface.contains(points)
    needs=np.flatnonzero(~inside | (distance<inset_mm))
    if not set(needs)<=set(indices):raise ValueError('A fixed station requires correction')
    result=points.copy()
    if len(needs):result[needs]=_inward_points(surface,closest[needs],faces[needs],inset_mm,adaptive_inset)
    displacement=np.linalg.norm(result-points,axis=1)
    if displacement.max()>max_displacement_mm:raise ValueError('Projection exceeds displacement limit')
    if np.any(np.linalg.norm(np.diff(result,axis=0),axis=1)<=1e-9):raise ValueError('Projection collapsed a path segment')
    containment=inspect_centerline_containment(surface,result)
    if containment['status']!='PASS':raise ProjectionContainmentError(containment,result)
    return result,dict(schema='vv-toolbox.centerline-projection/1',status='CANDIDATE',
        method='closest-source-face inward-normal projection',inset_mm=float(inset_mm),adaptive_inset=adaptive_inset,
        adaptive_anchor_fractions=[0.,.05] if adaptive_inset else [],
        displacement_limit_mm=float(max_displacement_mm),maximum_displacement_mm=float(displacement.max()),
        movable_indices=indices.tolist(),moved_indices=needs.tolist(),displacements_mm=displacement.tolist(),
        containment=containment,source_modified=False,accepted_for_generation=False,
        limitation='Inside path candidate, not a medial axis or radius-envelope validation. Inset may fail near concavities; no automatic retry or limit relaxation.')


def refine_projected_path(mesh,points,*,movable_indices,inset_mm,max_displacement_mm,max_rounds=8,max_points=2048,adaptive_inset=False):
    """Insert witnesses on failing intervals with fixed original parameter order."""
    if type(max_rounds) is not int or not 1<=max_rounds<=16 or type(max_points) is not int or max_points<2:
        raise ValueError('Explicit bounded refinement budget required')
    original=np.asarray(points,float)
    try:
        candidate,initial=project_outside_stations(mesh,original,movable_indices=movable_indices,
            inset_mm=inset_mm,max_displacement_mm=max_displacement_mm,adaptive_inset=adaptive_inset)
    except ProjectionContainmentError as error:
        candidate=error.candidate;inspection=error.inspection
    else:
        return candidate,dict(initial,refinement_rounds=0,source_parameters=list(range(len(original))))
    surface,_=exact_vertex_index_copy(mesh)
    parameters=np.arange(len(original),dtype=float);history=[]
    for iteration in range(max_rounds):
        additions={}
        for witness in inspection['outside_witnesses']:
            additions.setdefault(witness['segment_index'],set()).add(witness['fraction'])
        for index in inspection['unresolved_segments']:additions.setdefault(index,set()).add(.5)
        if not additions:raise ProjectionContainmentError(inspection,candidate)
        if len(candidate)+sum(map(len,additions.values()))>max_points:raise ValueError('Refinement point budget exceeded')
        new_points=[];new_parameters=[]
        for i,point in enumerate(candidate):
            new_points.append(point);new_parameters.append(parameters[i])
            for fraction in sorted(additions.get(i,())):
                new_points.append(point+fraction*(candidate[i+1]-point))
                new_parameters.append(parameters[i]+fraction*(parameters[i+1]-parameters[i]))
        candidate=np.asarray(new_points);new_parameters=np.asarray(new_parameters)
        inserted=~np.isin(new_parameters,parameters)
        closest,distance,faces=trimesh.proximity.closest_point(surface,candidate)
        needs=inserted & (~surface.contains(candidate) | (distance<inset_mm))
        if np.any(needs):candidate[needs]=_inward_points(surface,closest[needs],faces[needs],inset_mm,adaptive_inset)
        reference=np.column_stack([np.interp(new_parameters,np.arange(len(original)),original[:,k]) for k in range(3)])
        maximum=float(np.linalg.norm(candidate-reference,axis=1).max())
        if maximum>max_displacement_mm:raise ValueError('Refinement exceeds original-path displacement limit')
        parameters=new_parameters
        inspection=inspect_centerline_containment(surface,candidate)
        history.append(dict(round=iteration+1,point_count=len(candidate),status=inspection['status']))
        if inspection['status']=='PASS':
            return candidate,dict(schema='vv-toolbox.refined-path-projection/1',status='CANDIDATE',
                refinement_rounds=iteration+1,history=history,source_parameters=parameters.tolist(),
                maximum_displacement_mm=maximum,displacement_limit_mm=max_displacement_mm,inset_mm=inset_mm,adaptive_inset=adaptive_inset,
                containment=inspection,source_modified=False,accepted_for_generation=False,
                limitation='Ordered inside polyline only; smoothness, mediality and finite-radius passage unverified.')
    raise ProjectionContainmentError(inspection,candidate)
