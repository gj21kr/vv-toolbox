import hashlib
import json
import numpy as np
import pytest
from test_surface_context import context
from vv_toolbox.case_io import save_case
from vv_toolbox.candidate_preview import load_candidate_preview,MCA_CANDIDATE_ID
from vv_toolbox.surface_context import inspect_surface_context


@pytest.fixture
def bundle(tmp_path):
    case=context()
    case['edges'][0]['id']='FJ1692:e0'
    revision=save_case(tmp_path/'exports/atlas-case-inspection/all-arterial.snapshot.json',case)
    folder=tmp_path/'exports/union-regularization'
    folder.mkdir(parents=True)
    vertices=np.array([[0,0,0],[.1,0,0],[0,.1,0]])
    faces=np.array([[0,1,2]])
    np.savez_compressed(folder/'surface.npz',vertices_mm=vertices,faces=faces,
        metadata=np.array(json.dumps(dict(case_revision=revision,frame=case['frame']))))
    digest=hashlib.sha256((folder/'surface.npz').read_bytes()).hexdigest()
    audit=inspect_surface_context(case,vertices,faces,parent_edge_id='FJ1692:e0')
    audit['artifact_sha256']=digest
    docs=tmp_path/'docs/evidence';docs.mkdir(parents=True)
    (docs/'union-context-inspection.json').write_text(json.dumps(
        dict(case_revision=revision,reports=dict(after=audit))))
    (docs/'union-regularization.json').write_text(json.dumps(
        dict(case_revision=revision,artifact_sha256=digest)))
    return tmp_path


def test_mca_preview_keeps_unaccepted_context_visible(bundle):
    result=load_candidate_preview(bundle,MCA_CANDIDATE_ID)
    summary=result['summary']
    assert summary['read_only']
    assert summary['context_inspection']['status']=='REVIEW_REQUIRED'
    assert len(summary['context_inspection']['review_edges'])==1
    assert summary['whole_atlas_collision']=='NOT RUN'


@pytest.mark.parametrize('field,value',[
    ('artifact_sha256','0'*64),('context_edge_count',0),
    ('aabb_separated_count',1),('status','SEPARATED_PROFILES')])
def test_mca_preview_rejects_stale_or_inconsistent_audit(bundle,field,value):
    path=bundle/'docs/evidence/union-context-inspection.json'
    report=json.loads(path.read_text())
    report['reports']['after'][field]=value
    path.write_text(json.dumps(report))
    with pytest.raises(ValueError,match='mismatch'):
        load_candidate_preview(bundle,MCA_CANDIDATE_ID)
