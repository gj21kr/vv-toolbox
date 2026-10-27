"""Conservative nonincident-edge capsule clearance screening in millimetres."""
from itertools import combinations
import math

import numpy as np

from .case_contract import validate_case


def _arc_separated_distance(a, b, c, d, gap, window):
    """Minimum distance on segment parameter square clipped by arc separation."""
    u, v = b-a, d-c
    lu, lv = float(np.linalg.norm(u)), float(np.linalg.norm(v))
    value = lambda x: gap + x[1]*lv - x[0]*lu - window
    square = [np.array(x, dtype=float) for x in [(0,0),(1,0),(1,1),(0,1)]]
    polygon = []
    for p, q in zip(square, square[1:]+square[:1]):
        fp, fq = value(p), value(q)
        if fp >= 0:
            polygon.append(p)
        if (fp < 0) != (fq < 0):
            polygon.append(p + fp/(fp-fq)*(q-p))
    if not polygon:
        return None
    matrix, offset = np.column_stack([u, -v]), a-c
    candidates = list(polygon)
    for p, q in zip(polygon, polygon[1:]+polygon[:1]):
        direction = matrix @ (q-p)
        norm = float(direction @ direction)
        if norm > 0:
            t = np.clip(-float((offset+matrix@p)@direction)/norm, 0, 1)
            candidates.append(p+t*(q-p))
    stationary = np.linalg.lstsq(matrix, -offset, rcond=None)[0]
    if np.all(stationary >= 0) and np.all(stationary <= 1) and value(stationary) >= 0:
        candidates.append(stationary)
    return min(float(np.linalg.norm(offset+matrix@x)) for x in candidates)


def screen_self_clearance(case, edge_ids, *, local_windows_mm, margin_mm=0.,
                          max_segment_pairs=1_000_000):
    """Screen nonlocal within-edge capsules, including adjacent coarse intervals.

    Arc distances below each explicit local window are NOT checked. A window
    must exceed the largest diameter plus margin; same-interval points are then
    safe because their straight-line distance equals their arc separation.
    """
    validate_case(case)
    by_id = {e['id']:e for e in case['edges']}
    if (not isinstance(edge_ids,list) or not edge_ids or
            not all(isinstance(e,str) and e in by_id for e in edge_ids) or
            len(set(edge_ids)) != len(edge_ids)):
        raise ValueError('unique known edge IDs required')
    if type(margin_mm) not in (int,float) or not math.isfinite(margin_mm) or margin_mm < 0:
        raise ValueError('finite nonnegative margin required')
    if type(max_segment_pairs) is not int or max_segment_pairs < 1:
        raise ValueError('positive segment pair budget required')
    if not isinstance(local_windows_mm,dict) or set(local_windows_mm)!=set(edge_ids):
        raise ValueError('explicit local window for every selected edge required')
    examined, checked, exempt, conflicts = 0, 0, 0, []
    for ident in edge_ids:
        edge = by_id[ident]
        if edge['centerline_mm'] is None or edge['start']==edge['end']:
            raise ValueError('open centerline paths required')
        p, r = np.asarray(edge['centerline_mm'],dtype=float), np.asarray(edge['radii_mm'])
        window = local_windows_mm[ident]
        if (type(window) not in (int,float) or not math.isfinite(window) or
                window <= 2*float(r.max())+margin_mm):
            raise ValueError('local window must exceed maximum diameter plus margin')
        arc = np.r_[0.,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))]
        found = False
        for i in range(len(p)-1):
            for j in range(i+1,len(p)-1):
                if examined >= max_segment_pairs:
                    return dict(status='UNKNOWN',reason='pair_budget_exhausted',
                                examined_segment_pairs=examined,potential_contacts=conflicts)
                examined += 1
                if arc[j+1]-arc[i] < window:
                    exempt += 1
                    continue
                radii_sum = float(max(r[i:i+2])+max(r[j:j+2]))
                gap = np.maximum(np.maximum(p[i:i+2].min(0)-p[j:j+2].max(0),
                                            p[j:j+2].min(0)-p[i:i+2].max(0)),0)
                checked += 1
                if np.linalg.norm(gap) > radii_sum+margin_mm:
                    continue
                distance = _arc_separated_distance(p[i],p[i+1],p[j],p[j+1],arc[j]-arc[i],window)
                if distance is not None and distance-radii_sum <= margin_mm:
                    conflicts.append(dict(edge_id=ident,intervals=[i,j],
                                          clearance_lower_bound_mm=float(distance-radii_sum)))
                    found = True
                    break
            if found:
                break
    return dict(status='UNKNOWN' if conflicts else 'PASS',
                scope='within-edge capsules at arc separations at least the explicit local window',
                local_windows_mm=dict(local_windows_mm),margin_mm=margin_mm,
                examined_segment_pairs=examined,checked_segment_pairs=checked,
                locally_exempt_segment_pairs=exempt,potential_contacts=conflicts,
                local_folding='NOT CHECKED',final_surface_collision='NOT RUN')


def segment_closest_points(a, b, c, d):
    """Return minimum distance, interpolation parameters and witness points."""
    a, b, c, d = (np.asarray(p, dtype=float) for p in (a,b,c,d))
    u, v, w = b-a, d-c, a-c
    uu, vv, uv = float(u@u), float(v@v), float(u@v)
    if uu <= 0 or vv <= 0:
        raise ValueError('nonzero segments required')
    clamp = lambda x: max(0.0, min(1.0, x))
    candidates = [(0,clamp(float(v@w)/vv)), (1,clamp(float(v@(b-c))/vv)),
                  (clamp(float(u@(c-a))/uu),0), (clamp(float(u@(d-a))/uu),1)]
    uw, vw = float(u@w), float(v@w)
    determinant = uu*vv-uv*uv
    if determinant > 0:
        s, t = (uv*vw-vv*uw)/determinant, (uu*vw-uv*uw)/determinant
        if 0 <= s <= 1 and 0 <= t <= 1:
            candidates.append((s,t))
    s, t = min(candidates, key=lambda st: float(np.linalg.norm(w+st[0]*u-st[1]*v)))
    first, second = a+s*u, c+t*v
    return float(np.linalg.norm(first-second)), float(s), float(t), first, second


def segment_distance(a, b, c, d):
    """Minimum distance between closed straight segments, including interiors."""
    return segment_closest_points(a, b, c, d)[0]


def screen_nonincident_clearance(case, edge_ids, *, margin_mm=0.0, max_segment_pairs=1_000_000,
                                focus_edge_ids=None):
    """PASS certifies the tested capsule envelopes, not final mesh separation.

    Each polyline interval is bounded by a capsule of its maximum endpoint
    radius. Potential contacts are UNKNOWN (the bound may be conservative).
    Shared-node pairs and within-edge self-intersections are explicitly untested.
    Optional focus restricts pairs to those involving at least one focus edge;
    it does not restrict the surrounding selected edges used as obstacles.
    """
    validate_case(case)
    if type(margin_mm) not in (int,float) or not math.isfinite(margin_mm) or margin_mm < 0:
        raise ValueError('finite nonnegative margin required')
    if type(max_segment_pairs) is not int or max_segment_pairs < 1:
        raise ValueError('positive segment pair budget required')
    by_id = {e['id']:e for e in case['edges']}
    if not isinstance(edge_ids,list) or not edge_ids or len(set(edge_ids)) != len(edge_ids) or any(e not in by_id for e in edge_ids):
        raise ValueError('unique known edge IDs required')
    edges = [by_id[e] for e in edge_ids]
    if focus_edge_ids is not None and (
            not isinstance(focus_edge_ids,list) or not focus_edge_ids or
            not all(isinstance(e,str) and e in edge_ids for e in focus_edge_ids) or
            len(set(focus_edge_ids)) != len(focus_edge_ids)):
        raise ValueError('focus must contain unique selected edge IDs')
    focus = set(focus_edge_ids) if focus_edge_ids is not None else set(edge_ids)
    coverage = dict(selected_edge_ids=list(edge_ids), focus_edge_ids=sorted(focus),
                    pair_policy='at least one focus edge')
    if any(e['centerline_mm'] is None for e in edges):
        raise ValueError('centerline geometry required')
    checked, skipped, conflicts, bounded = 0, [], [], 0
    for first, second in combinations(edges,2):
        if first['id'] not in focus and second['id'] not in focus:
            continue
        if {first['start'],first['end']} & {second['start'],second['end']}:
            skipped.append([first['id'],second['id']])
            continue
        p, q = np.asarray(first['centerline_mm']), np.asarray(second['centerline_mm'])
        rp, rq = np.asarray(first['radii_mm']), np.asarray(second['radii_mm'])
        boundp, boundq = float(rp.max()), float(rq.max())
        gap = np.maximum(np.maximum(p.min(0)-q.max(0),q.min(0)-p.max(0)),0)
        if float(np.linalg.norm(gap)) > boundp + boundq + margin_mm:
            bounded += 1
            continue
        qlo, qhi = np.minimum(q[:-1], q[1:]), np.maximum(q[:-1], q[1:])
        qr = np.maximum(rq[:-1], rq[1:])
        for i in range(len(p)-1):
            # Vectorized interval boxes reject distant intervals without changing
            # pair accounting, ordering, or the first reported witness.
            gaps = np.maximum(np.maximum(np.minimum(p[i],p[i+1])-qhi,
                                         qlo-np.maximum(p[i],p[i+1])),0)
            possible = np.linalg.norm(gaps,axis=1) <= max(rp[i:i+2])+qr+margin_mm
            for j in range(len(q)-1):
                if checked >= max_segment_pairs:
                    return {'status':'UNKNOWN','reason':'pair_budget_exhausted','checked_segment_pairs':checked,
                            'potential_contacts':conflicts,'shared_node_pairs_not_checked':skipped,
                            'coverage':coverage}
                checked += 1
                if not possible[j]:
                    continue
                clearance = segment_distance(p[i],p[i+1],q[j],q[j+1]) - max(rp[i:i+2]) - max(rq[j:j+2])
                if clearance <= margin_mm:
                    conflicts.append({'edges':[first['id'],second['id']], 'intervals':[i,j],
                                      'clearance_lower_bound_mm':float(clearance)})
                    # One witness is sufficient to reject this pair; retain both edge IDs.
                    break
            else:
                continue
            break
    return {'status':'UNKNOWN' if conflicts else 'PASS',
            'scope':'nonincident edge conservative capsule envelopes only',
            'coverage':coverage,
            'margin_mm':margin_mm,'checked_segment_pairs':checked,'bbox_separated_pairs':bounded,
            'potential_contacts':conflicts,'shared_node_pairs_not_checked':skipped,
            'within_edge_self_intersection':'NOT RUN','final_surface_collision':'NOT RUN'}


def screen_junction_clearance(case, edge_ids, *, collars_mm, margin_mm=0.0,
                              max_segment_pairs=1_000_000):
    """Check incident paths outside explicit endpoint arc-length collars.

    Only two intervals wholly inside the SAME shared-node collar are exempt.
    Splitting intervals at collar limits prevents coarse sampling from hiding a
    remote crossing. Collars are synthetic modeling allowances, not anatomy.
    """
    validate_case(case)
    by_id = {e['id']: e for e in case['edges']}
    if (not isinstance(edge_ids, list) or not edge_ids or
            not all(isinstance(e, str) and e in by_id for e in edge_ids) or
            len(set(edge_ids)) != len(edge_ids)):
        raise ValueError('unique known edge IDs required')
    if type(margin_mm) not in (int, float) or not math.isfinite(margin_mm) or margin_mm < 0:
        raise ValueError('finite nonnegative margin required')
    if type(max_segment_pairs) is not int or max_segment_pairs < 1:
        raise ValueError('positive segment pair budget required')
    if not isinstance(collars_mm, dict) or any(
            n not in case['nodes'] or type(v) not in (int, float) or
            not math.isfinite(v) or v <= 0 for n, v in collars_mm.items()):
        raise ValueError('positive finite named junction collars required')
    edges = [by_id[e] for e in edge_ids]
    if any(e['centerline_mm'] is None or e['start'] == e['end'] for e in edges):
        raise ValueError('open centerline paths required')
    checked, exempt, conflicts, unresolved = 0, 0, [], []

    def intervals(edge, shared):
        points = np.asarray(edge['centerline_mm'], dtype=float)
        radii = np.asarray(edge['radii_mm'], dtype=float)
        arc = np.r_[0., np.cumsum(np.linalg.norm(np.diff(points, axis=0), axis=1))]
        length = float(arc[-1])
        widths = [collars_mm[n] for n in shared]
        if sum(widths) >= length:
            return None
        cuts = [collars_mm[n] if n == edge['start'] else length-collars_mm[n] for n in shared]
        positions = np.unique(np.r_[arc, cuts])
        p = np.column_stack([np.interp(positions, arc, points[:, k]) for k in range(3)])
        r = np.interp(positions, arc, radii)
        result = []
        for i, (lo, hi) in enumerate(zip(positions[:-1], positions[1:])):
            inside = {n for n in shared if
                      (hi <= collars_mm[n] if n == edge['start'] else lo >= length-collars_mm[n])}
            result.append((p[i], p[i+1], max(r[i:i+2]), inside, [float(lo), float(hi)]))
        return result

    for first, second in combinations(edges, 2):
        shared = {first['start'], first['end']} & {second['start'], second['end']}
        if not shared:
            continue
        if not shared <= collars_mm.keys():
            raise ValueError('every shared node requires an explicit collar')
        p, q = intervals(first, shared), intervals(second, shared)
        if p is None or q is None:
            unresolved.append([first['id'], second['id']])
            continue
        found = False
        for a, b, radius_p, zone_p, arc_p in p:
            for c, d, radius_q, zone_q, arc_q in q:
                if checked + exempt >= max_segment_pairs:
                    return dict(status='UNKNOWN', reason='pair_budget_exhausted',
                                checked_segment_pairs=checked, exempt_segment_pairs=exempt,
                                potential_contacts=conflicts, collar_consumed_edge_pairs=unresolved)
                if zone_p & zone_q:
                    exempt += 1
                    continue
                checked += 1
                clearance = segment_distance(a, b, c, d)-radius_p-radius_q
                if clearance <= margin_mm:
                    conflicts.append(dict(edges=[first['id'], second['id']],
                                          arc_intervals_mm=[arc_p, arc_q],
                                          clearance_lower_bound_mm=float(clearance)))
                    found = True
                    break
            if found:
                break
    return dict(status='UNKNOWN' if conflicts or unresolved else 'PASS',
                scope='incident-edge capsules outside explicit shared-node arc collars',
                collars_mm=dict(collars_mm), margin_mm=margin_mm,
                checked_segment_pairs=checked, exempt_segment_pairs=exempt,
                potential_contacts=conflicts, collar_consumed_edge_pairs=unresolved,
                inside_junction_collars='NOT CHECKED',
                within_edge_self_intersection='NOT RUN', final_surface_collision='NOT RUN')
