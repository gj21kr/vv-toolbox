"""Classify contact faces by actual open-mesh topology, not anatomy."""
import numpy as np


def classify_patch_contacts(faces,contact_pairs):
    faces=np.asarray(faces)
    if faces.ndim!=2 or faces.shape[1]!=3 or not len(faces) or not np.issubdtype(faces.dtype,np.integer) or faces.min()<0:
        raise ValueError('Nonnegative triangle indices required')
    pairs=np.asarray(contact_pairs)
    if pairs.size==0:pairs=np.empty((0,2),dtype=np.int64)
    if pairs.ndim!=2 or pairs.shape[1]!=2 or not np.issubdtype(pairs.dtype,np.integer) or np.any(pairs<0):
        raise ValueError('Nonnegative contact face-index pairs required')
    if len(pairs) and np.any(pairs[:,0]>=len(faces)):raise ValueError('Patch contact face outside mesh')
    edges=np.sort(np.concatenate([faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]]]),axis=1)
    unique,counts=np.unique(edges,axis=0,return_counts=True)
    if np.any(counts>2):raise ValueError('Nonmanifold patch edges')
    boundary_vertices=np.unique(unique[counts==1])
    touches=np.isin(faces,boundary_vertices).any(axis=1)
    ids=np.unique(pairs[:,0])
    boundary_faces=ids[touches[ids]];interior_faces=ids[~touches[ids]]
    return dict(schema='vv-toolbox.patch-contact-regions/1',boundary_vertex_count=len(boundary_vertices),
        contacting_face_count=len(ids),boundary_incident_face_ids=boundary_faces.tolist(),
        interior_face_ids=interior_faces.tolist(),
        boundary_incident_pair_count=int(touches[pairs[:,0]].sum()),
        interior_pair_count=int((~touches[pairs[:,0]]).sum()),
        status='INTERIOR_CONTACT' if len(interior_faces) else 'BOUNDARY_INCIDENT_CONTACT' if len(ids) else 'NO_RECORDED_CONTACT',
        limitation='Boundary-incident faces may intersect away from the boundary. Interior faces have no open-boundary vertex. '
                   'No claim of intended attachment, clearance or anatomical validity.')
