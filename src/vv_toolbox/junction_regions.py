"""Explicit bounded junction allowances; never anatomical acceptance."""
from itertools import combinations
from copy import deepcopy
import math

import numpy as np

from .case_contract import validate_case
from .case_io import case_digest
from .geometry_quality import segment_distance


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _positive(value):
    return type(value) in (int, float) and math.isfinite(value) and value > 0


def inspect_junction_regions(case, edge_ids, regions, *, margin_mm=0., max_segment_pairs=1_000_000):
    """Check all distinct selected edge pairs outside bounded declared regions.

    Each region binds a case digest and consists of endpoint prefixes. A full
    edge may connect internal region nodes, but cannot replace an external arm.
    The region allowance itself is untested, not evidence of safe geometry.
    """
    validate_case(case)
    _require(case['model_kind'] == 'synthetic', 'synthetic case required')
    edges = {e['id']: e for e in case['edges']}
    _require(isinstance(edge_ids, list) and bool(edge_ids) and
             all(isinstance(e, str) and e in edges for e in edge_ids) and
             len(set(edge_ids)) == len(edge_ids), 'unique known edge IDs required')
    _require(type(margin_mm) in (int, float) and math.isfinite(margin_mm) and margin_mm >= 0,
             'finite nonnegative margin required')
    _require(type(max_segment_pairs) is int and max_segment_pairs > 0, 'positive budget required')
    _require(isinstance(regions, list) and bool(regions), 'explicit regions required')
    geometry, zones = {}, {e: [] for e in edge_ids}
    for ident in edge_ids:
        edge = edges[ident]
        p = np.asarray(edge['centerline_mm'], dtype=float)
        r = np.asarray(edge['radii_mm'], dtype=float)
        _require(p.ndim == 2 and len(p) >= 2 and p.shape[1] == 3 and len(r) == len(p),
                 'selected geometry required')
        distances = np.linalg.norm(np.diff(p, axis=0), axis=1)
        _require(bool(np.all(distances > 0)), 'nonzero intervals required')
        geometry[ident] = p, r, np.r_[0., np.cumsum(distances)]
    revision = case_digest(case)
    names = set()
    for region in regions:
        _require(isinstance(region, dict), 'region object required')
        name = region.get('id')
        _require(isinstance(name, str) and bool(name.strip()) and name not in names, 'unique region ID required')
        names.add(name)
        _require(region.get('case_sha256') == revision, 'region case digest mismatch')
        _require(isinstance(region.get('rationale'), str) and bool(region['rationale'].strip()), 'rationale required')
        refs = region.get('evidence_refs')
        _require(isinstance(refs, list) and bool(refs) and all(isinstance(x, str) and x.strip() for x in refs), 'evidence refs required')
        portions = region.get('portions')
        _require(isinstance(portions, list) and bool(portions), 'portions required')
        touched, links, degree, full, arms, seen = set(), [], {}, [], 0, set()
        for portion in portions:
            _require(isinstance(portion, dict), 'portion object required')
            ident, endpoint, length = portion.get('edge_id'), portion.get('endpoint'), portion.get('length_mm')
            _require(isinstance(ident, str) and ident in geometry and ident not in seen, 'unique selected portion edge required')
            seen.add(ident)
            _require(endpoint in ('start', 'end') and _positive(length), 'endpoint and positive extent required')
            edge, total = edges[ident], float(geometry[ident][2][-1])
            _require(edge['start'] != edge['end'] and length <= total, 'open edge extent exceeds length')
            start = edge[endpoint]
            touched.add(start); degree[start] = degree.get(start, 0)+1
            if length == total:
                lineage = edge.get('bridge_split', {})
                sibling = edges.get(lineage.get('sibling_edge_id'), {})
                other = sibling.get('bridge_split', {})
                split_connector = bool(lineage and other and
                    sibling.get('id') in geometry and
                    other.get('sibling_edge_id') == ident and
                    lineage.get('parent_bridge_id') == other.get('parent_bridge_id') and
                    lineage.get('parent_case_revision') == other.get('parent_case_revision') and
                    lineage.get('internal_endpoint') in ('start', 'end') and
                    other.get('internal_endpoint') in ('start', 'end') and
                    edge[lineage['internal_endpoint']] == sibling[other['internal_endpoint']])
                _require(ident in case.get('synthetic_route_inspection', {}).get('bridge_ids', []) and
                         (edge.get('derivation', {}).get('attachment_mode') == 'side_branch' or split_connector),
                         'full edge must be a declared synthetic side-branch bridge or reciprocal split connector')
                end = edge['end' if endpoint == 'start' else 'start']
                touched.add(end); degree[end] = degree.get(end, 0)+1
                links.append((start, end)); full.append((start, end))
            else:
                arms += 1
            lo, hi = (0., float(length)) if endpoint == 'start' else (total-length, total)
            _require(all(hi < old_lo or lo > old_hi for old_lo, old_hi, _ in zones[ident]),
                     'different regions may not overlap or touch on one edge')
            zones[ident].append((lo, hi, name))
        root = region.get('root_node_id')
        _require(isinstance(root, str) and root in touched, 'root must belong to region')
        reached = {root}
        while True:
            grown = reached | {b for a, b in links if a in reached} | {a for a, b in links if b in reached}
            if grown == reached:
                break
            reached = grown
        _require(reached == touched, 'disconnected region portions')
        _require(arms >= (3 if full else 2), 'insufficient unconsumed external arms')
        _require(all(degree[a] >= 2 and degree[b] >= 2 for a, b in full), 'full edges must be internal connectors')
    clipped = {}
    for ident, (p, r, arc) in geometry.items():
        cuts = np.unique(np.r_[arc, [v for lo, hi, _ in zones[ident] for v in (lo, hi)]])
        points = np.column_stack([np.interp(cuts, arc, p[:, k]) for k in range(3)])
        radii = np.interp(cuts, arc, r)
        clipped[ident] = [(points[i], points[i+1], float(max(radii[i:i+2])),
                           {name for lo, hi, name in zones[ident] if cuts[i] >= lo and cuts[i+1] <= hi},
                           [float(cuts[i]), float(cuts[i+1])]) for i in range(len(cuts)-1)]
    checked, exempt, conflicts = 0, 0, []
    def report(reason=None):
        result = dict(status='UNKNOWN' if conflicts or reason else 'PASS',
            scope='distinct selected edge capsules outside explicit junction regions', case_sha256=revision,
            selected_edge_ids=list(edge_ids), regions=deepcopy(regions), margin_mm=margin_mm,
            checked_segment_pairs=checked, exempt_segment_pairs=exempt,
            potential_contacts=conflicts, inside_regions='NOT CHECKED',
            within_edge_self_intersection='NOT RUN', final_surface_collision='NOT RUN', anatomical_acceptance='UNKNOWN')
        if reason:
            result['reason'] = reason
        return result
    for first, second in combinations(edge_ids, 2):
        found = False
        for a, b, ra, za, aa in clipped[first]:
            for c, d, rb, zb, ab in clipped[second]:
                if checked+exempt >= max_segment_pairs:
                    return report('pair_budget_exhausted')
                if za & zb:
                    exempt += 1
                    continue
                checked += 1
                clearance = segment_distance(a, b, c, d)-ra-rb
                if clearance <= margin_mm:
                    conflicts.append(dict(edges=[first, second], arc_intervals_mm=[aa, ab],
                        clearance_lower_bound_mm=float(clearance), points_mm=[[a.tolist(), b.tolist()], [c.tolist(), d.tolist()]]))
                    found = True
                    break
            if found:
                break
    return report()
