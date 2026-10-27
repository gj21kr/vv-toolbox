"""Bind the fixed bend candidate to its complete graph and inspect every path."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh

from vv_toolbox.case_io import case_digest, load_case, save_case
from vv_toolbox.centerline_containment import inspect_centerline_containment
from vv_toolbox.resampled_access_preview import load_resampled_access_preview


def main():
    source = json.loads(Path('docs/evidence/access-shape-edit-bend.json').read_text())
    if source['status'] != 'CANDIDATE':
        raise ValueError('Bend candidate required')
    candidate = load_resampled_access_preview(Path('.'))
    if source['parent_surface_sha256'] != candidate['summary']['surface_sha256']:
        raise ValueError('Bend parent mismatch')
    original, parent_revision = load_case('exports/femoral-anterior-graph/case.snapshot.json')
    if original['edges'] != candidate['edges']:
        raise ValueError('Graph parent mismatch')
    selected = [e for e in original['edges'] if e.get('source_part_id') == 'FJ2074']
    if len(selected) != 1 or not np.array_equal(selected[0]['centerline_mm'], candidate['source_centerlines']['FJ2074']['points_mm']):
        raise ValueError('Explicit single-path graph correspondence required')
    with np.load(source['artifact'], allow_pickle=False) as data:
        vertices, faces, points = data['vertices'], data['faces'], data['centerline_mm']
    if not np.array_equal(points[[0, -1]], np.asarray(selected[0]['centerline_mm'])[[0, -1]]):
        raise ValueError('Graph endpoints moved')
    graph = deepcopy(original)
    graph.update(case_id=original['case_id']+'-bend-inspection', model_kind='synthetic',
        generation=dict(seed=0, generator_version='fixed-collar-bend/1',
                        config=dict(parameters=source['parameters'], parent_graph_revision=parent_revision)))
    for edge in graph['edges']:
        if edge['id'] == selected[0]['id']:
            edge['centerline_mm'] = points.tolist()
            edge['geometry_kind'] = 'estimated'
            edge['evidence_status'] = 'synthetic_estimate'
    graph['inspection'] = dict(shape_edit=dict(accepted_for_generation=False,
        radius_surface_consistency='NOT RUN', neighboring_vessels='NOT RUN'))
    revision = case_digest(graph)
    mesh = trimesh.Trimesh(vertices, faces, process=False)
    report = dict(status='RUNNING', graph_revision=revision, parent_graph_revision=parent_revision,
        geometry_sha256=hashlib.sha256(vertices.astype('<f8').tobytes()+faces.astype('<i8').tobytes()).hexdigest(),
        expected_edges=len(graph['edges']), rows=[], accepted_for_generation=False)
    target = Path('docs/evidence/access-bend-graph.json')
    for edge in graph['edges']:
        report['rows'].append(dict(edge_id=edge['id'], **inspect_centerline_containment(mesh, edge['centerline_mm'])))
        target.write_text(json.dumps(report, indent=2)+'\n')
    report['status'] = 'PASS' if all(r['status'] == 'PASS' for r in report['rows']) else 'UNKNOWN'
    if any(r['status'] == 'FAIL' for r in report['rows']):
        report['status'] = 'FAIL'
    output = Path('exports/access-shape-edit-bend/graph.snapshot.json')
    if output.exists():
        raise ValueError('Refusing to overwrite graph')
    save_case(output, graph)
    report['graph_file'] = str(output)
    target.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k != 'rows'}), flush=True)


if __name__ == '__main__':
    main()
