import json

import pytest

from vv_toolbox.case_cli import main
from vv_toolbox.case_io import load_case, save_case
from vv_toolbox.anatomical_labels import resolve_labels
from test_synthetic_routes import fixture


def setup(tmp_path):
    case,_=fixture()
    source=tmp_path/'source.json'
    revision=save_case(source,case)
    request=tmp_path/'labels.json'
    request.write_text(json.dumps(dict(schema='vv-toolbox.access-label-request/1',
        source_case_revision=revision,assignments=[
            dict(edge_id='a',label_id=13,evidence_refs=['synthetic full extent fixture'])])))
    return source,request,tmp_path/'output.json'


def test_registry_and_label_roundtrip(tmp_path,capsys):
    assert main(['label-registry'])==0
    registry=json.loads(capsys.readouterr().out)
    assert len(registry['labels'])==26
    source,request,output=setup(tmp_path)
    original=source.read_bytes()
    assert main(['access-labels',str(source),str(request),str(output)])==0
    summary=json.loads(capsys.readouterr().out)
    assert summary['labels']=={'a':13}
    assert summary['anatomical_acceptance']=='UNKNOWN'
    case,revision=load_case(output)
    assert summary['revision']==revision
    assert resolve_labels(case,['a'])[0]=={'a':13}
    assert source.read_bytes()==original
    result=output.read_bytes()
    with pytest.raises(SystemExit) as error:
        main(['access-labels',str(source),str(request),str(output)])
    assert error.value.code==2 and output.read_bytes()==result


@pytest.mark.parametrize('damage',['stale','schema','duplicate','missing_refs','source_output','request_output'])
def test_bad_requests_preserve_files(tmp_path,damage):
    source,request,output=setup(tmp_path)
    data=json.loads(request.read_text())
    if damage=='stale': data['source_case_revision']='0'*64
    elif damage=='schema': data['schema']='unknown'
    elif damage=='missing_refs': data['assignments'][0]['evidence_refs']=[]
    elif damage=='source_output': output=source
    elif damage=='request_output': output=request
    request.write_text(json.dumps(data))
    if damage=='duplicate':
        request.write_text(request.read_text().replace('"label_id": 13','"label_id": 13, "label_id": 18'))
    original_source,original_request=source.read_bytes(),request.read_bytes()
    with pytest.raises(SystemExit) as error:
        main(['access-labels',str(source),str(request),str(output)])
    assert error.value.code==2
    assert source.read_bytes()==original_source
    assert request.read_bytes()==original_request
    if damage not in ('source_output','request_output'):
        assert not output.exists()


def test_label_then_baseline_batch_cli_exports_left_right_masks(tmp_path,capsys):
    import numpy as np
    from test_batch import two_vessel_fixture
    case,_=two_vessel_fixture()
    source=tmp_path/'source.json'
    revision=save_case(source,case)
    request=tmp_path/'labels.json'
    request.write_text(json.dumps(dict(schema='vv-toolbox.access-label-request/1',
        source_case_revision=revision,assignments=[
            dict(edge_id=edge['id'],label_id=13+index*5,evidence_refs=['synthetic fixture'])
            for index,edge in enumerate(case['edges'])])))
    labelled=tmp_path/'labelled.json'
    assert main(['access-labels',str(source),str(request),str(labelled)])==0
    candidates=tmp_path/'candidates.json'
    candidates.write_text('[[]]')
    grid=tmp_path/'grid.json'
    grid.write_text(json.dumps(dict(grid_config=dict(shape_zyx=[7,17,27],
        spacing_xyz_mm=[1,1,1],origin_xyz_mm=[-3,-3,-3],frame_id='fixture'))))
    output=tmp_path/'batch'
    assert main(['batch',str(labelled),str(candidates),str(output),
        '--target-count','1','--max-attempts','1','--seed','3','--spacing-mm','.3',
        '--mask-config',str(grid)])==0
    with np.load(output/'case-00000/mask.npz') as data:
        assert data['anatomical'][3,3,13]==13
        assert data['anatomical'][3,13,13]==18
        assert not data['lesion_instance'].any()
