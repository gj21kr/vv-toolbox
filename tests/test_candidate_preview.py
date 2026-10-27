import hashlib
import json
import numpy as np
import pytest
from test_geometry_quality import crossing
from vv_toolbox.case_io import save_case,case_digest
from vv_toolbox.candidate_preview import load_candidate_preview,CANDIDATE_ID


@pytest.fixture
def bundle(tmp_path):
    c=crossing();revision=case_digest(c)
    path=tmp_path/'exports/synthetic-full-iliac-profiles/case.snapshot.json';path.parent.mkdir(parents=True)
    save_case(path,c)
    path=tmp_path/'exports/full-iliac-surface/surface.npz';path.parent.mkdir(parents=True)
    metadata=dict(case_revision=revision,frame=c['frame'],edge_ids=['first'])
    np.savez_compressed(path,vertices_mm=np.array([[0.,0.,0.],[1.,0.,0.],[0.,1.,0.]]),
                        faces=np.array([[0,1,2]]),metadata=np.array(json.dumps(metadata)))
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    docs=tmp_path/'docs/evidence';docs.mkdir(parents=True)
    (docs/'full-iliac-surface.json').write_text(json.dumps(dict(case_revision=revision,edge_ids=['first'],
        spacing_mm=.15,surface=dict(status='PASS',sha256=digest,vertices=3,triangles=1))))
    (docs/'full-iliac-mesh-separation.json').write_text(json.dumps(dict(case_revision=revision,
        surface_sha256=digest,separation=dict(status='UNKNOWN',triangle_separation_bound_mm=-1))))
    return tmp_path


def test_selected_scope_and_unknown_retained(bundle):
    result=load_candidate_preview(bundle,CANDIDATE_ID)
    assert [e['id'] for e in result['edges']]==['first']
    assert result['summary']['pair_surface_separation']=='UNKNOWN'
    assert result['summary']['whole_atlas_collision']=='NOT RUN'
    assert result['summary']['read_only']


def test_unknown_candidate_cannot_select_path(bundle):
    with pytest.raises(ValueError,match='unknown'):load_candidate_preview(bundle,'../elsewhere')


@pytest.mark.parametrize('filename',['full-iliac-surface.json','full-iliac-mesh-separation.json'])
def test_stale_evidence_rejected(bundle,filename):
    path=bundle/'docs/evidence'/filename;data=json.loads(path.read_text());data['case_revision']='0'*64
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError,match='mismatch'):load_candidate_preview(bundle,CANDIDATE_ID)


def test_modified_mesh_rejected(bundle):
    path=bundle/'exports/full-iliac-surface/surface.npz';path.write_bytes(path.read_bytes()+b'changed')
    with pytest.raises(ValueError,match='mismatch'):load_candidate_preview(bundle,CANDIDATE_ID)


@pytest.mark.parametrize('kind',['nonfinite','bad-index','float-index','wrong-frame'])
def test_invalid_archive_contract_even_with_matching_hash(bundle,kind):
    path=bundle/'exports/full-iliac-surface/surface.npz'
    with np.load(path,allow_pickle=False) as data:
        arrays={k:data[k].copy() for k in data.files}
    if kind=='nonfinite':arrays['vertices_mm'][0,0]=np.nan
    elif kind=='bad-index':arrays['faces'][0,0]=99
    elif kind=='float-index':arrays['faces']=arrays['faces'].astype(float)
    else:
        metadata=json.loads(str(arrays['metadata'].item()));metadata['frame']['units']='m'
        arrays['metadata']=np.array(json.dumps(metadata))
    np.savez_compressed(path,**arrays);digest=hashlib.sha256(path.read_bytes()).hexdigest()
    for name in ['full-iliac-surface.json','full-iliac-mesh-separation.json']:
        report=bundle/'docs/evidence'/name;value=json.loads(report.read_text())
        if name=='full-iliac-surface.json':value['surface']['sha256']=digest
        else:value['surface_sha256']=digest
        report.write_text(json.dumps(value))
    with pytest.raises(ValueError):load_candidate_preview(bundle,CANDIDATE_ID)
