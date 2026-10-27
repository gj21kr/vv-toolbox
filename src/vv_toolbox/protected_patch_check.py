"""Reject geometry edits that violate an explicit original patch contract."""
import hashlib

import numpy as np


def check_protected_patch(original, edited, faces, patch, *, allowed_vertex_ids, max_displacement_mm):
    original, edited, faces = np.asarray(original,dtype=float), np.asarray(edited,dtype=float), np.asarray(faces)
    allowed = np.asarray(allowed_vertex_ids)
    if (original.ndim!=2 or original.shape[1]!=3 or edited.shape!=original.shape
            or not np.isfinite(original).all() or not np.isfinite(edited).all()
            or faces.ndim!=2 or faces.shape[1]!=3 or not np.issubdtype(faces.dtype,np.integer)
            or not len(faces) or faces.min()<0 or faces.max()>=len(original)
            or allowed.ndim!=1 or not len(allowed) or not np.issubdtype(allowed.dtype,np.integer)
            or allowed.min()<0 or allowed.max()>=len(original) or len(np.unique(allowed))!=len(allowed)
            or type(max_displacement_mm) not in (int,float) or not np.isfinite(max_displacement_mm)
            or max_displacement_mm<=0):
        raise ValueError('Matching finite geometry and explicit bounded edit region required')
    selected=np.asarray(patch['source_face_ids'])
    if (selected.ndim!=1 or not len(selected) or not np.issubdtype(selected.dtype,np.integer)
            or selected.min()<0 or selected.max()>=len(faces)):
        raise ValueError('Valid patch source faces required')
    expected=np.asarray(patch['vertices'])[np.asarray(patch['faces'])]
    if not np.array_equal(original[faces[selected]],expected):
        raise ValueError('Protected patch does not match source')
    # Protect every source index sharing a protected coordinate, not only indexed faces.
    _,inverse=np.unique(original,axis=0,return_inverse=True)
    protected=np.isin(inverse,np.unique(inverse[faces[selected]]))
    if np.any(protected[allowed]):
        raise ValueError('Allowed edit region overlaps protected patch')
    fixed=np.ones(len(original),dtype=bool);fixed[allowed]=False
    if original[fixed].astype('<f8').tobytes()!=edited[fixed].astype('<f8').tobytes():
        raise ValueError('Fixed source positions changed')
    displacement=np.linalg.norm(edited-original,axis=1)
    if displacement.max()>max_displacement_mm:
        raise ValueError('Edit displacement exceeds declared bound')
    before,after=original[faces],edited[faces]
    nb=np.cross(before[:,1]-before[:,0],before[:,2]-before[:,0])
    na=np.cross(after[:,1]-after[:,0],after[:,2]-after[:,0])
    if np.any(np.linalg.norm(na,axis=1)<=1e-12) or np.any(np.sum(na*nb,axis=1)<=0):
        raise ValueError('Edit degenerates or reverses a source face')
    return dict(status='PASS',protected_patch_identity='PASS',fixed_positions_exact=True,
        protected_vertices=int(protected.sum()),allowed_vertices=len(allowed),
        moved_vertices=int(np.count_nonzero(displacement)),maximum_displacement_mm=float(displacement.max()),
        displacement_limit_mm=max_displacement_mm,
        protected_triangle_sha256=hashlib.sha256(after[selected].astype('<f8').tobytes()).hexdigest(),
        self_contact='NOT RUN',surroundings='NOT RUN',anatomical_validation='NOT RUN')
