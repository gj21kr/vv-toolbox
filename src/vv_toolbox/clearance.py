"""Conservative cross-circuit capsule proxy, not a triangle-surface collision test."""
from itertools import combinations
import numpy as np


def _capsules(edge):
    radii=np.full(len(edge.points),edge.radius_mm) if edge.radius_profile_mm is None else edge.radius_profile_mm
    return edge.points[:-1],np.diff(edge.points,axis=0),np.maximum(radii[:-1],radii[1:])


def _clearance(a,b):
    p,u,r=_capsules(a); q,v,s=_capsules(b)
    w=p[:,None,:]-q[None,:,:]
    aa=np.sum(u*u,axis=1)[:,None];bb=u@v.T;cc=np.sum(v*v,axis=1)[None,:]
    dd=np.einsum('ijk,ik->ij',w,u);ee=np.einsum('ijk,jk->ij',w,v)
    def distance(t,h):
        return np.sum((w+t[...,None]*u[:,None,:]-h[...,None]*v[None,:,:])**2,axis=2)
    zero=np.zeros_like(bb);one=np.ones_like(bb)
    best=np.minimum.reduce([distance(zero,np.clip(ee/cc,0,1)),distance(one,np.clip((ee+bb)/cc,0,1)),
                            distance(np.clip(-dd/aa,0,1),zero),distance(np.clip((bb-dd)/aa,0,1),one)])
    det=aa*cc-bb*bb
    valid=det>np.finfo(float).eps*16*aa*cc
    t=np.divide(bb*ee-cc*dd,det,out=zero.copy(),where=valid)
    h=np.divide(aa*ee-bb*dd,det,out=zero.copy(),where=valid)
    interior=valid & (t>=0)&(t<=1)&(h>=0)&(h<=1)
    best=np.minimum(best,np.where(interior,distance(t,h),np.inf))
    return float(np.min(np.sqrt(np.maximum(best,0))-r[:,None]-s[None,:]))


def cross_circuit_clearance(graphs):
    """Exact polyline segment distances minus enclosing per-capsule radii.

    Radius maxima conservatively bound linearly varying profiles. A negative
    clearance is a potential overlap of this proxy; mesh fillets are not included.
    """
    collisions=[];minimum=float('inf');closest=None
    for graph in graphs.values():graph.validate()
    for (layer_a,a),(layer_b,b) in combinations(graphs.items(),2):
        for edge_a in a.segments:
            for edge_b in b.segments:
                # AABB lower bound cheaply excludes distant vessel pairs.
                ra=float(np.max(_capsules(edge_a)[2]));rb=float(np.max(_capsules(edge_b)[2]))
                gap=np.maximum(np.maximum(edge_a.points.min(0)-edge_b.points.max(0),edge_b.points.min(0)-edge_a.points.max(0)),0)
                if np.linalg.norm(gap)-ra-rb>max(0.,minimum):continue
                value=_clearance(edge_a,edge_b)
                record=dict(layer_a=layer_a,layer_b=layer_b,vessel_a=edge_a.name,vessel_b=edge_b.name,clearance_mm=value)
                if value<minimum:minimum,closest=value,record
                if value<=0:collisions.append(record)
    return dict(status='OVERLAP' if collisions else 'CLEAR',potential_collisions=sorted(collisions,key=lambda x:x['clearance_mm']),
                minimum_clearance_mm=minimum if np.isfinite(minimum) else None,closest_pair=closest,
                method='Exact polyline capsule distance; per-capsule maximum endpoint radius conservatively bounds radius profiles',
                limitations='Centerline/radius proxy only; excludes reconstructed mesh fillets, organ boundaries and anatomical validity. CLEAR does not certify surface separation.')
