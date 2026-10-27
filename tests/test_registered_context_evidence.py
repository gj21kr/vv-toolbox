from copy import deepcopy
import hashlib
import json

import pytest

from test_registered_shape_edit import sample
from vv_toolbox.case_io import case_digest
from vv_toolbox.registered_context_evidence import attach_registered_context


def fixture(tmp_path):
    case=sample();case['inspection']['registered_shape_edit']={'neighboring_vessels':'NOT RUN'}
    folder=tmp_path/'docs/evidence';folder.mkdir(parents=True)
    context=dict(status='FAIL',completed=1,neighbor_count=1,context_sha256='context',
        rows=[dict(neighbor_id='neighbor',before={'complete':True},after={'complete':True})],
        new_or_extended_contacts=['neighbor'],unknown=[],remaining_contacts=['neighbor'])
    raw=json.dumps(context).encode();(folder/'access-bend-context.json').write_bytes(raw)
    binding=dict(case_revision=case_digest(case),binding='PASS',geometry_equality='EXACT',
        neighbor_count=1,context_sha256='context',status='FAIL',evidence_sha256=hashlib.sha256(raw).hexdigest())
    (folder/'registered-shape-context-binding.json').write_text(json.dumps(binding))
    (folder/'resampled-access-context.json').write_text(json.dumps(dict(context_sha256='context',rows=[{'neighbor_id':'neighbor'}])))
    return case,folder,binding,context


def test_exact_case_attachment_preserves_geometry_and_failed_state(tmp_path):
    case,_,_,context=fixture(tmp_path);before=deepcopy(case)
    result=attach_registered_context(case,tmp_path)
    assert case==before
    assert result['surface_parts']==case['surface_parts'] and result['edges']==case['edges']
    audit=result['inspection']['registered_shape_edit']
    assert audit['neighboring_vessels']=='FAIL' and audit['context']==context
    assert audit['accepted_for_generation'] is False


@pytest.mark.parametrize('damage',['case','bytes','ids','false_pass'])
def test_other_case_or_inconsistent_measurements_rejected(tmp_path,damage):
    case,folder,binding,context=fixture(tmp_path)
    if damage=='case':case['case_id']='other'
    elif damage=='bytes':(folder/'access-bend-context.json').write_text('{}')
    else:
        if damage=='ids':context['rows'][0]['neighbor_id']='different'
        else:context['status']=binding['status']='PASS'
        raw=json.dumps(context).encode();(folder/'access-bend-context.json').write_bytes(raw)
        binding['evidence_sha256']=hashlib.sha256(raw).hexdigest()
        (folder/'registered-shape-context-binding.json').write_text(json.dumps(binding))
    before=deepcopy(case)
    with pytest.raises(ValueError):attach_registered_context(case,tmp_path)
    assert case==before
