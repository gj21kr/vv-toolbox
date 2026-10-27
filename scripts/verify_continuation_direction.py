"""Check actual overlapping source endpoints without modifying source cases."""
import json
from pathlib import Path

from vv_toolbox.case_io import case_digest, load_case
from vv_toolbox.synthetic_routes import build_synthetic_routes

ROOT = Path(__file__).resolve().parents[1]


def main():
    source = json.loads((ROOT / 'exports/atlas-case-inspection/all-arterial-case.json').read_text())
    revision = case_digest(source)
    edges = {e['id']: e for e in source['edges']}
    pairs = [('BCT-RCCA', 'FJ3417:e0', 'start', 'FJ3564:e0', 'end'),
             ('L-iliac-femoral', 'FJ3466:e0', None, 'FJ2074:e0', None),
             ('R-iliac-femoral', 'FJ3567:e0', None, 'FJ2143:e0', None)]
    results = []
    for name, a, ae, b, be in pairs:
        # Lower iliac and upper femoral endpoints in native LPS superior Z.
        ae = ae or min(('start', 'end'), key=lambda k: edges[a]['centerline_mm'][0 if k == 'start' else -1][2])
        be = be or max(('start', 'end'), key=lambda k: edges[b]['centerline_mm'][0 if k == 'start' else -1][2])
        bridge = dict(id=name, **{'from': dict(edge_id=a, endpoint=ae), 'to': dict(edge_id=b, endpoint=be)},
                      handle_lengths_mm=[10, 10], samples=96,
                      rationale='negative test of overlapping original endpoints',
                      evidence_refs=['docs/BRACHIOCEPHALIC_JUNCTION.md', 'docs/ILIOFEMORAL_GAPS.md'])
        spec = dict(schema='vv-toolbox.synthetic-routes/1', source_case_sha256=revision, bridges=[bridge])
        try:
            build_synthetic_routes(source, spec, case_id=name)
        except ValueError as error:
            assert 'reverses' in str(error), str(error)
            results.append(dict(id=name, status='REJECTED', reason=str(error), anchors=[bridge['from'], bridge['to']]))
        else:
            raise AssertionError(f'{name}: expected backwards continuation rejection')
    neck, _ = load_case(ROOT / 'exports/synthetic-neck-case/case.snapshot.json')
    rebuilt = build_synthetic_routes(source, neck['generation']['config'], case_id=neck['case_id'])
    assert case_digest(rebuilt) == case_digest(neck)
    assert case_digest(source) == revision
    report = dict(schema='vv-toolbox.continuation-direction-verification/1', status='PASS',
                  source_case_sha256=revision, rejected_source_pairs=results,
                  existing_neck_case_identical=True, source_unchanged=True,
                  limitation='Chord monotonicity only; not collision, lumen continuity, or anatomical approval.')
    (ROOT / 'docs/evidence/continuation-direction-verification.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
