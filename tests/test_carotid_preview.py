import hashlib
import json

import numpy as np
import pytest
import trimesh

from vv_toolbox.carotid_preview import load_carotid_preview


def fixture(root):
    evidence=root/'docs/evidence';evidence.mkdir(parents=True)
    folder=root/'exports/carotid-solid-union-diagnostic-float64-lineage';folder.mkdir(parents=True)
    pid='estimated_left_carotid_neck';mesh=trimesh.creation.box()
    path=folder/(pid+'.npz')
    np.savez_compressed(path,vertices=mesh.vertices,faces=mesh.faces)
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    reports={
        'carotid-solid-union-diagnostic-float64-lineage.json':dict(source_case_revision='fixture',
            rows=[dict(part_id=pid,status='CANDIDATE',boundary_components=1,
                       self_contact=dict(status='NO_CONTACT_DETECTED'),
                       face_lineage=dict(source_names=['source','estimate'],
                                         face_source_indices=[0]*6+[1]*6,
                                         source_face_indices=list(range(12))))]),
        'carotid-union-lineage.json':dict(source_case_revision='fixture',rows=[
            dict(part_id=pid,status='PASS',union_sha256=digest,faces=len(mesh.faces))]),
        'carotid-union-paths.json':dict(source_case_revision='fixture',rows=[
            dict(part_id=pid,status='PASS',union_file_sha256=digest,segment_count=95)]),
        'carotid-union-neighbors.json':dict(union_files=[dict(part_id=pid,sha256=digest)],
            new_contacting_neighbors=[],unknown=[])}
    for name,value in reports.items():(evidence/name).write_text(json.dumps(value))
    return path,evidence


def test_registered_preview_loads_with_explicit_limits(tmp_path):
    fixture(tmp_path)
    result=load_carotid_preview(tmp_path,'left-carotid-solid-union')
    assert result['summary']['read_only']
    assert result['summary']['smoothness']=='NOT RUN'
    assert result['faces'].shape==(12,3)


def test_changed_geometry_rejected(tmp_path):
    path,_=fixture(tmp_path)
    path.write_bytes(path.read_bytes()+b'changed')
    with pytest.raises(ValueError,match='evidence'):
        load_carotid_preview(tmp_path,'left-carotid-solid-union')


def test_revision_mismatch_rejected(tmp_path):
    _,folder=fixture(tmp_path)
    path=folder/'carotid-union-lineage.json'
    data=json.loads(path.read_text());data['source_case_revision']='other'
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError,match='revisions'):
        load_carotid_preview(tmp_path,'left-carotid-solid-union')


def test_workspace_description_supports_carotid_summary(tmp_path):
    from types import SimpleNamespace
    from vv_toolbox.app import Workspace
    fixture(tmp_path)
    candidate=load_carotid_preview(tmp_path,'left-carotid-solid-union')
    description=Workspace.description(SimpleNamespace(source='candidate',candidate=candidate),None)
    assert '95개 구간' in description and '미확인' in description


def test_candidate_source_selection_and_return_preserve_geometry(tmp_path):
    from types import SimpleNamespace
    from vv_toolbox.app import Workspace
    fixture(tmp_path)
    candidate=load_carotid_preview(tmp_path,'left-carotid-solid-union')
    faces=candidate['faces'].copy();vertices=candidate['vertices_mm'].copy()
    workspace=SimpleNamespace(source='candidate',candidate=candidate,generation=1,draw_candidate=lambda:None)
    Workspace.select_candidate_source(workspace,'source')
    assert len(candidate['display_faces'])==6
    assert candidate['summary']['selected_source']=='source'
    Workspace.select_candidate_source(workspace,None)
    assert 'display_faces' not in candidate
    assert workspace.generation==3
    assert np.array_equal(candidate['faces'],faces) and np.array_equal(candidate['vertices_mm'],vertices)


def test_unknown_source_does_not_mutate_candidate(tmp_path):
    from types import SimpleNamespace
    from vv_toolbox.app import Workspace
    fixture(tmp_path);candidate=load_carotid_preview(tmp_path,'left-carotid-solid-union')
    workspace=SimpleNamespace(source='candidate',candidate=candidate,generation=1,draw_candidate=lambda:None)
    with pytest.raises(ValueError):Workspace.select_candidate_source(workspace,'not-a-source')
    assert workspace.generation==1 and 'display_faces' not in candidate
