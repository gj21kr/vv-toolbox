from copy import deepcopy
import hashlib
import json

import numpy as np
import pytest

import vv_toolbox.bend_preview as module
from test_union_radius import fixture as mesh_fixture
from test_case_surface import example
from vv_toolbox.case_io import save_case


def fixture(tmp_path, monkeypatch):
    mesh, lineage = mesh_fixture()
    base = dict(vertices_mm=mesh.vertices.copy(), faces=mesh.faces.copy(), face_lineage=lineage,
                summary=dict(surface_sha256='parent', access_graph={'revision':'before'}, access_union={}))
    monkeypatch.setattr(module, 'load_resampled_access_preview', lambda root: deepcopy(base))
    folder = tmp_path/'exports/access-shape-edit-bend'
    folder.mkdir(parents=True)
    evidence = tmp_path/'docs/evidence'
    evidence.mkdir(parents=True)
    revision = save_case(folder/'graph.snapshot.json', example())
    np.savez(folder/'candidate.npz', vertices=mesh.vertices, faces=mesh.faces)
    digest = hashlib.sha256(mesh.vertices.astype('<f8').tobytes()+mesh.faces.astype('<i8').tobytes()).hexdigest()
    records = {
        'access-shape-edit-bend': dict(status='CANDIDATE', parent_surface_sha256='parent', source='middle',
                                     audit={'self_contact':{'status':'NO_CONTACT_DETECTED'}}),
        'access-bend-graph': dict(status='PASS', graph_revision=revision, parent_graph_revision='before',
                                 geometry_sha256=digest, rows=[dict(edge_id='e',status='PASS')]),
        'access-bend-context': dict(status='RUNNING', before_sha256='parent',
            after_sha256=hashlib.sha256((folder/'candidate.npz').read_bytes()).hexdigest(),
            context_sha256='neighbors', neighbor_count=2, completed=0, rows=[]),
        'resampled-access-context': dict(context_sha256='neighbors', neighbor_count=2,
            rows=[dict(neighbor_id='a'), dict(neighbor_id='b')])}
    for name, record in records.items():
        (evidence/f'{name}.json').write_text(json.dumps(record))
    return evidence


def test_read_only_preview_preserves_pending_context(tmp_path, monkeypatch):
    fixture(tmp_path, monkeypatch)
    result = module.load_bend_preview(tmp_path)
    assert result['summary']['read_only']
    assert result['summary']['radius_path_sources'] == []
    assert result['summary']['access_union']['context_status'] == 'RUNNING'
    assert result['summary']['access_union']['checked_paths'] == 1


@pytest.mark.parametrize('damage', ['graph_hash', 'missing_edge', 'incomplete_pass', 'wrong_neighbors'])
def test_mismatched_evidence_rejected(tmp_path, monkeypatch, damage):
    evidence = fixture(tmp_path, monkeypatch)
    filename = 'access-bend-graph' if damage in ('graph_hash','missing_edge') else 'access-bend-context'
    path = evidence/f'{filename}.json'
    record = json.loads(path.read_text())
    if damage == 'graph_hash': record['geometry_sha256'] = 'wrong'
    elif damage == 'missing_edge': record['rows'] = []
    elif damage == 'incomplete_pass': record['status'] = 'PASS'
    else: record['context_sha256'] = 'wrong'
    path.write_text(json.dumps(record))
    with pytest.raises(ValueError): module.load_bend_preview(tmp_path)


@pytest.mark.parametrize('terminal', [False, True])
def test_substituted_neighbor_rejected_even_with_matching_count_and_hash(tmp_path, monkeypatch, terminal):
    evidence = fixture(tmp_path, monkeypatch)
    path = evidence/'access-bend-context.json'
    record = json.loads(path.read_text())
    record['rows'] = [dict(neighbor_id='unrelated',
        before=dict(status='SEPARATED', complete=True), after=dict(status='SEPARATED', complete=True))]
    if terminal:
        record['status'] = 'PASS'
        record['rows'].append(dict(neighbor_id='a',
            before=dict(status='SEPARATED', complete=True), after=dict(status='SEPARATED', complete=True)))
    record['completed'] = len(record['rows'])
    path.write_text(json.dumps(record))
    with pytest.raises(ValueError, match='context evidence mismatch'):
        module.load_bend_preview(tmp_path)
