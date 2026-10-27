"""Explicit overlap-tail removal and separate estimated iliofemoral bridges."""
import json
from pathlib import Path

import numpy as np

from vv_toolbox.case_io import case_digest, load_case
from vv_toolbox.synthetic_junctions import trim_synthetic_terminal
from vv_toolbox.synthetic_routes import extend_synthetic_routes
from vv_toolbox.junction_continuity import inspect_bridge_continuity
from build_synthetic_arch_carotid_case import store_snapshot


def main():
    root = Path(__file__).resolve().parents[1]
    path = root/'exports/synthetic-arch-carotid-case/case.snapshot.json'
    parent_bytes = path.read_bytes()
    parent, revision = load_case(path)
    case = parent
    records, bridge_ids = [], []
    for side, iliac, ie, femoral, fe in [
        ('L', 'FJ3466:e0', 'end', 'FJ2074:e0', 'start'),
        ('R', 'FJ3567:e0', 'start', 'FJ2143:e0', 'end')]:
        source_edges = {e['id']: e for e in parent['edges']}
        iz = source_edges[iliac]['centerline_mm'][0 if ie == 'start' else -1][2]
        fz = source_edges[femoral]['centerline_mm'][0 if fe == 'start' else -1][2]
        # A fixed synthetic construction rule, not an inguinal landmark claim.
        planes = [max(iz, fz)+10., min(iz, fz)-10.]
        kept_ids = []
        for ident, endpoint, z in zip([iliac, femoral], [ie, fe], planes):
            edge = next(e for e in case['edges'] if e['id'] == ident)
            points = np.asarray(edge['centerline_mm'])
            crossings = []
            for index, (p, q) in enumerate(zip(points[:-1], points[1:])):
                if p[2] != q[2]:
                    fraction = (z-p[2])/(q[2]-p[2])
                    if 0 < fraction < 1:
                        crossings.append((index, float(fraction)))
            if len(crossings) != 1:
                raise ValueError(f'{ident}: cut plane must have one internal crossing')
            index, fraction = crossings[0]
            children = [ident+'-trim-first', ident+'-trim-second']
            spec = dict(schema='vv-toolbox.synthetic-terminal-trim/1',
                        parent_case_sha256=case_digest(case), source_hashes={s['id']: s['sha256'] for s in case['sources']},
                        edge_id=ident, remove_endpoint=endpoint, interval_index=index, fraction=fraction,
                        node_id=ident+'-synthetic-cut', child_edge_ids=children,
                        rationale='Synthetic overlap removal: endpoint Z envelope plus fixed 10 mm margin; not anatomical boundary',
                        evidence_refs=['docs/ILIOFEMORAL_GAPS.md'])
            case = trim_synthetic_terminal(case, spec, case_id=f'iliofemoral-{side}-{ident}-trim')
            kept_ids.append(children[1 if endpoint == 'start' else 0])
            records.append(dict(cut_plane_z_mm=z, specification=spec))
        edges = {e['id']: e for e in case['edges']}
        p = edges[kept_ids[0]]['centerline_mm'][0 if ie == 'start' else -1]
        q = edges[kept_ids[1]]['centerline_mm'][0 if fe == 'start' else -1]
        length = float(np.linalg.norm(np.subtract(q, p)))
        bridge_id = f'estimated_{side}_iliofemoral'
        spec = dict(schema='vv-toolbox.synthetic-route-extension/1', parent_case_sha256=case_digest(case),
                    bridges=[dict(id=bridge_id, **{'from': dict(edge_id=kept_ids[0], endpoint=ie),
                        'to': dict(edge_id=kept_ids[1], endpoint=fe)},
                        handle_lengths_mm=[length, length], samples=192,
                        rationale='Estimated connection between explicitly trimmed source tails',
                        evidence_refs=['docs/ILIOFEMORAL_GAPS.md'])])
        case = extend_synthetic_routes(case, spec, case_id=f'iliofemoral-{side}-connected')
        bridge_ids.append(bridge_id)
    continuity = inspect_bridge_continuity(case, max_angle_deg=3., max_radius_jump_mm=0.)
    selected = [r for r in continuity['attachments'] if r['bridge_id'] in bridge_ids]
    assert len(selected) == 4 and all(r['status'] == 'PASS' for r in selected)
    changed = {'FJ3466:e0', 'FJ2074:e0', 'FJ3567:e0', 'FJ2143:e0'}
    final_edges = {e['id']: e for e in case['edges']}
    assert all(final_edges[e['id']] == e for e in parent['edges'] if e['id'] not in changed)
    assert path.read_bytes() == parent_bytes
    out = root/'exports/synthetic-iliofemoral-case'
    out.mkdir(parents=True, exist_ok=True)
    output_revision = store_snapshot(out/'case.snapshot.json', case)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig = plt.figure(figsize=(12, 6))
    for column, (side, iliac, femoral) in enumerate([
            ('L', 'FJ3466:e0', 'FJ2074:e0'), ('R', 'FJ3567:e0', 'FJ2143:e0')]):
        ax = fig.add_subplot(1, 2, column+1, projection='3d')
        for ident in (iliac, femoral):
            original = np.asarray(next(e for e in parent['edges'] if e['id'] == ident)['centerline_mm'])
            visible = original[(original[:, 2] > 760) & (original[:, 2] < 870)]
            ax.plot(*visible.T, color='gray', linestyle='--', label='Original' if ident == iliac else None)
            retained = np.asarray(next(e for e in case['edges'] if e['id'].startswith(ident+'-trim-'))['centerline_mm'])
            visible = retained[(retained[:, 2] > 760) & (retained[:, 2] < 870)]
            ax.plot(*visible.T, color='firebrick', label='Retained' if ident == iliac else None)
        bridge = np.asarray(final_edges[f'estimated_{side}_iliofemoral']['centerline_mm'])
        ax.plot(*bridge.T, color='darkorange', linewidth=3, label='Estimated bridge')
        ax.scatter(*bridge[[0, -1]].T, color='black', s=18)
        ax.set(xlabel='L (mm)', ylabel='P (mm)', zlabel='S (mm)', title=f'{side}: centerlines only')
        ax.set_box_aspect([1, 1, 2])
        ax.legend(fontsize=8)
    fig.suptitle('Synthetic tail trimming; NOT anatomical boundary or surface acceptance')
    fig.tight_layout()
    fig.savefig(out/'centerline-comparison.png', dpi=150)
    plt.close(fig)
    report = dict(schema='vv-toolbox.synthetic-iliofemoral-case/1', parent_case_revision=revision,
                  case_revision=output_revision, cuts=records, bridge_ids=bridge_ids,
                  attachments=selected, source_unchanged=True, unrelated_edges_unchanged=True,
                  collision_check='NOT RUN', surface_check='NOT RUN', anatomical_acceptance='UNKNOWN',
                  default_app_applied=False)
    (root/'docs/evidence/synthetic-iliofemoral-case.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k: report[k] for k in ['case_revision', 'bridge_ids', 'source_unchanged', 'collision_check']}))


if __name__ == '__main__':
    main()
