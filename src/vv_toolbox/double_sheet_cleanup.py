"""Remove only isolated reversed duplicate-triangle components on a copy."""
import numpy as np
import trimesh

from .surface_indexing import exact_vertex_index_copy
from .mesh_self_contact import inspect_self_contact


def remove_isolated_double_sheets(mesh):
    normalized,indexing=exact_vertex_index_copy(mesh)
    components=trimesh.graph.connected_components(
        normalized.face_adjacency,nodes=np.arange(len(normalized.faces)),min_len=1)
    removed=[]
    for component in components:
        if len(component)!=2:
            continue
        a,b=map(int,component)
        first,second=normalized.faces[[a,b]]
        if not np.array_equal(np.sort(first),np.sort(second)):
            continue
        if np.dot(normalized.face_normals[a],normalized.face_normals[b])>=0:
            continue
        # A two-face component alone is insufficient on a nonmanifold edge.
        target=set(first)
        related=np.count_nonzero(np.isin(normalized.faces,list(target)),axis=1)>=2
        if np.flatnonzero(related).tolist()!=sorted([a,b]):
            continue
        removed.extend([a,b])
    if not removed:
        raise ValueError('No isolated reversed double-sheet components')
    keep=np.setdiff1d(np.arange(len(normalized.faces)),removed)
    if not len(keep):
        raise ValueError('Cleanup must retain a positive volume')
    vertices_used=np.unique(normalized.faces[keep])
    inverse=np.full(len(normalized.vertices),-1,dtype=int)
    inverse[vertices_used]=np.arange(len(vertices_used))
    result=trimesh.Trimesh(normalized.vertices[vertices_used].copy(),
                           inverse[normalized.faces[keep]],process=False)
    if not np.array_equal(result.triangles,normalized.triangles[keep]):
        raise ValueError('Retained triangle coordinates changed')
    if not result.is_volume:
        raise ValueError('Remaining surface is not a closed positive volume')
    inspection=inspect_self_contact(result.vertices,result.faces)
    if inspection['status']!='NO_CONTACT_DETECTED':
        raise ValueError('Remaining surface self-contact not cleared')
    return result,dict(status='CANDIDATE',method='isolated-reversed-double-sheets/1',
        removed_source_face_ids=sorted(removed),retained_source_face_ids=keep.tolist(),
        source_indexing=indexing,retained_triangle_coordinates_unchanged=True,
        input_volume_mm3=float(normalized.volume),output_volume_mm3=float(result.volume),
        self_contact=inspection,source_modified=False,anatomical_validation='NOT RUN')
