"""Live asynchronous API failure contract; no duplicate expensive context run."""
import json
from pathlib import Path
import time
from urllib.request import Request,urlopen
from urllib.error import HTTPError

from vv_toolbox.case_io import load_case,case_digest


def request(path,data=None):
    body=None if data is None else json.dumps(data).encode()
    req=Request('http://127.0.0.1:8093'+path,data=body,headers={'Content-Type':'application/json'})
    try:
        with urlopen(req,timeout=30) as response:return response.status,json.load(response)
    except HTTPError as error:return error.code,json.load(error)


def main():
    root=Path(__file__).resolve().parents[1]
    _,before=request('/api/state')
    assert request('/api/case-context-jobs',{'snapshot':{}})[0]==400
    case,_=load_case(root/'exports/registered-shape-case/case.snapshot.json')
    case['generation']['config']['parent_case_revision']='0'*64
    doc=dict(schema='vv-toolbox.case-snapshot/1',revision=case_digest(case),case=case)
    code,job=request('/api/case-context-jobs',{'snapshot':doc})
    assert code==202
    end=time.monotonic()+30
    while time.monotonic()<end:
        code,state=request('/api/case-context-jobs/'+job['id'])
        assert code==200
        if state['state']!='RUNNING':break
        time.sleep(.2)
    assert state['state']=='ERROR' and 'registered access parent' in state['error']
    assert request('/api/case-context-jobs/'+job['id']+'/result')[0]==409
    assert request('/api/case-context-jobs/not-a-job')[0]==404
    stored=root/'exports/context-jobs'/job['id']
    persisted=json.loads((stored/'status.json').read_text())
    _,stored_revision=load_case(stored/'input.snapshot.json')
    assert persisted['state']=='ERROR' and stored_revision==doc['revision']
    _,after=request('/api/state')
    assert before['source']==after['source'] and before['generation']==after['generation']
    result=dict(status='PASS',scope='Live HTTP submit/status/error/result boundaries; no successful full-context job',
        invalid_snapshot=400,submit=202,unsupported_parent='ERROR',failed_result=409,unknown_job=404,
        atlas_unchanged=True,job_id=job['id'],input_and_error_persisted=True)
    (root/'docs/evidence/context-job-api.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__':main()
