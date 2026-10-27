"""Verify Boolean face lineage against the original input triangles."""
import numpy as np
import trimesh


def compose_face_lineage(lineage, nested):
    """Flatten one union stage; callers still verify the final source triangles."""
    def validate(value):
        names=value['source_names']
        owner=np.asarray(value['face_source_indices'])
        faces=np.asarray(value['source_face_indices'])
        if (not isinstance(names,list) or not names or any(not isinstance(n,str) or not n for n in names)
                or len(set(names))!=len(names) or owner.ndim!=1 or faces.shape!=owner.shape
                or not np.issubdtype(owner.dtype,np.integer) or not np.issubdtype(faces.dtype,np.integer)
                or np.any(owner<0) or np.any(owner>=len(names)) or np.any(faces<0)):
            raise ValueError('Invalid union lineage')
        return names,owner,faces
    names,owner,faces=validate(lineage)
    if set(nested)-set(names):
        raise ValueError('Nested lineage refers to unknown union input')
    tables={name:validate(value) for name,value in nested.items()}
    leaves=[]
    for name in names:
        expanded=tables[name][0] if name in tables else [name]
        if set(leaves)&set(expanded):
            raise ValueError('Ambiguous repeated original source')
        leaves.extend(expanded)
    leaf_indices={name:index for index,name in enumerate(leaves)}
    output_owner=np.empty(len(owner),dtype=int)
    output_faces=faces.copy()
    for index,name in enumerate(names):
        selected=np.flatnonzero(owner==index)
        if name in tables:
            child_names,child_owner,child_faces=tables[name]
            ids=faces[selected]
            if np.any(ids>=len(child_owner)):
                raise ValueError('Nested source face index outside parent union')
            output_owner[selected]=[leaf_indices[child_names[i]] for i in child_owner[ids]]
            output_faces[selected]=child_faces[ids]
        else:
            output_owner[selected]=leaf_indices[name]
    return dict(source_names=leaves,face_source_indices=output_owner.tolist(),
                source_face_indices=output_faces.tolist(),anatomical_labels='NOT ASSIGNED')


def verify_face_lineage(mesh, sources, lineage, *, tolerance_mm=1e-6):
    if not np.isfinite(tolerance_mm) or tolerance_mm<=0:
        raise ValueError('Positive finite tolerance required')
    names=lineage['source_names']
    owner=np.asarray(lineage['face_source_indices'])
    face=np.asarray(lineage['source_face_indices'])
    if (len(set(names))!=len(names) or set(names)!=set(sources)
            or owner.shape!=(len(mesh.faces),) or face.shape!=owner.shape
            or not np.issubdtype(owner.dtype,np.integer) or not np.issubdtype(face.dtype,np.integer)
            or np.any(owner<0) or np.any(owner>=len(names))):
        raise ValueError('Incomplete face lineage')
    rows=[]
    for index,name in enumerate(names):
        selected=np.flatnonzero(owner==index)
        ids=face[selected]
        source=sources[name]
        if np.any(ids<0) or np.any(ids>=len(source.faces)):
            raise ValueError('Source face index outside source')
        if not len(ids):
            rows.append(dict(source=name,faces=0,maximum_vertex_distance_mm=0.,
                             mismatched_faces=0,opposite_or_degenerate_normals=0))
            continue
        original=source.triangles[ids]
        output=mesh.triangles[selected]
        nearest=trimesh.triangles.closest_point(np.repeat(original,3,axis=0),
                                                output.reshape(-1,3))
        distance=np.linalg.norm(nearest-output.reshape(-1,3),axis=1).reshape(-1,3)
        alignment=np.einsum('ij,ij->i',source.face_normals[ids],mesh.face_normals[selected])
        rows.append(dict(source=name,faces=len(ids),
                         maximum_vertex_distance_mm=float(distance.max()),
                         mismatched_faces=int(np.count_nonzero(np.any(distance>tolerance_mm,axis=1))),
                         opposite_or_degenerate_normals=int(np.count_nonzero(alignment<=0))))
    return dict(status='PASS' if all(not r['mismatched_faces'] and
                                    not r['opposite_or_degenerate_normals'] for r in rows) else 'FAIL',
                rows=rows,tolerance_mm=tolerance_mm,faces=len(mesh.faces),
                scope='Every output triangle vertex against its declared input triangle, plus normal orientation',
                anatomical_labels='NOT ASSIGNED')
