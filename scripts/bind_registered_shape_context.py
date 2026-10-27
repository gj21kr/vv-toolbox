"""Bind existing contact measurements only after exact before/after geometry equality."""
import hashlib
import json
from pathlib import Path

import numpy as np

from vv_toolbox.case_io import load_case


def main():
    root=Path(__file__).resolve().parents[1]
    evidence=root/'docs/evidence'
    candidate,revision=load_case(root/'exports/registered-shape-case/case.snapshot.json')
    parent,parent_revision=load_case(root/'exports/candidate-case-download/case.snapshot.json')
    assert candidate['generation']['config']['parent_case_revision']==parent_revision
    assert len(candidate['surface_parts'])==len(parent['surface_parts'])==1
    report_path=evidence/'access-bend-context.json'
    context=json.loads(report_path.read_text())
    baseline=json.loads((evidence/'resampled-access-context.json').read_text())
    before=root/'exports/resampled-access-union/protected-candidate.npz'
    after=root/'exports/access-shape-edit-bend/candidate.npz'
    for case,path,key in [(parent,before,'before_sha256'),(candidate,after,'after_sha256')]:
        assert hashlib.sha256(path.read_bytes()).hexdigest()==context[key]
        part=case['surface_parts'][0]
        with np.load(path,allow_pickle=False) as data:
            np.testing.assert_array_equal(part['vertices_mm'],data['vertices'])
            np.testing.assert_array_equal(part['faces'],data['faces'])
    ids=[r['neighbor_id'] for r in context['rows']]
    assert context['completed']==context['neighbor_count']==len(ids)==len(set(ids))==788
    assert set(ids)=={r['neighbor_id'] for r in baseline['rows']}
    assert context['context_sha256']==baseline['context_sha256']
    assert context['status']=='FAIL'
    result=dict(status='FAIL',binding='PASS',case_revision=revision,parent_revision=parent_revision,
        evidence_sha256=hashlib.sha256(report_path.read_bytes()).hexdigest(),
        context_sha256=context['context_sha256'],neighbor_count=len(ids),
        changed_contacts=context['new_or_extended_contacts'],
        scope='Existing fixed-context contact measurements bound by exact before/after vertex and triangle equality; no rerun',
        geometry_equality='EXACT',accepted_for_generation=False,
        anatomical_classification='UNKNOWN',case_snapshot_modified=False)
    (evidence/'registered-shape-context-binding.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__':
    main()
