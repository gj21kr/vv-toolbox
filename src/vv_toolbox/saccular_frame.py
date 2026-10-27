"""Explicit engineering frame proposal with local parallel transport."""
import math
import numpy as np
from .case_contract import validate_case
from .case_io import case_digest
from .saccular import _vector


def propose_saccular_frame(case, edge_id, station_mm, reference_direction, *, search_mm):
    """Project a supplied reference or transport it from a nearby usable segment.

    No automatic world-axis substitute, geometry modification or attachment
    acceptance. Reversing extraction order need not preserve the width axis.
    """
    validate_case(case)
    for name,value in [('station',station_mm),('search distance',search_mm)]:
        if type(value) not in (int,float) or not math.isfinite(value) or value<=0:
            raise ValueError(f'positive finite {name} required')
    reference=_vector(reference_direction,'reference direction')
    if np.linalg.norm(reference)<1e-12:
        raise ValueError('nonzero reference direction required')
    reference/=np.linalg.norm(reference)
    edge=next((e for e in case['edges'] if e['id']==edge_id),None)
    if edge is None or edge['centerline_mm'] is None:
        raise ValueError('resolved parent edge required')
    points=np.asarray(edge['centerline_mm'],dtype=float)
    radii=np.asarray(edge['radii_mm'],dtype=float)
    lengths=np.linalg.norm(np.diff(points,axis=0),axis=1)
    stations=np.r_[0.,np.cumsum(lengths)]
    if station_mm>=stations[-1]:
        raise ValueError('interior parent station required')
    target=int(np.searchsorted(stations,station_mm,side='right')-1)
    tangents=np.diff(points,axis=0)/lengths[:,None]
    projected=reference-tangents*(tangents@reference)[:,None]
    norms=np.linalg.norm(projected,axis=1)
    if norms[target]>1e-6:
        seed=target
    else:
        # Distance to a segment interval (not sample index) sets search scope.
        distances=np.maximum.reduce([stations[:-1]-station_mm,
                                      station_mm-stations[1:],np.zeros(len(lengths))])
        eligible=np.flatnonzero((norms>1e-6)&(distances<=search_mm))
        if not len(eligible):
            raise ValueError('no nonparallel reference in search window; explicit alternative direction required')
        seed=min(eligible,key=lambda i:(distances[i],abs(i-target),i))
    normal=projected[seed]/norms[seed]
    step=1 if target>=seed else -1
    for i in range(seed,target,step):
        a,b=tangents[i],tangents[i+step]
        cross=np.cross(a,b)
        cosine=float(np.clip(a@b,-1,1))
        if cosine < -1+1e-8:
            raise ValueError('antiparallel tangent makes transport ambiguous')
        # Minimal rotation: Rv = v + k x v + k x (k x v)/(1+c).
        normal=normal+np.cross(cross,normal)+np.cross(cross,np.cross(cross,normal))/(1+cosine)
        normal-=b*(normal@b)
        normal/=np.linalg.norm(normal)
    fraction=float((station_mm-stations[target])/lengths[target])
    anchor=points[target]+fraction*(points[target+1]-points[target])
    radius=float(radii[target]+fraction*(radii[target+1]-radii[target]))
    return dict(schema='vv-toolbox.saccular-frame-proposal/1',status='CANDIDATE',
        case_revision=case_digest(case),edge_id=edge_id,station_mm=station_mm,
        reference_direction=reference.tolist(),search_mm=search_mm,
        seed_interval=int(seed),target_interval=target,
        method='direct projection' if seed==target else 'nearby segment parallel transport',
        outward_normal=normal.tolist(),width_direction=tangents[target].tolist(),
        neck_center_mm=(anchor+radius*normal).tolist(),
        anatomical_direction='UNKNOWN',attachment_acceptance='NOT RUN')
