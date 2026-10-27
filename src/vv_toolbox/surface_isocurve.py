"""Topology of a piecewise-linear scalar zero contour on a triangle surface."""
import numpy as np


def extract_surface_isocurve(vertices,faces,values):
    vertices=np.asarray(vertices,dtype=float);faces=np.asarray(faces);values=np.asarray(values,dtype=float)
    if (vertices.ndim!=2 or vertices.shape[1]!=3 or not len(vertices)
            or faces.ndim!=2 or faces.shape[1]!=3 or not len(faces)
            or not np.issubdtype(faces.dtype,np.integer) or faces.min()<0 or faces.max()>=len(vertices)
            or values.shape!=(len(vertices),) or not np.isfinite(values).all()
            or not np.isfinite(vertices).all()):
        raise ValueError('finite mesh and per-vertex values required')
    if np.any(np.abs(values)<=1e-12):
        return dict(status='UNKNOWN',reason='zero-valued vertices require explicit degeneracy handling',components=[])
    crossing={};adjacency={};segments=[]
    for face in faces:
        keys=[]
        for a,b in zip(face,np.roll(face,-1)):
            a,b=int(a),int(b)
            if (values[a]<0)==(values[b]<0):
                continue
            key=tuple(sorted((a,b)))
            if key not in crossing:
                t=values[a]/(values[a]-values[b])
                crossing[key]=(vertices[a]+t*(vertices[b]-vertices[a])).tolist()
            keys.append(key)
        if len(keys)==2:
            a,b=keys
            adjacency.setdefault(a,[]).append(b)
            adjacency.setdefault(b,[]).append(a)
            segments.append([crossing[a],crossing[b]])
    remaining=set(adjacency);components=[]
    while remaining:
        seed=min(remaining);stack=[seed];seen=set()
        while stack:
            node=stack.pop()
            if node in seen:
                continue
            seen.add(node);stack.extend(adjacency[node])
        remaining-=seen
        closed=all(len(adjacency[node])==2 for node in seen)
        ordered=[]
        if closed:
            previous=None;node=seed
            while True:
                ordered.append(node)
                nxt=next(n for n in adjacency[node] if n!=previous)
                previous,node=node,nxt
                if node==seed:
                    break
        else:
            ordered=sorted(seen)
        points=np.array([crossing[node] for node in ordered])
        components.append(dict(closed=closed,point_count=len(points),points_mm=points.tolist(),
            bounds_mm=[points.min(axis=0).tolist(),points.max(axis=0).tolist()]))
    return dict(status='EXTRACTED',components=components,segment_count=len(segments),
        scope='zero contour of linearly interpolated vertex values; not exact nonlinear profile intersection')
