"""Fixed bounded smoothing across the synthetic L common/external iliac node."""
import json
from pathlib import Path

import numpy as np

from vv_toolbox.case_io import load_case
from vv_toolbox.junction_regularization import smooth_continuation_node
from build_synthetic_arch_carotid_case import store_snapshot

ROOT = Path(__file__).resolve().parents[1]


def measure(case):
    edges = {e['id']: e for e in case['edges']}
    a, b = edges['FJ3464:e0'], edges['FJ3466:e0-trim-first']
    u, v = np.diff(a['centerline_mm'], axis=0)[-1], np.diff(b['centerline_mm'], axis=0)[0]
    return dict(angle_deg=float(np.degrees(np.arccos(np.clip(u@v/np.linalg.norm(u)/np.linalg.norm(v), -1, 1)))),
                radius_jump_mm=abs(a['radii_mm'][-1]-b['radii_mm'][0]))


def main():
    path = ROOT/'exports/synthetic-left-iliac-case/case.snapshot.json'
    raw = path.read_bytes(); case, revision = load_case(path)
    params = dict(sigma_mm=2., support_mm=6., sample_spacing_mm=.25, max_displacement_mm=1., max_radius_change_mm=1.)
    result = smooth_continuation_node(case, 'synthetic_L_common_external_iliac', **params, case_id='L-iliac-junction-smoothed-candidate')
    before, after = measure(case), measure(result)
    assert after['radius_jump_mm'] == 0 and after['angle_deg'] < before['angle_deg']
    selected = {'FJ3464:e0', 'FJ3466:e0-trim-first'}
    assert all(a == b for a, b in zip(case['edges'], result['edges']) if a['id'] not in selected)
    assert path.read_bytes() == raw
    out = ROOT/'exports/synthetic-left-iliac-smoothed'; out.mkdir(parents=True, exist_ok=True)
    output_revision = store_snapshot(out/'case.snapshot.json', result)
    report = dict(schema='vv-toolbox.left-iliac-junction-smoothing/1', parent_revision=revision, case_revision=output_revision,
                  parameters=params, before=before, after=after,
                  max_displacement_mm=result['junction_regularization_history'][-1]['measured_max_displacement_mm'],
                  max_radius_change_mm=result['junction_regularization_history'][-1]['measured_max_radius_change_mm'],
                  source_unchanged=True, unrelated_edges_unchanged=True,
                  surface_check='NOT RUN', surrounding_check='NOT RUN', anatomical_acceptance='UNKNOWN')
    (ROOT/'docs/evidence/left-iliac-junction-smoothing.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
