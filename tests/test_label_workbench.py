from copy import deepcopy

import pytest

from vv_toolbox.case_io import case_digest
from vv_toolbox.label_workbench import process_request
from test_synthetic_routes import fixture


def request():
    case,_=fixture()
    return dict(action='inspect',snapshot=dict(schema='vv-toolbox.case-snapshot/1',
        revision=case_digest(case),case=case),assignments=[])


def test_inspect_apply_roundtrip_and_input_isolation():
    req=request();before=deepcopy(req)
    inspected=process_request(req)
    assert len(inspected['labels'])==14
    assert inspected['edges'][0]['label_id']==0
    req.update(action='apply',assignments=[dict(edge_id='a',label_id=13,evidence_refs=['fixture'])])
    applied=process_request(req)
    assert applied['edges'][0]['label_id']==13
    assert applied['anatomical_acceptance']=='UNKNOWN'
    assert req['snapshot']==before['snapshot']
    assert process_request(dict(action='inspect',snapshot=applied['snapshot'],assignments=[]))==applied


def test_registered_candidate_inspection_roundtrip_preserves_surface_and_failure():
    from test_candidate_case import fixture as candidate_fixture
    from vv_toolbox.candidate_case import candidate_snapshot
    graph, candidate = candidate_fixture()
    candidate['geometry_context'] = {'status':'FAIL', 'rows':[{'neighbor_id':'a'}]}
    snapshot = candidate_snapshot(candidate, graph)
    inspected = process_request(dict(action='inspect', snapshot=snapshot, assignments=[]))
    assert inspected['snapshot'] == snapshot
    assert inspected['snapshot']['case']['surface_parts'] == snapshot['case']['surface_parts']
    assert inspected['snapshot']['case']['inspection']['access_candidate']['context']['status'] == 'FAIL'
    assert inspected['snapshot']['case']['inspection']['access_candidate']['accepted_for_generation'] is False


@pytest.mark.parametrize('damage',['hash','schema','unknown_action','extra','missing_refs','inspect_assignments'])
def test_invalid_input_does_not_mutate(damage):
    req=request()
    if damage=='hash':req['snapshot']['revision']='0'*64
    elif damage=='schema':req['snapshot']['schema']='bad'
    elif damage=='unknown_action':req['action']='save'
    elif damage=='extra':req['path']='any-file'
    elif damage=='missing_refs':req.update(action='apply',assignments=[dict(edge_id='a',label_id=13)])
    else:req['assignments']=[{}]
    before=deepcopy(req)
    with pytest.raises(ValueError):process_request(req)
    assert req==before


def test_serialized_snapshot_preserves_float_and_negative_zero_hash(tmp_path):
    import json
    from vv_toolbox.case_io import load_case
    req=request()
    case=req['snapshot']['case']
    case['edges'][0]['radii_mm'][0]=1.0
    case['edges'][0]['centerline_mm'][0][1]=-0.0
    req['snapshot']['revision']=case_digest(case)
    req['snapshot']=json.dumps(req['snapshot'])
    result=process_request(req)
    assert '1.0' in result['snapshot_json'] and '-0.0' in result['snapshot_json']
    applied=process_request(dict(action='apply',snapshot=result['snapshot_json'],
        assignments=[dict(edge_id='a',label_id=13,evidence_refs=['fixture'])]))
    path=tmp_path/'download.json'
    path.write_text(applied['snapshot_json'])
    loaded,revision=load_case(path)
    assert revision==applied['snapshot']['revision']
    assert loaded['edges'][0]['anatomy']['artery']=='femoral'


def smoothing_request():
    req=request()
    case=req['snapshot']['case']
    case['edges'][0]['centerline_mm']=[[i*1.25,0 if i in (0,8) else .15*(-1)**i,0] for i in range(9)]
    case['edges'][0]['radii_mm']=[1]*9
    req['snapshot']['revision']=case_digest(case)
    req.pop('assignments')
    req.update(action='smooth',parameters=dict(edge_id='a',sigma_mm=.5,max_displacement_mm=.3))
    return req


def test_smooth_source_in_separate_copy_and_preserve_endpoints():
    req=smoothing_request();before=deepcopy(req)
    result=process_request(req)
    case=result['snapshot']['case'];original=req['snapshot']['case']
    assert req==before and case['model_kind']=='synthetic'
    assert case['case_id']!=original['case_id']
    assert case['nodes']==original['nodes']
    assert case['edges'][1:]==original['edges'][1:]
    old,new=original['edges'][0],case['edges'][0]
    assert old['centerline_mm']!=new['centerline_mm']
    for i in (0,1,-2,-1):assert old['centerline_mm'][i]==new['centerline_mm'][i]
    assert old['radii_mm']==new['radii_mm']
    assert case['centerline_regularization']['geometry_quality']=='NOT RUN'
    assert process_request(req)==result
    other=deepcopy(req)
    other['parameters']['sigma_mm']=.6
    assert process_request(other)['snapshot']['case']['case_id']!=case['case_id']


@pytest.mark.parametrize('parameters',[
    dict(edge_id='a',sigma_mm=True,max_displacement_mm=.3),
    dict(edge_id='a',sigma_mm=20,max_displacement_mm=.3),
    dict(edge_id='a',sigma_mm=.5,max_displacement_mm=.000001),
    dict(edge_id='missing',sigma_mm=.5,max_displacement_mm=.3)])
def test_failed_smoothing_preserves_source(parameters):
    req=smoothing_request();req['parameters']=parameters;before=deepcopy(req)
    with pytest.raises(ValueError):process_request(req)
    assert req==before
