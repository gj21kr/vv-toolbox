"""Screen new iliofemoral geometry against imported arteries and build surfaces."""
import hashlib
import json
from pathlib import Path

import numpy as np

from vv_toolbox.case_io import load_case
from vv_toolbox.case_surface import build_case_surface
from vv_toolbox.geometry_quality import screen_nonincident_clearance

ROOT = Path(__file__).resolve().parents[1]


def main():
    paths = [ROOT/'exports/synthetic-arch-carotid-case/case.snapshot.json',
             ROOT/'exports/synthetic-iliofemoral-case/case.snapshot.json']
    raw = [p.read_bytes() for p in paths]
    baseline, baseline_revision = load_case(paths[0])
    candidate, revision = load_case(paths[1])
    original_ids = {'FJ3466:e0', 'FJ2074:e0', 'FJ3567:e0', 'FJ2143:e0'}
    bridge_ids = {'estimated_L_iliofemoral', 'estimated_R_iliofemoral'}
    mapping = {e['id']: e['derived_interval']['parent_edge_id'] for e in candidate['edges']
               if e.get('derived_interval', {}).get('parent_edge_id') in original_ids}
    focus = set(mapping) | bridge_ids

    def inspect(case, selected_focus):
        selected = [e['id'] for e in case['edges'] if e['centerline_mm'] is not None]
        screen = screen_nonincident_clearance(case, selected, focus_edge_ids=sorted(selected_focus),
                                              margin_mm=1.2, max_segment_pairs=2_000_000)
        if screen.get('reason') == 'pair_budget_exhausted':
            raise ValueError('Incomplete surroundings screen: pair budget exhausted')
        outside = [{**c, 'normalized_pair': sorted(mapping.get(i, i) for i in c['edges'])}
                   for c in screen['potential_contacts'] if not all(i in selected_focus for i in c['edges'])]
        return screen, outside

    before, old = inspect(baseline, original_ids)
    after, new = inspect(candidate, focus)
    old_pairs = {tuple(c['normalized_pair']) for c in old}
    new_pairs = {tuple(c['normalized_pair']) for c in new}
    out = ROOT/'exports/iliofemoral-candidate-inspection'
    out.mkdir(parents=True, exist_ok=True)
    surfaces = []
    for side, parts in [('L', {'FJ3466:e0', 'FJ2074:e0'}), ('R', {'FJ3567:e0', 'FJ2143:e0'})]:
        selected = sorted([i for i, parent in mapping.items() if parent in parts]+[f'estimated_{side}_iliofemoral'])
        record = dict(side=side, selected_edge_ids=selected, spacing_mm=.6)
        try:
            vertices, faces, metadata = build_case_surface(candidate, selected, spacing_mm=.6)
            target = out/f'{side}-surface.npz'
            np.savez_compressed(target, vertices_mm=vertices, faces=faces, metadata=np.array(json.dumps(metadata)))
            record.update(status='PASS', vertices=len(vertices), triangles=len(faces), metadata=metadata,
                          path=target.relative_to(ROOT).as_posix(), sha256=hashlib.sha256(target.read_bytes()).hexdigest())
        except ValueError as error:
            record.update(status='FAIL', reason=str(error), surface_published=False)
        surfaces.append(record)
    assert all(path.read_bytes() == contents for path, contents in zip(paths, raw))
    report = dict(schema='vv-toolbox.iliofemoral-candidate-inspection/1', baseline_revision=baseline_revision,
                  candidate_revision=revision, baseline_screen=before, candidate_screen=after,
                  baseline_surrounding_contacts=old, candidate_surrounding_contacts=new,
                  new_surrounding_pairs=[list(p) for p in sorted(new_pairs-old_pairs)],
                  persistent_surrounding_pairs=[list(p) for p in sorted(new_pairs & old_pairs)],
                  no_longer_detected_pairs=[list(p) for p in sorted(old_pairs-new_pairs)],
                  bridge_surrounding_contacts=[c for c in new if any(i in bridge_ids for i in c['edges'])],
                  surfaces=surfaces, input_unchanged=True, anatomical_acceptance='UNKNOWN',
                  final_mesh_collision='NOT RUN', default_adoption='NOT ACCEPTED',
                  limitations='Conservative centerline/radius capsules; shared nodes excluded in surrounding screen. Local surface builder checks junction collars and self clearance. Missing source parts not tested.')
    (ROOT/'docs/evidence/iliofemoral-candidate-inspection.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(baseline_pairs=len(old_pairs), candidate_pairs=len(new_pairs),
                         new_pairs=report['new_surrounding_pairs'],
                         bridge_contacts=len(report['bridge_surrounding_contacts']),
                         surfaces=[{k: v for k, v in s.items() if k != 'metadata'} for s in surfaces])))


if __name__ == '__main__':
    main()
