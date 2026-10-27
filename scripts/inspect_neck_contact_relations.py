"""Classify existing capsule witnesses without promoting atlas connectivity."""
import hashlib
import json
from collections import Counter
from pathlib import Path

import numpy as np

from vv_toolbox.atlas_topology import reference_junctions
from vv_toolbox.case_io import load_case
from vv_toolbox.geometry_quality import segment_distance


ICA_SOURCE = 'https://pubmed.ncbi.nlm.nih.gov/7277004/'
BCT_SOURCE = 'https://pmc.ncbi.nlm.nih.gov/articles/PMC7505533/'


def nearest_parameters(a, b, c, d):
    """Constrained segment minimum; return fractions, independently check distance."""
    u, v, w = b-a, d-c, a-c
    uu, vv, uv = float(u@u), float(v@v), float(u@v)
    clip = lambda x: float(np.clip(x, 0, 1))
    candidates = [(0., clip(v@w/vv)), (1., clip(v@(b-c)/vv)),
                  (clip(u@(c-a)/uu), 0.), (clip(u@(d-a)/uu), 1.)]
    det = uu*vv-uv*uv
    if det > 0:
        s, t = (uv*(v@w)-vv*(u@w))/det, (uu*(v@w)-uv*(u@w))/det
        if 0 <= s <= 1 and 0 <= t <= 1:
            candidates.append((float(s), float(t)))
    s, t = min(candidates, key=lambda st: np.linalg.norm(w+st[0]*u-st[1]*v))
    distance = float(np.linalg.norm(w+s*u-t*v))
    if not np.isclose(distance, segment_distance(a, b, c, d), atol=1e-9):
        raise ValueError('witness distance implementation disagrees')
    return s, t, distance


def location(edge, interval, fraction):
    points = np.asarray(edge['centerline_mm'])
    lengths = np.linalg.norm(np.diff(points, axis=0), axis=1)
    station = float(lengths[:interval].sum()+fraction*lengths[interval])
    total = float(lengths.sum())
    position = points[interval]+fraction*(points[interval+1]-points[interval])
    endpoint = 'start' if station < 1e-7 else 'end' if total-station < 1e-7 else None
    return dict(edge_id=edge['id'], source_part_id=edge['source_part_id'],
                source_name=edge['anatomy']['artery'], interval_index=interval,
                interval_fraction=fraction, position_mm=position.tolist(),
                arc_from_start_mm=station, arc_to_end_mm=total-station,
                exact_endpoint=endpoint, location='endpoint' if endpoint else 'internal',
                nearest_endpoint='start' if station <= total-station else 'end',
                identity_refs=edge['identity_refs'], geometry_kind=edge['geometry_kind'])


def relation(edges, junctions):
    ids = {e['source_part_id'] for e in edges}
    matches = [j for j in junctions if all(any(pid in m['part_ids'] for m in j['members']) for pid in ids)]
    if matches:
        return dict(status='known_reference_relation', kind='curated_junction_members',
                    junction_ids=[j['id'] for j in matches], sources=sorted({j['source_url'] for j in matches}),
                    note='Reference member identity only; no specimen lumen connection established.')
    names = [e['anatomy']['artery'] for e in edges]
    if any('anterolateral central branch' in n for n in names):
        return dict(status='unknown_direct_relation', kind='source_name_parent_mismatch', sources=[],
                    note='Source names this an MCA branch; this witness touches ICA. Verify its MCA origin and full source mesh before any ICA connection.')
    if any('anterior choroidal' in n or 'ophthalmic' in n for n in names) and any('internal carotid' in n for n in names):
        return dict(status='known_reference_relation', kind='ICA_branch', sources=[ICA_SOURCE],
                    note='Cadaver study describes this named ICA branch; exact origin and lumen in this atlas remain unknown.')
    if ids == {'FJ3417', 'FJ3564'}:
        return dict(status='known_reference_relation', kind='brachiocephalic_to_right_CCA', sources=[BCT_SOURCE],
                    note='Reference parent/daughter; atlas junction is unverified.')
    if ids == {'FJ3564', 'FJ3579'}:
        return dict(status='known_reference_relation', kind='sibling_branches_of_brachiocephalic', sources=[BCT_SOURCE],
                    note='Shared reference parent does not justify a direct CCA-to-subclavian edge. Review all three parts jointly.')
    return dict(status='unknown_direct_relation', kind='unmapped', sources=[], note='No reviewed relation covers this pair.')


def main():
    root = Path(__file__).resolve().parents[1]
    experiment_path = root/'docs/evidence/centerline-regularized-neck.json'
    experiment = json.loads(experiment_path.read_text())
    snapshot = root/'exports/synthetic-neck-case/case.snapshot.json'
    baseline, revision = load_case(snapshot)
    derived, derived_revision = load_case(root/'exports/synthetic-neck-case/centerline-regularized-case.snapshot.json')
    if revision != experiment['parent_revision'] or derived_revision != experiment['derived_revision']:
        raise ValueError('experiment snapshot revisions disagree')
    by_id = {e['id']: e for e in baseline['edges']}
    parts = {e['source_part_id']: dict(id=e['source_part_id'], name=e['anatomy']['artery'], layer='arterial')
             for e in baseline['edges'] if e.get('source_part_id')}
    junctions = reference_junctions(list(parts.values()))
    before = experiment['baseline_same_scope_capsules']['potential_contacts']
    after = {tuple(c['edges']): c for c in experiment['whole_case_modified_edge_capsules']['potential_contacts']}
    if len(before) != 17 or {tuple(c['edges']) for c in before} != set(after):
        raise ValueError('expected exactly 17 persistent contact pairs')
    rows = []
    for witness in before:
        edges = [by_id[e] for e in witness['edges']]
        i, j = witness['intervals']
        p, q = (np.asarray(e['centerline_mm']) for e in edges)
        s, t, distance = nearest_parameters(p[i], p[i+1], q[j], q[j+1])
        locations = [location(edges[0], i, s), location(edges[1], j, t)]
        radius_sum = sum(max(e['radii_mm'][k:k+2]) for e, k in zip(edges, (i, j)))
        if not np.isclose(distance-radius_sum, witness['clearance_lower_bound_mm'], atol=1e-8):
            raise ValueError('capsule witness no longer matches source')
        semantic = relation(edges, junctions)
        eligible = semantic['status'] == 'known_reference_relation' and semantic['kind'] != 'sibling_branches_of_brachiocephalic'
        rows.append(dict(edges=witness['edges'], before_witness=witness,
            after_witness=after[tuple(witness['edges'])], locations=locations,
            centerline_distance_mm=distance, reference_relation=semantic,
            specimen_lumen_connection='UNKNOWN', exact_surface_collision='NOT RUN',
            followup=dict(status='inspection_candidate_only',
                action='inspect_attachment_then_split_internal_edge_if_confirmed' if eligible else 'resolve_parent_and_joint_surface_before_any_split',
                proposed_internal_split_edge_ids=[x['edge_id'] for x in locations if x['location']=='internal'] if eligible else [],
                required=['source mesh local cross-sections', 'anatomical origin adjudication',
                          'explicit attachment coordinates', 'retain source unchanged; modify synthetic graph only']),
            automatic_connectivity_promotion=False))
    report = dict(schema='vv-toolbox.neck-contact-relations/1', status='PASS',
        scope='17 existing conservative capsule witnesses classified; not anatomical approval',
        parent_revision=revision, derived_revision=derived_revision,
        inputs={str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in (experiment_path, snapshot, root/'src/vv_toolbox/atlas_topology.py', Path(__file__))},
        witness_policy='First detected capsule contact per edge pair, not global closest point or anatomical origin. Arc distances are exact for this source polyline witness only.',
        counts=dict(Counter(r['reference_relation']['status'] for r in rows)),
        specimen_connections_confirmed=0, graph_modified=False, pairs=rows)
    target = root/'docs/evidence/neck-contact-relations.json'
    target.write_text(json.dumps(report, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    print(json.dumps(dict(pair_count=len(rows), counts=report['counts'], specimen_connections_confirmed=0)))


if __name__ == '__main__':
    main()
