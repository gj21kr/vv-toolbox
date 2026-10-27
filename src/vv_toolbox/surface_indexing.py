"""Exact-coordinate index normalization on a copy, with no triangle relocation."""
import hashlib

import numpy as np
import trimesh


def exact_vertex_index_copy(mesh):
    vertices=np.asarray(mesh.vertices,dtype=np.float64)
    faces=np.asarray(mesh.faces)
    if (vertices.ndim!=2 or vertices.shape[1]!=3 or not len(vertices)
            or not np.isfinite(vertices).all() or faces.ndim!=2 or faces.shape[1]!=3
            or not len(faces) or not np.issubdtype(faces.dtype,np.integer)
            or faces.min()<0 or faces.max()>=len(vertices)):
        raise ValueError('Finite vertices and valid triangular indices required')
    unique,inverse=np.unique(vertices,axis=0,return_inverse=True)
    remapped=inverse[faces]
    before=np.asarray(vertices[faces],dtype='<f8').tobytes()
    after=np.asarray(unique[remapped],dtype='<f8').tobytes()
    if before!=after:
        raise ValueError('Index normalization must preserve triangle coordinate bytes')
    result=trimesh.Trimesh(unique,remapped,process=False)
    zero_area=int(np.count_nonzero(result.area_faces<=1e-12))
    usable=bool(result.is_watertight and result.is_winding_consistent and zero_area==0)
    report=dict(method='exact-coordinate-index-copy/1',coordinate_tolerance_mm=0,
        original_vertices=len(vertices),normalized_vertices=len(unique),
        faces=len(faces),triangle_coordinate_bytes_preserved=True,
        triangle_sha256=hashlib.sha256(before).hexdigest(),
        original_watertight=bool(mesh.is_watertight),
        normalized_watertight=bool(result.is_watertight),
        normalized_winding_consistent=bool(result.is_winding_consistent),
        zero_area_faces=zero_area,usable_for_sampled_containment=usable,
        original_modified=False,faces_added_or_removed=False,
        self_intersection='NOT RUN',anatomical_validity='NOT RUN')
    return result,report
