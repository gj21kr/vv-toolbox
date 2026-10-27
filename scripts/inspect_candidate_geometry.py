"""Run a hash-bound local surface and all-imported-vessel surroundings audit."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from vv_toolbox.case_io import load_case, _unique_object
from vv_toolbox.case_surface import build_case_surface
from vv_toolbox.geometry_quality import screen_nonincident_clearance, screen_junction_clearance

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('specification', type=Path)
    parser.add_argument('report', type=Path)
    parser.add_argument('artifact_directory', type=Path)
    args = parser.parse_args()
    spec_raw = args.specification.read_bytes()
    spec = json.loads(spec_raw, object_pairs_hook=_unique_object)
    if spec.get('schema') != 'vv-toolbox.candidate-geometry-audit/1':
        raise ValueError('unsupported inspection specification')
    paths = [ROOT/spec[label]['snapshot'] for label in ('baseline', 'candidate')]
    inputs = {p.resolve() for p in paths+[args.specification]}
    targets = [args.report, args.artifact_directory/'surface.npz']
    if len({p.resolve() for p in targets}) != len(targets) or any(p.resolve() in inputs for p in targets):
        raise ValueError('inspection output may not overwrite inputs')
    raw = [p.read_bytes() for p in paths]
    loaded = [load_case(p) for p in paths]
    for label, (_, revision) in zip(('baseline', 'candidate'), loaded):
        if revision != spec[label]['revision']:
            raise ValueError('inspection input revision mismatch: '+label)
    if loaded[0][0]['sources'] != loaded[1][0]['sources']:
        raise ValueError('source identity changed between inspection cases')
    normalization = spec.get('candidate_normalization', {})
    old_ids = {e['id'] for e in loaded[0][0]['edges']}
    new_ids = {e['id'] for e in loaded[1][0]['edges']}
    if any(k not in new_ids or v not in old_ids for k, v in normalization.items()):
        raise ValueError('normalization must map actual candidate to baseline edges')
    screens, outside = [], []
    for label, (case, _) in zip(('baseline', 'candidate'), loaded):
        focus = spec[label]['focus_edge_ids']
        screen = screen_nonincident_clearance(case, [e['id'] for e in case['edges'] if e['centerline_mm'] is not None],
            focus_edge_ids=focus, margin_mm=spec['margin_mm'], max_segment_pairs=spec['max_segment_pairs'])
        if screen.get('reason') == 'pair_budget_exhausted':
            raise ValueError('inspection pair budget exhausted')
        screens.append(screen)
        rows = []
        for contact in screen['potential_contacts']:
            if all(i in focus for i in contact['edges']):
                continue
            rows.append({**contact, 'normalized_pair': sorted(normalization.get(i, i) if label == 'candidate' else i for i in contact['edges'])})
        outside.append(rows)
        print(json.dumps(dict(stage=label, surrounding_pairs=len(rows))), flush=True)
    args.artifact_directory.mkdir(parents=True, exist_ok=True)
    try:
        vertices, faces, metadata = build_case_surface(loaded[1][0], spec['candidate']['focus_edge_ids'],
            spacing_mm=spec['spacing_mm'], junction_regions=spec.get('junction_regions'))
        path = args.artifact_directory/'surface.npz'
        np.savez_compressed(path, vertices_mm=vertices, faces=faces, metadata=np.array(json.dumps(metadata)))
        surface = dict(status='PASS', vertices=len(vertices), triangles=len(faces), metadata=metadata,
                       sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    except ValueError as error:
        surface = dict(status='FAIL', reason=str(error), surface_published=False)
        if spec.get('junction_regions') is None:
            selected = [e for e in loaded[1][0]['edges'] if e['id'] in spec['candidate']['focus_edge_ids']]
            incidence = {}
            for edge in selected:
                for endpoint, index in [('start', 0), ('end', -1)]:
                    incidence.setdefault(edge[endpoint], []).append(edge['radii_mm'][index])
            collars = {node: 3*max(radii)+2*spec['spacing_mm'] for node, radii in incidence.items() if len(radii) > 1}
            surface['junction_diagnostic'] = screen_junction_clearance(loaded[1][0], spec['candidate']['focus_edge_ids'],
                collars_mm=collars, margin_mm=2*spec['spacing_mm'], max_segment_pairs=spec['max_segment_pairs'])
    pairs = [{tuple(c['normalized_pair']) for c in rows} for rows in outside]
    report = dict(schema='vv-toolbox.candidate-geometry-audit-result/1', specification=spec,
        specification_sha256=hashlib.sha256(spec_raw).hexdigest(), baseline_screen=screens[0], candidate_screen=screens[1],
        baseline_surrounding_contacts=outside[0], candidate_surrounding_contacts=outside[1],
        new_pairs=[list(p) for p in sorted(pairs[1]-pairs[0])], persistent_pairs=[list(p) for p in sorted(pairs[0]&pairs[1])],
        removed_pairs=[list(p) for p in sorted(pairs[0]-pairs[1])], surface=surface,
        anatomical_acceptance='UNKNOWN', final_mesh_collision='NOT RUN', default_adoption='NOT ACCEPTED',
        limitation='Focus-vs-imported-case capsule screen; within-focus contacts remain in raw screen but excluded from surrounding delta. Shared-node, source coverage and local-region exclusions remain applicable.')
    if any(p.read_bytes() != b for p, b in zip(paths, raw)) or args.specification.read_bytes() != spec_raw:
        raise ValueError('inspection input changed during run')
    report['inputs_unchanged'] = True
    args.report.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(new_pairs=report['new_pairs'], persistent_pairs=report['persistent_pairs'],
                         surface={k: v for k, v in surface.items() if k != 'metadata'})))


if __name__ == '__main__':
    main()
