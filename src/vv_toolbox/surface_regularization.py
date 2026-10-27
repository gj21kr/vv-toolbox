"""Bounded candidate mesh regularization with unchanged triangle connectivity."""
import math
import numpy as np
import trimesh
from scipy.sparse import coo_matrix


def regularize_surface(vertices,faces,*,iterations,max_displacement_mm,max_volume_change_fraction):
    for value in (max_displacement_mm,max_volume_change_fraction):
        if type(value) not in (int,float) or not math.isfinite(value) or value<=0:
            raise ValueError('positive finite preservation limits required')
    if type(iterations) is not int or not 1<=iterations<=100:
        raise ValueError('iterations must be between 1 and 100')
    original=np.asarray(vertices,dtype=float)
    faces=np.asarray(faces)
    if (original.ndim!=2 or original.shape[1]!=3 or not np.isfinite(original).all()
            or faces.ndim!=2 or faces.shape[1]!=3 or not len(faces)
            or not np.issubdtype(faces.dtype,np.integer) or faces.min()<0 or faces.max()>=len(original)):
        raise ValueError('finite vertices and integer triangle indices required')
    mesh=trimesh.Trimesh(vertices=original,faces=faces,process=False)
    if not mesh.is_volume or len(mesh.split(only_watertight=False))!=1:
        raise ValueError('one positive closed input surface required')
    edges=mesh.edges_unique
    rows=np.r_[edges[:,0],edges[:,1]]
    cols=np.r_[edges[:,1],edges[:,0]]
    degree=np.bincount(rows,minlength=len(original))
    if np.any(degree==0):
        raise ValueError('unused vertices are not supported')
    average=coo_matrix((1/degree[rows],(rows,cols)),shape=(len(original),len(original))).tocsr()
    moved=original.copy()
    # Work near the origin to avoid loss of precision from large atlas coordinates.
    origin=original.mean(axis=0)
    moved-=origin
    for _ in range(iterations):
        for coefficient in (.5,-.53):
            moved+=coefficient*(average@moved-moved)
    moved+=origin
    displacement=float(np.linalg.norm(moved-original,axis=1).max())
    if displacement>max_displacement_mm:
        raise ValueError(f'surface displacement limit exceeded: {displacement}')
    result=trimesh.Trimesh(vertices=moved,faces=faces,process=False)
    if not result.is_volume or np.any(result.area_faces<=0):
        raise ValueError('regularization invalidated surface')
    volume_change=abs(float(result.volume/mesh.volume)-1)
    if volume_change>max_volume_change_fraction:
        raise ValueError(f'surface volume preservation limit exceeded: {volume_change}')
    def angles(surface):
        values=np.degrees(surface.face_adjacency_angles)
        return dict(median_degrees=float(np.median(values)),p95_degrees=float(np.percentile(values,95)))
    return moved,faces.copy(),dict(schema='vv-toolbox.surface-regularization/1',status='CANDIDATE',
        method='uniform-adjacency two-pass Laplacian',coefficients=[.5,-.53],iterations=iterations,
        max_displacement_mm=displacement,displacement_limit_mm=max_displacement_mm,
        volume_change_fraction=volume_change,volume_change_limit_fraction=max_volume_change_fraction,
        before_adjacent_face_angles=angles(mesh),after_adjacent_face_angles=angles(result),
        triangle_connectivity_unchanged=True,
        checks=dict(displacement='PASS',volume_preservation='PASS',closed_surface='PASS',
                    self_intersection='NOT RUN',neck_dimensions='NOT RUN',clinical_validity='NOT RUN'),
        limitation='Same-triangle vertex motion bounds pointwise surface displacement, but not collision clearance or anatomical fidelity.')
