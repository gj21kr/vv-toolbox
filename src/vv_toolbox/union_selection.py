"""Source-part selections with explicit shared interface vertices."""
import numpy as np


def select_union_source(vertices, faces, lineage, source_name):
    vertices=np.asarray(vertices);faces=np.asarray(faces)
    names=lineage['source_names']
    owners=np.asarray(lineage['face_source_indices'])
    source_faces=np.asarray(lineage['source_face_indices'])
    if (vertices.ndim!=2 or vertices.shape[1]!=3 or not np.isfinite(vertices).all()
            or faces.ndim!=2 or faces.shape[1]!=3 or not len(faces)
            or not np.issubdtype(faces.dtype,np.integer)
            or faces.min()<0 or faces.max()>=len(vertices)
            or len(set(names))!=len(names) or source_name not in names
            or owners.shape!=(len(faces),) or source_faces.shape!=owners.shape
            or not np.issubdtype(owners.dtype,np.integer)
            or not np.issubdtype(source_faces.dtype,np.integer)
            or np.any(owners<0) or np.any(owners>=len(names)) or np.any(source_faces<0)):
        raise ValueError('Valid union geometry and complete source lineage required')
    mask=owners==names.index(source_name)
    selected=np.flatnonzero(mask)
    vertices_selected=np.unique(faces[mask])
    shared=np.intersect1d(vertices_selected,np.unique(faces[~mask]))
    exclusive=np.setdiff1d(vertices_selected,shared)
    return dict(source_name=source_name,face_ids=selected.tolist(),
                source_face_ids=source_faces[mask].tolist(),
                vertex_ids=vertices_selected.tolist(),
                shared_interface_vertex_ids=shared.tolist(),
                exclusive_vertex_ids=exclusive.tolist(),
                editing_policy='Shared interface vertices require coordinated editing',
                anatomy='Source part identity only; anatomical segment labels not inferred')
