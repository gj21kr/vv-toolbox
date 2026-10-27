"""Author an estimated IIA branch from the source-section review candidate."""
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
    path = ROOT/'exports/synthetic-right-iliac-case/case.snapshot.json'
    raw = path.read_bytes(); parent, revision = load_case(path)
    review = json.loads((ROOT/'docs/evidence/internal-iliac-junction-review.json').read_text())
    assert revision == review['case_revision']
    location = review['synthetic_branch_locator']
    node = 'synthetic_R_internal_iliac_origin'
    children = ['R_iliac_continuation_before_IIA', 'R_iliac_continuation_after_IIA']
    spec = dict(schema='vv-toolbox.synthetic-bridge-split/1', parent_case_sha256=revision,
                source_hashes={s['id']: s['sha256'] for s in parent['sources']},
                edge_id=location['edge_id'], interval_index=location['interval_index'], fraction=location['fraction'],
                node_id=node, child_edge_ids=children,
                rationale='Synthetic IIA origin selected from native surface overlap review; anatomical ostium remains unknown',
                evidence_refs=['docs/evidence/internal-iliac-junction-review.json'])
    split = split_synthetic_bridge(parent, spec, case_id='R-IIA-origin-candidate')
    edges = {e['id']: e for e in split['edges']}
    target = edges[location['daughter_edge_id']]
    endpoint = location['daughter_endpoint']; index = 0 if endpoint == 'start' else -1
    delta = np.subtract(target['centerline_mm'][index], split['nodes'][node]['position_mm'])
    length = float(np.linalg.norm(delta))
    radius = min(target['radii_mm'][index], edges[children[0]]['radii_mm'][-1])
    spec = dict(schema='vv-toolbox.synthetic-route-extension/1', parent_case_sha256=case_digest(split),
        bridges=[dict(id='estimated_R_internal_iliac_origin',
            **{'from': dict(edge_id=children[0], endpoint='end'), 'to': dict(edge_id=target['id'], endpoint=endpoint)},
            attachment_mode='side_branch', from_direction_xyz=(delta/length).tolist(), from_radius_mm=radius,
            handle_lengths_mm=[length, length], samples=192,
            rationale='Explicit synthetic attachment supported by source-section overlap, not source lumen verification',
            evidence_refs=['docs/evidence/internal-iliac-junction-review.json'])])
    case = extend_synthetic_routes(split, spec, case_id='R-iliac-bifurcation-candidate')
    continuity = inspect_bridge_continuity(case, max_angle_deg=3., max_radius_jump_mm=0.)
    assert continuity['status'] == 'PASS'
    incident = sorted(e['id'] for e in case['edges'] if node in (e['start'], e['end']))
    assert len(incident) == 3
    result_edges = {e['id']: e for e in case['edges']}
    assert all(result_edges[e['id']] == e for e in parent['edges'] if e['id'] != location['edge_id'])
    assert path.read_bytes() == raw
    out = ROOT/'exports/synthetic-internal-iliac-case'; out.mkdir(parents=True, exist_ok=True)
    output_revision = store_snapshot(out/'case.snapshot.json', case)
    report = dict(schema='vv-toolbox.synthetic-internal-iliac-branch/1', parent_revision=revision,
        case_revision=output_revision, chosen_origin=location, origin_status='synthetic_estimate',
        incident_edge_ids=incident, continuity=continuity, source_unchanged=True, unrelated_edges_unchanged=True,
        anatomical_acceptance='UNKNOWN', surface_and_surrounding_check='NOT RUN', default_app_applied=False)
    (ROOT/'docs/evidence/synthetic-internal-iliac-branch.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(revision=output_revision, degree=len(incident), continuity=continuity['status'], attachments=len(continuity['attachments']))))


if __name__ == '__main__':
    main()
