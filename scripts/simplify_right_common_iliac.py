"""Apply the source-reviewed, explicit CIA twig omission in a synthetic case."""
import json
from pathlib import Path

from vv_toolbox.case_io import load_case
from vv_toolbox.trunk_simplification import simplify_synthetic_trunk
from vv_toolbox.junction_continuity import inspect_bridge_continuity
from build_synthetic_arch_carotid_case import store_snapshot

ROOT = Path(__file__).resolve().parents[1]


def main():
    path = ROOT/'exports/synthetic-internal-iliac-case/case.snapshot.json'
    raw = path.read_bytes(); case, revision = load_case(path)
    review = json.loads((ROOT/'docs/evidence/common-iliac-spur-inspection.json').read_text())
    assert review['case_revision'] == revision and review['edge_id'] == 'FJ3565:e1'
    spec = dict(schema='vv-toolbox.synthetic-trunk-simplification/1', parent_case_sha256=revision,
        source_hashes={s['id']: s['sha256'] for s in case['sources']},
        trunk_edge_ids=['R-CIA-retained', 'FJ3565:e2'], omit_edge_id='FJ3565:e1',
        merged_edge_id='synthetic_R_common_iliac_trunk', max_omitted_length_mm=2.,
        rationale='Explicit synthetic omission of 1.385641 mm extracted twig inside tested single source contours; no independent anatomical daughter established',
        evidence_refs=['docs/COMMON_ILIAC_SPUR_INSPECTION.md', 'docs/evidence/common-iliac-spur-inspection.json'])
    result = simplify_synthetic_trunk(case, spec, case_id='R-iliac-bifurcation-trunk-candidate')
    continuity = inspect_bridge_continuity(result, max_angle_deg=3., max_radius_jump_mm=0.)
    assert continuity['status'] == 'PASS' and path.read_bytes() == raw
    out = ROOT/'exports/synthetic-common-iliac-trunk'; out.mkdir(parents=True, exist_ok=True)
    output_revision = store_snapshot(out/'case.snapshot.json', result)
    report = dict(schema='vv-toolbox.common-iliac-trunk-simplification/1', parent_revision=revision,
        case_revision=output_revision, specification=spec, continuity=continuity, source_unchanged=True,
        omitted_source_edge='FJ3565:e1', trunk_samples_preserved=True, anatomical_acceptance='UNKNOWN',
        surface_and_surrounding_check='NOT RUN', default_app_applied=False)
    (ROOT/'docs/evidence/common-iliac-trunk-simplification.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(revision=output_revision, continuity=continuity['status'], attachments=len(continuity['attachments']))))


if __name__ == '__main__':
    main()
