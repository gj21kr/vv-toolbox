"""Bounded compound-junction and surrounding screens for the IEA candidate."""
import hashlib
import json
from pathlib import Path

import numpy as np

from vv_toolbox.case_io import load_case
from vv_toolbox.case_surface import build_case_surface
from vv_toolbox.junction_regions import inspect_junction_regions
from vv_toolbox.geometry_quality import screen_nonincident_clearance

ROOT = Path(__file__).resolve().parents[1]


def main():
    paths = [ROOT/'exports/synthetic-iliofemoral-case/case.snapshot.json', ROOT/'exports/synthetic-epigastric-case/case.snapshot.json']
    raw = [p.read_bytes() for p in paths]
    baseline, baseline_revision = load_case(paths[0])
    case, revision = load_case(paths[1])
    e = {edge['id']: edge for edge in case['edges']}
    iliac, femoral, daughter = 'FJ3567:e0-trim-second', 'FJ2143:e0-trim-first', 'FJ3604:e0'
    before, after, branch = 'synthetic_R_iliofemoral_before_IEA', 'synthetic_R_iliofemoral_after_IEA', 'estimated_R_IEA_origin_connection'
    selected = [iliac, femoral, daughter, before, after, branch]
    spacing = .6
    width = 3*max(e[before]['radii_mm'][-1], e[iliac]['radii_mm'][0])+2*spacing
    far_width = 3*max(e[after]['radii_mm'][-1], e[femoral]['radii_mm'][-1])+2*spacing

    def portion(ident, endpoint, length=None):
        if length is None:
            length = float(np.cumsum(np.linalg.norm(np.diff(e[ident]['centerline_mm'], axis=0), axis=1))[-1])
        return dict(edge_id=ident, endpoint=endpoint, length_mm=length)

    def region(ident, node, portions):
        return dict(id=ident, case_sha256=revision, root_node_id=node, portions=portions,
                    rationale='Numerical 3*max endpoint radius+2*spacing collar, spanning declared short internal connectors; not anatomical ostium extent',
                    evidence_refs=['docs/EPIGASTRIC_SOURCE_JUNCTION.md', 'docs/SYNTHETIC_BRIDGE_SPLIT.md'])

    regions = [region('IEA-compound', e[branch]['start'], [portion(before, 'start'), portion(branch, 'start'),
        portion(iliac, 'start', width), portion(after, 'start', width), portion(daughter, 'start', width)]),
        region('femoral-attachment', e[after]['end'], [portion(after, 'end', far_width), portion(femoral, 'end', far_width)])]
    local = inspect_junction_regions(case, selected, regions, margin_mm=1.2)
    print(json.dumps(dict(local_status=local['status'], local_contacts=local['potential_contacts'])), flush=True)
    out = ROOT/'exports/epigastric-candidate-inspection'; out.mkdir(parents=True, exist_ok=True)
    surface = dict(status='NOT RUN')
    try:
        vertices, faces, metadata = build_case_surface(case, selected, spacing_mm=spacing, junction_regions=regions)
        target = out/'surface.npz'
        np.savez_compressed(target, vertices_mm=vertices, faces=faces, metadata=np.array(json.dumps(metadata)))
        surface = dict(status='PASS', vertices=len(vertices), triangles=len(faces), metadata=metadata,
                       path=target.relative_to(ROOT).as_posix(), sha256=hashlib.sha256(target.read_bytes()).hexdigest())
    except ValueError as error:
        surface = dict(status='FAIL', reason=str(error), surface_published=False)
    print(json.dumps({k: v for k, v in surface.items() if k != 'metadata'}), flush=True)

    def normalize(ident):
        return 'estimated_R_iliofemoral' if ident in (before, after) else ident

    def surroundings(model, focus):
        screen = screen_nonincident_clearance(model, [x['id'] for x in model['edges'] if x['centerline_mm'] is not None],
                    focus_edge_ids=focus, margin_mm=1.2, max_segment_pairs=2_000_000)
        if screen.get('reason') == 'pair_budget_exhausted':
            raise ValueError('Surrounding pair budget exhausted')
        outside = [{**c, 'normalized_pair': sorted(normalize(i) for i in c['edges'])}
                   for c in screen['potential_contacts'] if not all(i in focus for i in c['edges'])]
        return screen, outside

    old_screen, old = surroundings(baseline, [iliac, femoral, daughter, 'estimated_R_iliofemoral'])
    new_screen, new = surroundings(case, selected)
    old_pairs, new_pairs = [{tuple(c['normalized_pair']) for c in rows} for rows in [old, new]]
    assert all(p.read_bytes() == b for p, b in zip(paths, raw))
    report = dict(schema='vv-toolbox.epigastric-candidate-inspection/1', baseline_revision=baseline_revision,
                  case_revision=revision, selected_edge_ids=selected, regions=regions, local_clearance=local,
                  surface=surface, baseline_screen=old_screen, candidate_screen=new_screen,
                  baseline_surrounding_contacts=old, candidate_surrounding_contacts=new,
                  new_surrounding_pairs=[list(p) for p in sorted(new_pairs-old_pairs)],
                  persistent_surrounding_pairs=[list(p) for p in sorted(new_pairs & old_pairs)],
                  removed_surrounding_pairs=[list(p) for p in sorted(old_pairs-new_pairs)],
                  input_unchanged=True, anatomical_acceptance='UNKNOWN', final_mesh_collision='NOT RUN',
                  inside_region_detail='NOT CHECKED', default_adoption='NOT ACCEPTED')
    (ROOT/'docs/evidence/epigastric-candidate-inspection.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(old_surrounding_pairs=len(old_pairs), new_surrounding_pairs=len(new_pairs),
                         newly_detected=report['new_surrounding_pairs'])), flush=True)


if __name__ == '__main__':
    main()
