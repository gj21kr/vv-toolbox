"""Verify full fresh context measurements and the independently saved case."""
import hashlib
import json
from pathlib import Path

from vv_toolbox.case_io import load_case
from vv_toolbox.registered_context import case_with_context

root=Path(__file__).resolve().parents[1]
report_path=root/'docs/evidence/registered-context-fresh.json'
report=json.loads(report_path.read_text())
previous=json.loads((root/'docs/evidence/access-bend-context.json').read_text())
original,_=load_case(root/'exports/registered-shape-case/case.snapshot.json')
saved_path=root/'exports/registered-context-fresh/case.snapshot.json'
saved,revision=load_case(saved_path)
audit=saved['inspection']['registered_shape_edit']
assert report['completed']==report['neighbor_count']==len(report['rows'])==788
assert report['rows']==previous['rows']
assert report['new_or_extended_contacts']==previous['new_or_extended_contacts']
assert audit['context']['rows']==report['rows'] and audit['context']['status']==report['status']
assert case_with_context(original,audit['context'])==saved
assert saved['surface_parts']==original['surface_parts'] and saved['edges']==original['edges']
assert audit['accepted_for_generation'] is False and revision==report['saved_case_revision']
result=dict(status='PASS',scope='Complete measurement comparison and saved-case reload; not geometry acceptance',
    inspection_status=report['status'],rows=788,prior_rows_equal=True,geometry_graph_unchanged=True,
    output_revision=revision,report_sha256=hashlib.sha256(report_path.read_bytes()).hexdigest(),
    output_sha256=hashlib.sha256(saved_path.read_bytes()).hexdigest(),accepted_for_generation=False)
(root/'docs/evidence/registered-context-result-verification.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
