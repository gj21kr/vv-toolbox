"""Construct a separately identified estimated epigastric branch candidate."""
import json
from pathlib import Path

import numpy as np

from vv_toolbox.case_io import case_digest, load_case
from vv_toolbox.synthetic_junctions import split_synthetic_bridge
from vv_toolbox.synthetic_routes import extend_synthetic_routes
from vv_toolbox.junction_continuity import inspect_bridge_continuity
from build_synthetic_arch_carotid_case import store_snapshot

ROOT = Path(__file__).resolve().parents[1]


def main():
    path = ROOT/'exports/synthetic-iliofemoral-case/case.snapshot.json'
    raw = path.read_bytes()
    parent, revision = load_case(path)
    review = json.loads((ROOT/'docs/evidence/epigastric-source-junction.json').read_text())
    assert review['case_revision'] == revision
    location = review['synthetic_branch_locator']
    node = 'synthetic_R_IEA_origin'
    children = ['synthetic_R_iliofemoral_before_IEA', 'synthetic_R_iliofemoral_after_IEA']
    spec = dict(schema='vv-toolbox.synthetic-bridge-split/1', parent_case_sha256=revision,
                source_hashes={s['id']: s['sha256'] for s in parent['sources']},
                edge_id=location['edge_id'], interval_index=location['interval_index'], fraction=location['fraction'],
                node_id=node, child_edge_ids=children,
                rationale='Explicit estimated branch origin selected from the source-overlap review locator; not a confirmed ostium',
                evidence_refs=['docs/EPIGASTRIC_SOURCE_JUNCTION.md'])
    split = split_synthetic_bridge(parent, spec, case_id='iliofemoral-IEA-origin-candidate')
    edges = {e['id']: e for e in split['edges']}
    target = edges[location['daughter_edge_id']]
    point = np.array(target['centerline_mm'][0])
    start = np.array(split['nodes'][node]['position_mm'])
    delta = point-start
    length = float(np.linalg.norm(delta))
    radius = min(target['radii_mm'][0], edges[children[0]]['radii_mm'][-1])
    spec = dict(schema='vv-toolbox.synthetic-route-extension/1', parent_case_sha256=case_digest(split),
                bridges=[dict(id='estimated_R_IEA_origin_connection',
                    **{'from': dict(edge_id=children[0], endpoint='end'),
                       'to': dict(edge_id=target['id'], endpoint='start')},
                    attachment_mode='side_branch', from_direction_xyz=(delta/length).tolist(),
                    from_radius_mm=radius, handle_lengths_mm=[length, length], samples=192,
                    rationale='Synthetic branch attached at a separately declared review candidate; source shared lumen remains unknown',
                    evidence_refs=['docs/EPIGASTRIC_SOURCE_JUNCTION.md'])])
    case = extend_synthetic_routes(split, spec, case_id='iliofemoral-with-R-IEA-candidate')
    continuity = inspect_bridge_continuity(case, max_angle_deg=3., max_radius_jump_mm=0.)
    assert continuity['status'] == 'PASS'
    incident = sorted(e['id'] for e in case['edges'] if node in (e['start'], e['end']))
    assert len(incident) == 3
    after = {e['id']: e for e in case['edges']}
    assert all(after[e['id']] == e for e in parent['edges'] if e['id'] != location['edge_id'])
    assert path.read_bytes() == raw
    out = ROOT/'exports/synthetic-epigastric-case'; out.mkdir(parents=True, exist_ok=True)
    output_revision = store_snapshot(out/'case.snapshot.json', case)
    report = dict(schema='vv-toolbox.synthetic-epigastric-branch/1', parent_revision=revision,
                  case_revision=output_revision, chosen_origin=location, origin_status='synthetic_estimate',
                  node_id=node, incident_edge_ids=incident, continuity=continuity,
                  source_unchanged=True, unrelated_edges_unchanged=True,
                  anatomical_acceptance='UNKNOWN', surface_and_surrounding_check='NOT RUN',
                  default_app_applied=False)
    (ROOT/'docs/evidence/synthetic-epigastric-branch.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(case_revision=output_revision, incident_edge_ids=incident,
                         continuity=continuity['status'], attachments=len(continuity['attachments']))))


if __name__ == '__main__':
    main()
