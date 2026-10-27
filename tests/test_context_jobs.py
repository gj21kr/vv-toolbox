from threading import Event
import time
import json

import pytest

from test_registered_context import fixture
from vv_toolbox.context_jobs import ContextJobs, ContextJobBusy
from vv_toolbox.registered_context import inspect_registered_context,context_fingerprint
from vv_toolbox.case_io import case_digest


def wait(manager,token):
    end=time.monotonic()+5
    while time.monotonic()<end:
        status=manager.status(token)
        if status['state']!='RUNNING':return status
        time.sleep(.01)
    pytest.fail('job did not finish')


def test_duplicate_start_single_flight_and_result_isolation():
    parent,case,neighbors=fixture();revision=case_digest(case)
    entered,release=Event(),Event();calls=[]
    def runner(value,progress):
        calls.append(value);entered.set();assert release.wait(5)
        return inspect_registered_context(value,parent,neighbors,expected_neighbor_ids=['distant'],
            expected_context_sha256=context_fingerprint(neighbors),progress=progress)
    manager=ContextJobs(runner);job=manager.start(case);assert entered.wait(5)
    assert manager.start(case)['id']==job['id']
    case['case_id']='different'
    with pytest.raises(ContextJobBusy):manager.start(case)
    with pytest.raises(ValueError,match='not complete'):manager.result(job['id'])
    release.set();status=wait(manager,job['id'])
    assert status['state']=='COMPLETE' and status['case_revision']==revision and len(calls)==1
    result=manager.result(job['id']);result['case']['case_id']='tampered'
    assert manager.result(job['id'])['case']['case_id']!='tampered'
    assert manager.result(job['id'])['case']['inspection']['registered_shape_edit']['accepted_for_generation'] is False


@pytest.mark.parametrize('failure',['runner','progress','revision'])
def test_failed_jobs_have_no_success_result_and_release_slot(failure):
    _,case,_=fixture()
    def runner(value,progress):
        if failure=='runner':raise ValueError('deliberate failure')
        if failure=='progress':progress({'completed':2,'total':1})
        return {'case_revision':'other'}
    manager=ContextJobs(runner);job=manager.start(case)
    assert wait(manager,job['id'])['state']=='ERROR'
    with pytest.raises(ValueError,match='not complete'):manager.result(job['id'])
    again=manager.start(case);assert again['id']!=job['id']
    assert wait(manager,again['id'])['state']=='ERROR'


@pytest.mark.parametrize('state',['complete','interrupted','corrupt'])
def test_persistent_jobs_restore_without_restarting_computation(tmp_path,state):
    parent,case,neighbors=fixture()
    def runner(value,progress):
        return inspect_registered_context(value,parent,neighbors,expected_neighbor_ids=['distant'],
            expected_context_sha256=context_fingerprint(neighbors),progress=progress)
    manager=ContextJobs(runner,store=tmp_path);job=manager.start(case)
    assert wait(manager,job['id'])['state']=='COMPLETE'
    original=manager.result(job['id']);folder=tmp_path/job['id']
    input_bytes=(folder/'input.snapshot.json').read_bytes()
    if state=='interrupted':
        status=json.loads((folder/'status.json').read_text());status['state']='RUNNING'
        (folder/'status.json').write_text(json.dumps(status))
    if state=='corrupt':(folder/'result.snapshot.json').write_text('{}')
    calls=[]
    restored=ContextJobs(lambda *a:calls.append(a),store=tmp_path)
    assert not calls and restored.active is None
    assert (folder/'input.snapshot.json').read_bytes()==input_bytes
    if state=='complete':
        assert restored.status(job['id'])['state']=='COMPLETE'
        assert restored.result(job['id'])==original
    else:
        assert restored.status(job['id'])['state']==('INTERRUPTED' if state=='interrupted' else 'ERROR')
        with pytest.raises(ValueError,match='not complete'):restored.result(job['id'])
