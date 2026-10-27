"""Detached whole-access radius experiment with fixed interfaces and path checks."""
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh

from vv_toolbox.case_io import load_case
from vv_toolbox.centerline_containment import inspect_centerline_containment
from vv_toolbox.resampled_access_preview import load_resampled_access_preview
from vv_toolbox.union_radius import scale_selected_radius


def main():
    evidence = Path('docs/evidence')
    candidate = load_resampled_access_preview(Path('.'))
    record = json.loads((evidence / 'atlas-neck-volume-case.json').read_text())
    case, revision = load_case(record['derived_case_file'])
    if revision != candidate['summary']['revision']:
        raise ValueError('Source revision mismatch')
    source = 'FJ2074'
    part = next(p for p in case['surface_parts'] if p['part_id'] == source)
    paths = [e for e in case['edges'] if e['id'] in part['edge_ids']]
    if len(paths) != 1:
        raise ValueError('Single explicit source centerline required')
    parameters = dict(scale=1.05, transition_mm=10., max_displacement_mm=1.)
    report = dict(status='RUNNING', source=source, parameters=parameters,
                  source_case_revision=revision, source_edge=paths[0]['id'],
                  parent_surface_sha256=candidate['summary']['surface_sha256'],
                  graph_revision=candidate['summary']['access_graph']['revision'],
                  expected_edges=len(candidate['edges']), rows=[],
                  context='NOT RUN', anatomical_validation='NOT RUN', live_scene_changed=False)
    target = evidence / 'access-radius-edit.json'

    def save():
        temp = target.with_suffix('.json.tmp')
        temp.write_text(json.dumps(report, indent=2) + '\n')
        temp.replace(target)

    save()
    try:
        mesh = trimesh.Trimesh(candidate['vertices_mm'], candidate['faces'], process=False)
        output, audit = scale_selected_radius(mesh, candidate['face_lineage'], source,
                                              paths[0]['centerline_mm'], **parameters)
        folder = Path('exports/access-radius-edit')
        folder.mkdir(parents=True, exist_ok=True)
        artifact = folder / 'left-femoral-105.npz'
        np.savez_compressed(artifact, vertices=output.vertices, faces=output.faces)
        report.update(radius_edit=audit, artifact=str(artifact),
                      output_sha256=hashlib.sha256(artifact.read_bytes()).hexdigest(),
                      lineage_scope='Inherited face ownership; deformed coordinates are synthetic')
        save()
        for edge in candidate['edges']:
            result = inspect_centerline_containment(output, edge['centerline_mm'])
            report['rows'].append(dict(edge_id=edge['id'], **result))
            save()
        states = [row['status'] for row in report['rows']]
        report['centerline_status'] = ('FAIL' if 'FAIL' in states else
                                        'UNKNOWN' if 'UNKNOWN' in states else 'PASS')
        report['status'] = 'CANDIDATE' if report['centerline_status'] == 'PASS' else report['centerline_status']
    except ValueError as error:
        report.update(status='FAIL', reason=str(error))
    save()
    print(json.dumps({k: report.get(k) for k in ('status', 'centerline_status', 'reason')}), flush=True)


if __name__ == '__main__':
    main()
