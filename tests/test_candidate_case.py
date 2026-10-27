from copy import deepcopy
import hashlib
import json

import numpy as np
import pytest
import trimesh

from test_case_surface import example
from vv_toolbox.candidate_case import candidate_snapshot, displayed_candidate_snapshot
from vv_toolbox.case_io import case_digest, load_case, save_case
from vv_toolbox.case_surface import build_case_surface


def fixture():
    graph = example()
    mesh = trimesh.creation.box(extents=[20, 4, 2])
    mesh.vertices += [10, 0, 0]
    candidate = dict(vertices_mm=mesh.vertices.copy(), faces=mesh.faces.copy(),
        edges=deepcopy(graph['edges']), face_lineage={'scope': 'fixture'},
        summary=dict(revision='source-revision', surface_sha256='a'*64,
                     access_graph={'revision': case_digest(graph)},
                     access_union={'context_status': 'FAIL'}, anatomy='UNKNOWN'))
    return graph, candidate


@pytest.mark.parametrize('edited', [False, True])
def test_snapshot_preserves_displayed_geometry_and_failed_evidence(tmp_path, edited):
    graph, candidate = fixture()
    original = deepcopy(graph)
    if edited:
        candidate['vertices_mm'][:, 1] *= 1.05
        candidate['summary']['geometry_sha256'] = hashlib.sha256(
            candidate['vertices_mm'].astype('<f8').tobytes()+candidate['faces'].astype('<i8').tobytes()).hexdigest()
        candidate['summary']['radius_edit'] = {'scale': 1.05}
    result = candidate_snapshot(candidate, graph)
    path = tmp_path/'case.json'
    path.write_text(json.dumps(result))
    case, revision = load_case(path)
    v, f, _ = build_case_surface(case, ['e'], spacing_mm=1.)
    np.testing.assert_array_equal(v, candidate['vertices_mm'])
    np.testing.assert_array_equal(f, candidate['faces'])
    assert graph == original and case['edges'] == original['edges']
    assert revision == result['revision']
    audit = case['inspection']['access_candidate']
    assert audit['summary']['access_union']['context_status'] == 'FAIL'
    assert audit['accepted_for_generation'] is False
    assert audit['radius_surface_consistency'] == 'NOT RUN'


@pytest.mark.parametrize('damage', ['graph', 'geometry', 'faces'])
def test_mismatched_candidate_rejected(damage):
    graph, candidate = fixture()
    if damage == 'graph':
        candidate['edges'] = []
    elif damage == 'geometry':
        candidate['summary']['geometry_sha256'] = '0'*64
    else:
        candidate['faces'] = candidate['faces'].astype(float)+.1
    with pytest.raises(ValueError):
        candidate_snapshot(candidate, graph)


def test_bend_snapshot_uses_changed_graph_and_keeps_context(tmp_path):
    graph, candidate = fixture()
    candidate['summary']['id'] = 'access-femoral-bend-inspection'
    graph['case_id'] = 'changed-bend'
    candidate['summary']['access_graph']['revision'] = case_digest(graph)
    candidate['geometry_context'] = {'status':'FAIL', 'rows':[{'neighbor_id':'a'}]}
    path = tmp_path/'exports/access-shape-edit-bend/graph.snapshot.json'
    path.parent.mkdir(parents=True)
    save_case(path, graph)
    result = displayed_candidate_snapshot(candidate, tmp_path)
    audit = result['case']['inspection']['access_candidate']
    assert audit['context'] == candidate['geometry_context']
    assert audit['accepted_for_generation'] is False
    assert result['case']['generation']['config']['parent_graph_revision'] == case_digest(graph)
    audit['context']['rows'].clear()
    assert candidate['geometry_context']['rows']
    graph['case_id'] = 'stale-bend'
    save_case(path, graph, expected_revision=candidate['summary']['access_graph']['revision'])
    with pytest.raises(ValueError, match='graph identity'):
        displayed_candidate_snapshot(candidate, tmp_path)
