"""Bounded projection on a separate mesh copy with exact protected vertices."""
from collections import deque
import numpy as np
import trimesh


def fit_protected_surface(source, target, protected_vertex_ids, *,
                          max_displacement_mm, transition_rings=3):
    """Preserve source faces and weld-equivalent positions; taper from fixed rings.

    Protected IDs are caller-declared. This does not identify anatomical junctions
    or certify contact preservation with unlisted neighboring geometry.
    """
    vertices=np.asarray(source.vertices,dtype=float)
    faces=np.asarray(source.faces)
    if (type(max_displacement_mm) not in (int,float)
            or not np.isfinite(max_displacement_mm) or max_displacement_mm<=0
            or type(transition_rings) is not int or not 1<=transition_rings<=100
            or not isinstance(protected_vertex_ids,list)
            or not protected_vertex_ids
            or any(type(i) is not int or not 0<=i<len(vertices) for i in protected_vertex_ids)):
        raise ValueError('Explicit protected vertices, positive bound and transition rings required')
    if not len(faces) or not len(target.faces) or not np.isfinite(vertices).all():
        raise ValueError('Finite nonempty source and target meshes required')
    unique,inverse=np.unique(vertices,axis=0,return_inverse=True)
    fixed=set(inverse[protected_vertex_ids].tolist())
    adjacency=[set() for _ in unique]
    for a,b,c in inverse[faces]:
        adjacency[a].update((int(b),int(c)))
        adjacency[b].update((int(a),int(c)))
        adjacency[c].update((int(a),int(b)))
    depth=np.full(len(unique),transition_rings,dtype=int)
    queue=deque(fixed)
    for i in fixed:depth[i]=0
    while queue:
        i=queue.popleft()
        if depth[i]>=transition_rings:continue
        for j in adjacency[i]:
            if depth[j]>depth[i]+1:
                depth[j]=depth[i]+1;queue.append(j)
    nearest,_,_=trimesh.proximity.closest_point(target,unique)
    weight=np.clip(depth/transition_rings,0,1).astype(float)
    weight=weight*weight*(3-2*weight)
    fitted=unique+(nearest-unique)*weight[:,None]
    fitted[list(fixed)]=unique[list(fixed)]
    delta=np.linalg.norm(fitted-unique,axis=1)
    if not np.isfinite(fitted).all() or max(delta)>max_displacement_mm:
        raise ValueError('Projection exceeds declared displacement bound')
    output=fitted[inverse]
    before=vertices[faces];after=output[faces]
    nb=np.cross(before[:,1]-before[:,0],before[:,2]-before[:,0])
    na=np.cross(after[:,1]-after[:,0],after[:,2]-after[:,0])
    if np.any(np.linalg.norm(na,axis=1)<=1e-12) or np.any(np.sum(na*nb,axis=1)<=0):
        raise ValueError('Projection degenerates or reverses a source triangle')
    mesh=trimesh.Trimesh(output,faces.copy(),process=False)
    return mesh,dict(method='protected-source-projection/1',status='CANDIDATE',
        protected_vertices=int(np.isin(inverse,list(fixed)).sum()),
        moved_vertices=int(np.count_nonzero(delta[inverse]>1e-12)),
        maximum_displacement_mm=float(max(delta)),displacement_bound_mm=max_displacement_mm,
        transition_rings=transition_rings,faces_unchanged=bool(np.array_equal(mesh.faces,faces)),
        protected_positions_unchanged=bool(np.array_equal(output[protected_vertex_ids],vertices[protected_vertex_ids])),
        duplicate_positions_preserved=True,self_contact='NOT RUN',surroundings='NOT RUN',
        anatomical_validation='NOT RUN')
