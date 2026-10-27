"""Finite-precision self-contact screening including shared-topology pairs."""
import numpy as np
from scipy.spatial import cKDTree
from .triangle_contact import triangle_contacts
from .adjacent_contact import overlap_beyond_shared


def inspect_self_contact(vertices, faces, *, tolerance_mm=1e-8, max_pairs=2_000_000):
    vertices=np.asarray(vertices,dtype=float);faces=np.asarray(faces)
    if (vertices.ndim!=2 or vertices.shape[1]!=3 or not np.isfinite(vertices).all() or
            faces.ndim!=2 or faces.shape[1]!=3 or not len(faces) or
            not np.issubdtype(faces.dtype,np.integer) or faces.min()<0 or faces.max()>=len(vertices) or
            not np.isfinite(tolerance_mm) or tolerance_mm<=0 or
            type(max_pairs) is not int or max_pairs<1):
        raise ValueError('Valid triangles, positive tolerance and pair budget required')
    triangles=vertices[faces]
    area2=np.linalg.norm(np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0]),axis=1)
    if np.any(area2<=1e-12):
        return dict(status='UNKNOWN',coverage='degenerate input triangles',
                    degenerate_face_ids=np.flatnonzero(area2<=1e-12).tolist(),
                    contact_pairs=[],checked_pairs=0)
    centers=triangles.mean(axis=1)
    radii=np.linalg.norm(triangles-centers[:,None],axis=2).max(axis=1)
    tree=cKDTree(centers);max_radius=float(radii.max())
    low,high=triangles.min(axis=1),triangles.max(axis=1)
    checked=0;adjacent_checked=0;contacts=[];complete=True
    for i in range(len(faces)):
        ids=np.asarray(tree.query_ball_point(centers[i],radii[i]+max_radius+tolerance_mm),dtype=int)
        ids=ids[ids>i]
        ids=ids[np.all(low[ids]<=high[i]+tolerance_mm,axis=1)&
                np.all(high[ids]>=low[i]-tolerance_mm,axis=1)]
        if checked+len(ids)>max_pairs:
            complete=False
            break
        adjacent=np.isin(faces[ids],faces[i]).any(axis=1)
        for j in ids[adjacent]:
            shared=np.intersect1d(faces[i],faces[j])
            if len(shared)==3 or overlap_beyond_shared(triangles[i],triangles[j],vertices[shared],tolerance_mm):
                contacts.append([i,int(j)])
        other=ids[~adjacent]
        if len(other):
            hit=triangle_contacts(np.broadcast_to(triangles[i],(len(other),3,3)),triangles[other],tolerance_mm)
            contacts.extend([i,int(j)] for j in other[hit])
        checked+=len(ids);adjacent_checked+=int(adjacent.sum())
    return dict(status='CONTACT_DETECTED' if contacts else 'NO_CONTACT_DETECTED' if complete else 'UNKNOWN',
                coverage='all distinct triangle pairs' if complete else 'pair budget exhausted',
                checked_pairs=checked,adjacent_pairs_checked=adjacent_checked,
                contact_pairs=contacts,tolerance_mm=tolerance_mm,max_pairs=max_pairs,
                limitations='Finite-precision tests, not exact predicates. Other vessels not checked. Adjacent pairs check overlap beyond shared topology, not clearance.')
