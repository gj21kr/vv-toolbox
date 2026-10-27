"""Explicit terminal-tail treatment for the R common/external iliac gap."""
import json
from pathlib import Path

import numpy as np

from vv_toolbox.case_io import case_digest, load_case
from vv_toolbox.synthetic_junctions import trim_synthetic_terminal
from vv_toolbox.synthetic_routes import extend_synthetic_routes
from vv_toolbox.junction_continuity import inspect_bridge_continuity
from build_synthetic_arch_carotid_case import store_snapshot

ROOT = Path(__file__).resolve().parents[1]


def main():
    path = ROOT/'exports/synthetic-left-iliac-smoothed/case.snapshot.json'
    raw = path.read_bytes(); original, revision = load_case(path)
    case = original
    specifications = []
    # Fixed synthetic cut planes bracketing the overlapping source endpoints.
    # These are not an anatomical bifurcation or inguinal landmark annotation.
    for ident, endpoint, z, children in [
        ('FJ3565:e0', 'start', 915., ['R-CIA-removed-tail', 'R-CIA-retained']),
        ('FJ3567:e0-trim-second', 'end', 903., ['R-EIA-retained', 'R-EIA-removed-tail'])]:
        edge = next(e for e in case['edges'] if e['id'] == ident)
        crossings = []
        for i, (a, b) in enumerate(zip(edge['centerline_mm'][:-1], edge['centerline_mm'][1:])):
            if a[2] != b[2]:
                fraction = (z-a[2])/(b[2]-a[2])
                if 0 < fraction < 1:
                    crossings.append((i, fraction))
        if len(crossings) != 1:
            raise ValueError('Declared plane must intersect one internal interval')
        i, fraction = crossings[0]
        spec = dict(schema='vv-toolbox.synthetic-terminal-trim/1', parent_case_sha256=case_digest(case),
                    source_hashes={s['id']: s['sha256'] for s in case['sources']}, edge_id=ident,
                    remove_endpoint=endpoint, interval_index=i, fraction=fraction,
                    node_id=ident+'-iliac-cut', child_edge_ids=children,
                    rationale=f'Explicit synthetic overlap treatment at fixed LPS Z={z} mm; not an anatomical boundary',
                    evidence_refs=['docs/evidence/access-route-endpoints.json'])
        case = trim_synthetic_terminal(case, spec, case_id=ident+'-iliac-trimmed')
        specifications.append(spec)
    edges = {e['id']: e for e in case['edges']}
    p, q = edges['R-CIA-retained']['centerline_mm'][0], edges['R-EIA-retained']['centerline_mm'][-1]
    length = float(np.linalg.norm(np.subtract(q, p)))
    spec = dict(schema='vv-toolbox.synthetic-route-extension/1', parent_case_sha256=case_digest(case),
                bridges=[dict(id='estimated_R_CIA_EIA_continuation',
                    **{'from': dict(edge_id='R-CIA-retained', endpoint='start'),
                       'to': dict(edge_id='R-EIA-retained', endpoint='end')},
                    handle_lengths_mm=[length, length], samples=192,
                    rationale='Estimated continuation across explicitly trimmed R iliac endpoint overlap',
                    evidence_refs=['docs/evidence/access-route-endpoints.json'])])
    case = extend_synthetic_routes(case, spec, case_id='bilateral-iliac-continuation-candidate')
    report = inspect_bridge_continuity(case, max_angle_deg=3., max_radius_jump_mm=0.)
    attachments = [r for r in report['attachments'] if r['bridge_id'] == 'estimated_R_CIA_EIA_continuation']
    assert len(attachments) == 2 and all(r['status'] == 'PASS' for r in attachments)
    modified = {'FJ3565:e0', 'FJ3567:e0-trim-second'}
    final_edges = {e['id']: e for e in case['edges']}
    # Existing bridge attachment references may be rebound, but geometry stays exact.
    for edge in original['edges']:
        if edge['id'] not in modified:
            assert final_edges[edge['id']]['centerline_mm'] == edge['centerline_mm']
            assert final_edges[edge['id']]['radii_mm'] == edge['radii_mm']
    assert path.read_bytes() == raw
    out = ROOT/'exports/synthetic-right-iliac-case'; out.mkdir(parents=True, exist_ok=True)
    output_revision = store_snapshot(out/'case.snapshot.json', case)
    evidence = dict(schema='vv-toolbox.synthetic-right-iliac-junction/1', parent_revision=revision,
                    case_revision=output_revision, cuts=specifications, continuation_spec=spec,
                    new_attachments=attachments, all_declared_bridge_continuity=report,
                    original_unchanged=True, unrelated_geometry_unchanged=True,
                    anatomical_acceptance='UNKNOWN', surface_check='NOT RUN', surrounding_check='NOT RUN',
                    limitation='Internal iliac branch is not attached by this continuation operation.')
    (ROOT/'docs/evidence/synthetic-right-iliac-junction.json').write_text(json.dumps(evidence, indent=2)+'\n')
    print(json.dumps(dict(revision=output_revision, new_attachment_status=[r['status'] for r in attachments],
                         all_bridge_continuity=report['status'])))


if __name__ == '__main__':
    main()
