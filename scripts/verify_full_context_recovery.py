"""Reload a completed actual context job without rerunning its geometry work."""
from pathlib import Path
import hashlib
import json

from vv_toolbox.context_jobs import ContextJobs
from vv_toolbox.case_io import load_case


def main():
    root=Path(__file__).resolve().parents[1]
    ui=json.loads((root/'docs/evidence/full-context-job-ui.json').read_text())
    if ui['status']!='PASS':raise ValueError('Complete actual browser inspection first')
    job_id=ui['job_id']
    cli,cli_revision=load_case(root/'exports/registered-context-fresh/case.snapshot.json')
    browser,browser_revision=load_case(root/'exports/full-context-job-ui/case.snapshot.json')
    assert cli==browser and cli_revision==browser_revision
    store=root/'exports/context-jobs'
    def forbidden(*args,**kwargs):raise AssertionError('Recovery must not start a calculation')
    jobs=ContextJobs(forbidden,store=store)
    status=jobs.status(job_id)
    assert status['state']=='COMPLETE' and status['completed']==status['total']==788
    recovered=jobs.result(job_id)
    assert recovered['case']==cli and recovered['revision']==cli_revision
    assert jobs.active is None
    assert cli['inspection']['registered_shape_edit']['accepted_for_generation'] is False
    evidence=dict(status='PASS',scope='Actual full job loaded by fresh job manager; not an HTTP server restart',
        job_id=job_id,output_revision=cli_revision,cli_browser_saved_result_exact=True,
        restored_completed=788,automatic_calculation_started=False,accepted_for_generation=False,
        inspection_status=status['inspection_status'],
        output_sha256=hashlib.sha256((store/job_id/'result.snapshot.json').read_bytes()).hexdigest())
    (root/'docs/evidence/full-context-recovery.json').write_text(json.dumps(evidence,indent=2)+'\n')
    print(json.dumps(evidence))


if __name__=='__main__':main()
