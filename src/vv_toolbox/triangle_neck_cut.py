"""Partition one source triangle by a convex projected neck polygon.

Outputs are barycentric polygons, not an assembled or accepted lumen mesh.
No point is lifted from a reconstructed collar: all points stay on the source.
"""
import numpy as np


def partition_triangle(projected_triangle, neck_polygon):
    triangle=np.asarray(projected_triangle,float)
    polygon=np.asarray(neck_polygon,float)
    if (triangle.shape!=(3,2) or polygon.ndim!=2 or polygon.shape[1]!=2
            or len(polygon)<3 or not np.isfinite(triangle).all()
            or not np.isfinite(polygon).all()):
        raise ValueError('Finite projected triangle and convex polygon required')
    def cross(a,b):return a[...,0]*b[...,1]-a[...,1]*b[...,0]
    if abs(cross(triangle[1]-triangle[0],triangle[2]-triangle[0]))<=1e-12:
        raise ValueError('Nondegenerate projected triangle required')
    area=sum(cross(a,b) for a,b in zip(polygon,np.roll(polygon,-1,axis=0)))
    if abs(area)<=1e-12:raise ValueError('Nondegenerate convex neck polygon required')
    if area<0:polygon=polygon[::-1]
    for a,b in zip(polygon,np.roll(polygon,-1,axis=0)):
        if np.linalg.norm(b-a)<=1e-12 or np.any(cross(b-a,polygon-a)<-1e-12):
            raise ValueError('Convex neck polygon with distinct adjacent points required')

    def clip(points,distances,positive):
        result=[]
        for i,p in enumerate(points):
            q=points[(i+1)%len(points)];dp=distances[i];dq=distances[(i+1)%len(points)]
            pin=dp>=0 if positive else dp<=0
            qin=dq>=0 if positive else dq<=0
            if pin:result.append(p)
            if pin!=qin:result.append(p+(q-p)*(dp/(dp-dq)))
        clean=[]
        for p in result:
            if not clean or np.linalg.norm(p-clean[-1])>1e-12:clean.append(p)
        if len(clean)>1 and np.linalg.norm(clean[0]-clean[-1])<=1e-12:clean.pop()
        if len(clean)<3:return np.empty((0,3))
        points=np.asarray(clean)
        # Barycentric area avoids mistaking a line contact for a surface piece.
        xy=points[:,1:]
        if abs(sum(cross(a,b) for a,b in zip(xy,np.roll(xy,-1,axis=0))))<=1e-14:
            return np.empty((0,3))
        return points

    remaining=np.eye(3);outside=[]
    for a,b in zip(polygon,np.roll(polygon,-1,axis=0)):
        if not len(remaining):break
        distances=cross(b-a,remaining@triangle-a)
        piece=clip(remaining,distances,False)
        if len(piece):outside.append(piece)
        remaining=clip(remaining,distances,True)
    return remaining,outside
