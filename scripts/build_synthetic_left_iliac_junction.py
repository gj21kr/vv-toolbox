"""Explicitly coalesce coincident L common/external iliac source endpoints."""
import json
from pathlib import Path

import numpy as np

from vv_toolbox.case_io import load_case
from vv_toolbox.synthetic_nodes import coalesce_synthetic_nodes
from build_synthetic_arch_carotid_case import store_snapshot

ROOT = Path(__file__).resolve().parents[1]


def main():
    path = ROOT/'exports/synthetic-epigastric-case/case.snapshot.json'
    before = path.read_bytes()
    case, revision = load_case(path)
    edges = {e['id']: e for e in case['edges']}
    common, external = edges['FJ3464:e0'], edges['FJ3466:e0-trim-first']
    spec = dict(schema='vv-toolbox.synthetic-node-coalescence/1', parent_case_sha256=revision,
                source_hashes={s['id']: s['sha256'] for s in case['sources']},
                node_ids=[common['end'], external['start']], node_id='synthetic_L_common_external_iliac',
                rationale='Explicit synthetic continuation at identical source endpoint coordinates; no source ostium approval',
                evidence_refs=['docs/evidence/access-route-endpoints.json'])
    result = coalesce_synthetic_nodes(case, spec, case_id='arterial-L-iliac-coalesced-candidate')
    a = np.subtract(common['centerline_mm'][-1], common['centerline_mm'][-2])
    b = np.subtract(external['centerline_mm'][1], external['centerline_mm'][0])
    angle = float(np.degrees(np.arccos(np.clip(a@b/np.linalg.norm(a)/np.linalg.norm(b), -1, 1))))
    radius_jump = abs(common['radii_mm'][-1]-external['radii_mm'][0])
    assert path.read_bytes() == before
    assert all(a['centerline_mm'] == b['centerline_mm'] and a['radii_mm'] == b['radii_mm'] for a, b in zip(case['edges'], result['edges']))
    out = ROOT/'exports/synthetic-left-iliac-case'; out.mkdir(parents=True, exist_ok=True)
    output_revision = store_snapshot(out/'case.snapshot.json', result)
    report = dict(schema='vv-toolbox.synthetic-left-iliac-junction/1', parent_revision=revision,
                  case_revision=output_revision, specification=spec,
                  position_mm=result['nodes'][spec['node_id']]['position_mm'], position_gap_mm=0.,
                  radius_jump_mm=radius_jump, sampled_tangent_angle_deg=angle,
                  original_snapshot_unchanged=True, all_centerlines_and_radii_unchanged=True,
                  graph_connection='PRESENT', anatomical_acceptance='UNKNOWN', surface_check='NOT RUN')
    (ROOT/'docs/evidence/synthetic-left-iliac-junction.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'specification'}))


if __name__ == '__main__':
    main()
