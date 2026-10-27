"""Ordered mesh-index boundary loops of an explicitly selected face region."""
import numpy as np


def patch_boundary_loops(faces,selected_faces):
    faces=np.asarray(faces);selected=np.asarray(selected_faces)
    if (faces.ndim!=2 or faces.shape[1]!=3 or not np.issubdtype(faces.dtype,np.integer)
            or np.any(faces<0) or selected.ndim!=1 or not len(selected)
            or not np.issubdtype(selected.dtype,np.integer) or selected.min()<0
            or selected.max()>=len(faces) or len(set(selected.tolist()))!=len(selected)):
        raise ValueError('valid faces and unique selected face indices required')
    patch=faces[selected]
    if np.any(np.diff(np.sort(patch,axis=1),axis=1)==0):
        raise ValueError('degenerate face indices')
    edges=np.sort(np.concatenate([patch[:,[0,1]],patch[:,[1,2]],patch[:,[2,0]]]),axis=1)
    unique,counts=np.unique(edges,axis=0,return_counts=True)
    if np.any(counts>2):
        raise ValueError('nonmanifold patch edge')
    boundary=unique[counts==1]
    adjacency={}
    for a,b in boundary:
        adjacency.setdefault(int(a),[]).append(int(b))
        adjacency.setdefault(int(b),[]).append(int(a))
    if any(len(neighbors)!=2 for neighbors in adjacency.values()):
        raise ValueError('boundary is not a set of simple closed loops')
    remaining=set(adjacency);loops=[]
    while remaining:
        start=min(remaining);previous=None;current=start;loop=[]
        while True:
            if current in loop:
                raise ValueError('self-touching boundary topology')
            loop.append(current);remaining.remove(current)
            choices=sorted(n for n in adjacency[current] if n!=previous)
            previous,current=current,choices[0]
            if current==start:break
        loops.append(loop)
    return loops


def vertices_to_closed_curve_distance(points,curve):
    points=np.asarray(points,dtype=float);curve=np.asarray(curve,dtype=float)
    if (points.ndim!=2 or points.shape[1]!=3 or not len(points) or
            curve.ndim!=2 or curve.shape[1]!=3 or len(curve)<3 or
            not np.isfinite(points).all() or not np.isfinite(curve).all()):
        raise ValueError('finite points and closed polygon required')
    delta=np.roll(curve,-1,axis=0)-curve
    length2=np.sum(delta*delta,axis=1)
    if np.any(length2<=1e-24):
        raise ValueError('degenerate polygon edge')
    result=np.full(len(points),np.inf)
    for a,d,squared in zip(curve,delta,length2):
        t=np.clip((points-a)@d/squared,0,1)
        result=np.minimum(result,np.linalg.norm(points-a-t[:,None]*d,axis=1))
    return result
