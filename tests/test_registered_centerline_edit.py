from copy import deepcopy

import pytest

from test_candidate_case import fixture
from vv_toolbox.candidate_case import candidate_case
from vv_toolbox.case_io import case_digest
from vv_toolbox.label_workbench import process_request


def request():
    graph, candidate = fixture()
    candidate['vertices_mm'][:, 0] = 10 + 1.2*(candidate['vertices_mm'][:, 0]-10)
    edge = graph['edges'][0]
    edge['centerline_mm'] = [[i*2.5, .2*(-1)**i if i not in (0,8) else 0., 0.] for i in range(9)]
    edge['radii_mm'] = [1.] * 9
    candidate['edges'] = deepcopy(graph['edges'])
    candidate['summary']['access_graph']['revision'] = case_digest(graph)
    case = candidate_case(candidate, graph)
    return dict(action='smooth', snapshot=dict(schema='vv-toolbox.case-snapshot/1',
        revision=case_digest(case), case=case),
        parameters=dict(edge_id='e', sigma_mm=1., max_displacement_mm=.5))


def test_registered_wall_is_preserved_and_changed_path_checked():
    req = request()
    original = deepcopy(req)
    result = process_request(req)['snapshot']['case']
    before = req['snapshot']['case']
    assert req == original
    assert result['edges'][0]['centerline_mm'] != before['edges'][0]['centerline_mm']
    assert result['nodes'] == before['nodes']
    old, new = before['surface_parts'][0], result['surface_parts'][0]
    for key in ('vertices_mm', 'faces', 'geometry_sha256', 'face_lineage'):
        assert new[key] == old[key]
    assert new['paths_sha256'] != old['paths_sha256']
    audit = result['inspection']['centerline_edit']
    assert audit['checked_paths'][0]['containment']['status'] == 'PASS'
    assert audit['accepted_for_generation'] is False
    assert result['inspection']['access_candidate'] == before['inspection']['access_candidate']
    case_digest(result)


def test_unproven_containment_rejects_without_mutating(monkeypatch):
    req = request(); before = deepcopy(req)
    monkeypatch.setattr('vv_toolbox.centerline_containment.inspect_centerline_containment',
                        lambda *a, **k: {'status':'UNKNOWN'})
    with pytest.raises(ValueError, match='not proven inside'):
        process_request(req)
    assert req == before
