import hashlib
import json
import numpy as np
import pytest
from test_surface_context import context
from vv_toolbox.case_cli import main
from vv_toolbox.case_io import save_case


@pytest.mark.parametrize('mode', ['clear','overlap','hash','revision','frame'])
def test_context_cli_provenance_and_exit_status(tmp_path,capsys,mode):
    case=context()
    snapshot=tmp_path/'case.json'
    revision=save_case(snapshot,case)
    vertices=np.array([[0,0,0],[.1,0,0],[0,.1,0]])
    if mode=='clear':
        vertices+=100
    metadata=dict(case_revision=revision,frame=case['frame'])
    if mode=='revision':
        metadata['case_revision']='0'*64
    if mode=='frame':
        metadata['frame']=dict(case['frame'],units='m')
    surface=tmp_path/'surface.npz'
    np.savez_compressed(surface,vertices_mm=vertices,faces=[[0,1,2]],
                        metadata=np.array(json.dumps(metadata)))
    before=surface.read_bytes(),snapshot.read_bytes()
    sha=hashlib.sha256(before[0]).hexdigest() if mode!='hash' else '0'*64
    argv=['surface-context',str(snapshot),str(surface),'--parent-edge','e','--sha256',sha]
    if mode in ('hash','revision','frame'):
        with pytest.raises(SystemExit) as exc:
            main(argv)
        assert exc.value.code==2
        assert 'mismatch' in capsys.readouterr().err
    else:
        assert main(argv)==(0 if mode=='clear' else 3)
        result=json.loads(capsys.readouterr().out)
        assert result['case_revision']==revision and result['artifact_sha256']==sha
        assert result['status']==('SEPARATED_PROFILES' if mode=='clear' else 'REVIEW_REQUIRED')
    assert before==(surface.read_bytes(),snapshot.read_bytes())
