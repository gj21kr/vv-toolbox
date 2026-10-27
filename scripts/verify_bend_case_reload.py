"""Independently reload the browser-downloaded bend snapshot and compare inputs."""
import hashlib
import json
from pathlib import Path

import numpy as np

from vv_toolbox.case_io import load_case
from vv_toolbox.case_surface import build_case_surface


def main():
    root = Path(__file__).resolve().parents[1]
    path = root/'exports/bend-case-download/case.snapshot.json'
    case, revision = load_case(path)
    graph, graph_revision = load_case(root/'exports/access-shape-edit-bend/graph.snapshot.json')
    assert case['edges'] == graph['edges'] and case['nodes'] == graph['nodes']
    assert case['generation']['config']['parent_graph_revision'] == graph_revision
    vertices, faces, _ = build_case_surface(case, [e['id'] for e in graph['edges']], spacing_mm=1.)
    with np.load(root/'exports/access-shape-edit-bend/candidate.npz', allow_pickle=False) as data:
        np.testing.assert_array_equal(vertices, data['vertices'])
        np.testing.assert_array_equal(faces, data['faces'])
    context = json.loads((root/'docs/evidence/access-bend-context.json').read_text())
    audit = case['inspection']['access_candidate']
    assert audit['context'] == context and context['status'] == 'FAIL'
    assert audit['accepted_for_generation'] is False
    assert audit['radius_surface_consistency'] == 'NOT RUN'
    report = dict(status='PASS', revision=revision, graph_revision=graph_revision,
        file_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        vertices=len(vertices), faces=len(faces), edges=len(case['edges']),
        context_rows=len(context['rows']), context_status=context['status'],
        scope='Downloaded geometry, changed graph and full failed inspection exact roundtrip; not anatomy acceptance')
    (root/'docs/evidence/bend-case-reload.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
