"""Single-flight context inspections with revision-bound results."""
from copy import deepcopy
from threading import Lock, Thread
import uuid
import json
from pathlib import Path
import re

from .case_io import case_digest,save_case,load_case
from .registered_context import case_with_context


class ContextJobBusy(ValueError):
    pass


class ContextJobs:
    """One running computation; retain the latest four jobs in this process.

    The runner receives an immutable-by-convention input copy and a progress
    callback, and returns a complete report. No scene/workspace is mutated.
    """
    def __init__(self, runner, store=None):
        self.runner=runner
        self.lock=Lock()
        self.jobs={}
        self.active=None
        self.store=Path(store) if store is not None else None
        if self.store is not None:
            self.store.mkdir(parents=True,exist_ok=True)
            self._restore()

    def _persist(self,job):
        if self.store is None:return
        directory=self.store/job['id'];directory.mkdir(parents=True,exist_ok=True)
        temporary=directory/'status.tmp'
        temporary.write_text(json.dumps(self._public(job),indent=2)+'\n')
        temporary.replace(directory/'status.json')

    def _restore(self):
        paths=[p for p in self.store.glob('*/status.json') if re.fullmatch('[0-9a-f]{32}',p.parent.name)]
        for path in sorted(paths,key=lambda p:p.stat().st_mtime)[-4:]:
            token=path.parent.name
            try:
                job=json.loads(path.read_text())
                if job['id']!=token or job['state'] not in ('RUNNING','COMPLETE','ERROR','INTERRUPTED'):
                    raise ValueError('Invalid stored job state')
                _,revision=load_case(path.parent/'input.snapshot.json')
                if revision!=job['case_revision']:raise ValueError('Stored input revision mismatch')
                job['result']=None
                if job['state']=='RUNNING':
                    job.update(state='INTERRUPTED',phase='interrupted',error='Server stopped before completion; not restarted automatically')
                elif job['state']=='COMPLETE':
                    case,result_revision=load_case(path.parent/'result.snapshot.json')
                    report=case['inspection']['registered_shape_edit']['context']
                    if (result_revision!=job['result_revision'] or report['case_revision']!=revision
                            or report['status']!=job['inspection_status']
                            or report['completed']!=job['completed'] or report['neighbor_count']!=job['total']):
                        raise ValueError('Stored result identity mismatch')
                    job['result']=dict(schema='vv-toolbox.case-snapshot/1',revision=result_revision,case=case)
            except (OSError,ValueError,KeyError,TypeError) as error:
                job=dict(id=token,state='ERROR',phase='recovery_failed',case_revision=None,
                         completed=0,total=None,result=None,error=str(error))
            self.jobs[token]=job
            if job['phase']!='recovery_failed':self._persist(job)

    def start(self, case):
        snapshot=deepcopy(case)
        revision=case_digest(snapshot)
        with self.lock:
            if self.active:
                active=self.jobs[self.active]
                if active['case_revision']==revision:
                    return self._public(active)
                raise ContextJobBusy('Another context inspection is running')
            while len(self.jobs)>=4:
                del self.jobs[next(iter(self.jobs))]
            token=uuid.uuid4().hex
            job=dict(id=token,state='RUNNING',phase='preparing',case_revision=revision,
                     completed=0,total=None,result=None,error=None)
            self.jobs[token]=job;self.active=token
            try:
                if self.store is not None:
                    directory=self.store/token;directory.mkdir(parents=True,exist_ok=True)
                    save_case(directory/'input.snapshot.json',snapshot)
                    self._persist(job)
                Thread(target=self._run,args=(token,snapshot),daemon=True).start()
            except Exception:
                self.jobs.pop(token);self.active=None
                raise
            return self._public(job)

    def _public(self, job):
        return deepcopy({k:v for k,v in job.items() if k!='result'})

    def status(self, token):
        with self.lock:
            if token not in self.jobs:raise ValueError('Unknown or expired context job')
            return self._public(self.jobs[token])

    def result(self, token):
        with self.lock:
            if token not in self.jobs:raise ValueError('Unknown or expired context job')
            job=self.jobs[token]
            if job['state']!='COMPLETE':raise ValueError('Context result is not complete')
            return deepcopy(job['result'])

    def _run(self, token, case):
        def progress(event):
            completed,total=event['completed'],event['total']
            with self.lock:
                job=self.jobs[token]
                if (type(completed) is not int or type(total) is not int or total<1
                        or not job['completed']<=completed<=total
                        or (job['total'] is not None and job['total']!=total)):
                    raise ValueError('Invalid context progress')
                job.update(phase='inspecting',completed=completed,total=total)
                self._persist(job)
        try:
            report=self.runner(case,progress)
            if report['case_revision']!=self.jobs[token]['case_revision']:
                raise ValueError('Context job returned another case revision')
            result=case_with_context(case,report)
            document=dict(schema='vv-toolbox.case-snapshot/1',revision=case_digest(result),case=result)
            if self.store is not None:
                save_case(self.store/token/'result.snapshot.json',result)
            with self.lock:
                self.jobs[token].update(state='COMPLETE',phase='complete',completed=report['completed'],
                    total=report['neighbor_count'],inspection_status=report['status'],result=document,
                    result_revision=document['revision'])
                self._persist(self.jobs[token])
                self.active=None
        except Exception as error:
            with self.lock:
                self.jobs[token].update(state='ERROR',phase='failed',error=str(error),result=None)
                try:self._persist(self.jobs[token])
                finally:self.active=None
