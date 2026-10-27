"""Adaptive whole-interval containment bounds against unchanged source triangles."""
import math

import numpy as np
import trimesh

from .surface_indexing import exact_vertex_index_copy

# Bound simultaneous ray/nearest-triangle queries, not the inspected path.
# Trimesh can allocate large triangle candidate arrays per query batch.
_QUERY_BATCH_SIZE = 128


def inspect_centerline_containment(mesh, points, *, tolerance_mm=1e-6,
                                  max_depth=16, max_cells=100000):
    return _inspect_containment(mesh, points, tolerance_mm=tolerance_mm,
                                max_depth=max_depth, max_cells=max_cells)


def inspect_radius_envelope_containment(mesh, points, radii_mm, *, tolerance_mm=1e-6,
                                       max_depth=16, max_cells=100000):
    """Inspect the union of balls with linearly interpolated centers and radii.

    This envelope contains circular normal sections but can extend beyond tube
    end caps. A failed envelope is not proof that a reconstructed tube wall exits.
    """
    if radii_mm is None:
        raise ValueError('Positive radius at every centerline point required')
    return _inspect_containment(mesh, points, radii_mm=radii_mm,
                                tolerance_mm=tolerance_mm, max_depth=max_depth,
                                max_cells=max_cells)


def _inspect_containment(mesh, points, *, radii_mm=None, tolerance_mm=1e-6,
                         max_depth=16, max_cells=100000):
    """Cover intervals with interior balls, or return an outside witness/UNKNOWN.

    Distance to the nearest triangle is 1-Lipschitz. A midpoint whose distance
    exceeds half the cell length plus tolerance certifies that whole cell stays
    off the boundary, assuming the closed surface represents a valid solid.
    Computations are floating-point, not exact arithmetic or anatomical proof.
    """
    points=np.asarray(points,dtype=float)
    if (points.ndim!=2 or points.shape[1]!=3 or len(points)<2
            or not np.isfinite(points).all()
            or np.any(np.linalg.norm(np.diff(points,axis=0),axis=1)<=0)):
        raise ValueError('Finite nondegenerate polyline required')
    radii=None if radii_mm is None else np.asarray(radii_mm,dtype=float)
    if radii is not None and (radii.shape!=(len(points),) or
                             not np.isfinite(radii).all() or np.any(radii<=0)):
        raise ValueError('Positive radius at every centerline point required')
    if (type(tolerance_mm) not in (int,float) or not math.isfinite(tolerance_mm) or tolerance_mm<=0
            or type(max_depth) is not int or not 0<=max_depth<=24
            or type(max_cells) is not int or not 1<=max_cells<=1000000):
        raise ValueError('Positive tolerance and bounded subdivision budget required')
    normalized,indexing=exact_vertex_index_copy(mesh)
    report=dict(status='UNKNOWN',method='interior-midpoint-ball-cover/1',
        scope='whole polyline intervals under floating-point closed-solid assumptions',
        tolerance_mm=tolerance_mm,max_depth=max_depth,max_cells=max_cells,
        query_batch_size=_QUERY_BATCH_SIZE,
        indexing=indexing,segment_count=len(points)-1,processed_cells=0,covered_cells=0,
        unresolved_segments=[],outside_witnesses=[],maximum_depth_used=0,
        minimum_cover_margin_mm=None,
        surface_self_intersection='NOT RUN',anatomical_validation='NOT RUN')
    if radii is not None:
        report.update(method='linear-radius-ball-envelope/1',
            scope='union of linearly interpolated radius balls under floating-point closed-solid assumptions',
            radius_exceedance_witnesses=[],tube_wall_containment='NOT RUN')
    if not indexing['usable_for_sampled_containment']:
        report['reason']='closed consistently oriented nondegenerate triangles required'
        return report
    pending=[(i,0.,1.,0) for i in range(len(points)-1)]
    unresolved=set()
    while pending:
        available=max_cells-report['processed_cells']
        if available<=0:
            unresolved.update(i for i,_,_,_ in pending)
            report['reason']='subdivision cell budget exhausted'
            break
        batch=pending[:min(available,_QUERY_BATCH_SIZE)];pending=pending[len(batch):]
        indices=np.asarray([i for i,_,_,_ in batch])
        lo=np.asarray([a for _,a,_,_ in batch]);hi=np.asarray([b for _,_,b,_ in batch])
        delta=points[indices+1]-points[indices]
        middle=(lo+hi)/2
        query=points[indices]+middle[:,None]*delta
        _,distance,_=trimesh.proximity.closest_point(normalized,query)
        inside=normalized.contains(query)
        report['processed_cells']+=len(batch)
        for k,(ident,start,stop,depth) in enumerate(batch):
            report['maximum_depth_used']=max(report['maximum_depth_used'],depth)
            if not np.isfinite(distance[k]) or distance[k]<=tolerance_mm:
                unresolved.add(ident)
                continue
            if not inside[k]:
                report['outside_witnesses'].append(dict(segment_index=ident,
                    fraction=float(middle[k]),position_mm=query[k].tolist(),
                    distance_to_surface_mm=float(distance[k])))
                continue
            half_length=np.linalg.norm(delta[k])*(stop-start)/2
            max_radius=0.
            if radii is not None:
                dr=radii[ident+1]-radii[ident]
                midpoint_radius=radii[ident]+middle[k]*dr
                if midpoint_radius>distance[k]+tolerance_mm:
                    report['radius_exceedance_witnesses'].append(dict(
                        segment_index=ident,fraction=float(middle[k]),
                        position_mm=query[k].tolist(),radius_mm=float(midpoint_radius),
                        distance_to_surface_mm=float(distance[k]),
                        excess_mm=float(midpoint_radius-distance[k])))
                    continue
                max_radius=max(radii[ident]+start*dr,radii[ident]+stop*dr)
            if distance[k]>half_length+max_radius+tolerance_mm:
                report['covered_cells']+=1
                margin=float(distance[k]-half_length-max_radius-tolerance_mm)
                previous=report['minimum_cover_margin_mm']
                report['minimum_cover_margin_mm']=margin if previous is None else min(previous,margin)
            elif depth>=max_depth:
                unresolved.add(ident)
            else:
                mid=float(middle[k])
                pending.extend([(ident,start,mid,depth+1),(ident,mid,stop,depth+1)])
    report['unresolved_segments']=sorted(unresolved)
    failed=report['outside_witnesses'] or report.get('radius_exceedance_witnesses',[])
    report['status']='FAIL' if failed else 'UNKNOWN' if unresolved else 'PASS'
    if unresolved and 'reason' not in report:
        report['reason']='boundary proximity or depth limit leaves intervals unproven'
    return report
