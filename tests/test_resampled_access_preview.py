import json

import pytest

import vv_toolbox.resampled_access_preview as module
from test_access_union_preview import fixture as baseline_fixture


def fixture(tmp_path,monkeypatch):
    evidence,path,digest=baseline_fixture(tmp_path)
    original=module.load_access_union_preview
    def base(root):
        result=original(root);result['edges']=[dict(id='edge')]
        result['summary']['access_graph']=dict(revision='graph')
        return result
    monkeypatch.setattr(module,'load_access_union_preview',base)
    parent=json.loads((evidence/'femoral-anterior-union.json').read_text())
    parent['parent_sha256']=digest
    (evidence/'resampled-access-union.json').write_text(json.dumps(parent))
    protected=dict(status='CANDIDATE',artifact=str(path.relative_to(tmp_path)),output_sha256=digest,
        source_case_revision='fixture',parent_sha256=digest,self_contact=dict(status='NO_CONTACT_DETECTED'),
        closed_positive_volume=True,faces_unchanged=True,restoration=dict(status='PASS',protected_positions_exact=True))
    (evidence/'resampled-access-protected.json').write_text(json.dumps(protected))
    paths=dict(status='PASS',surface_sha256=digest,graph_revision='graph',expected_edges=1,
               rows=[dict(edge_id='edge',status='PASS',segment_count=1)])
    (evidence/'resampled-access-paths.json').write_text(json.dumps(paths))
    return evidence,digest


def test_preview_keeps_running_context_and_read_only(tmp_path,monkeypatch):
    evidence,digest=fixture(tmp_path,monkeypatch)
    (evidence/'resampled-access-context.json').write_text(json.dumps(dict(status='RUNNING',
        candidate_sha256=digest,source_case_revision='fixture',neighbor_count=2,completed=1,
        excluded_union_sources=['source'],rows=[dict(neighbor_id='one',status='SEPARATED',complete=True)])))
    result=module.load_resampled_access_preview(tmp_path)
    assert result['summary']['id']==module.CANDIDATE_ID and result['summary']['read_only']
    assert result['summary']['access_union']['context_status']=='RUNNING'
    assert result['summary']['access_union']['context_completed']==1
    assert result['source_centerlines']=={}


@pytest.mark.parametrize('kind',['missing_path','fake_pass','wrong_parent'])
def test_incomplete_or_mismatched_evidence_rejected(tmp_path,monkeypatch,kind):
    evidence,digest=fixture(tmp_path,monkeypatch)
    if kind=='missing_path':
        path=evidence/'resampled-access-paths.json';record=json.loads(path.read_text());record['rows']=[]
    elif kind=='wrong_parent':
        path=evidence/'resampled-access-protected.json';record=json.loads(path.read_text());record['parent_sha256']='bad'
    else:
        path=evidence/'resampled-access-context.json';record=dict(status='PASS',candidate_sha256=digest,
            source_case_revision='fixture',neighbor_count=2,completed=0,rows=[],excluded_union_sources=['source'])
    path.write_text(json.dumps(record))
    with pytest.raises(ValueError):module.load_resampled_access_preview(tmp_path)


def test_edit_paths_bind_to_matching_source_case(tmp_path, monkeypatch):
    from vv_toolbox import case_io
    evidence, _ = fixture(tmp_path, monkeypatch)
    (evidence/'atlas-neck-volume-case.json').write_text(json.dumps(dict(derived_case_file='case.json')))
    case = dict(surface_parts=[dict(part_id='source', edge_ids=['edge'])],
                edges=[dict(id='edge', centerline_mm=[[0, 0, 0], [0, 0, 1]])])
    monkeypatch.setattr(case_io, 'load_case', lambda path: (case, 'fixture'))
    result = module.load_resampled_access_preview(tmp_path)
    assert result['summary']['radius_path_sources'] == ['source']
    assert result['source_centerlines']['source']['case_revision'] == 'fixture'
    monkeypatch.setattr(case_io, 'load_case', lambda path: (case, 'different'))
    with pytest.raises(ValueError, match='revision mismatch'):
        module.load_resampled_access_preview(tmp_path)
