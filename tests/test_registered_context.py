from copy import deepcopy

import pytest
import trimesh

from test_registered_shape_edit import sample,edit
from vv_toolbox.registered_context import inspect_registered_context,context_fingerprint,case_with_context
from vv_toolbox.case_io import case_digest


def fixture():
    parent=sample();case=edit(parent)
    mesh=trimesh.creation.box();mesh.apply_translation([10,0,0])
    neighbors={'distant':mesh}
    return parent,case,neighbors


def test_new_inspection_bound_to_case_parent_and_complete_context():
    parent,case,neighbors=fixture();before=deepcopy(case);events=[]
    report=inspect_registered_context(case,parent,neighbors,
        expected_context_sha256=context_fingerprint(neighbors),expected_neighbor_ids=['distant'],progress=events.append)
    assert report['status']=='PASS' and report['completed']==1
    assert events[-1]['completed']==1
    assert report['case_revision']==case_digest(case)
    result=case_with_context(case,report)
    assert case==before and result['surface_parts']==case['surface_parts']
    assert result['inspection']['registered_shape_edit']['accepted_for_generation'] is False


@pytest.mark.parametrize('damage',['parent','context','missing'])
def test_unmatched_inputs_rejected_before_work(damage,monkeypatch):
    parent,case,neighbors=fixture();digest=context_fingerprint(neighbors)
    if damage=='parent':parent['case_id']='different'
    elif damage=='context':neighbors['distant'].vertices[0,0]+=1
    else:neighbors={}
    monkeypatch.setattr('vv_toolbox.registered_context.inspect_radius_context',lambda *a,**k:pytest.fail('must not run'))
    with pytest.raises(ValueError):inspect_registered_context(case,parent,neighbors,
        expected_context_sha256=digest,expected_neighbor_ids=['distant'])


@pytest.mark.parametrize('damage',['other_case','contradictory_pass'])
def test_result_cannot_be_attached_to_wrong_or_inconsistent_case(damage):
    parent,case,neighbors=fixture()
    report=inspect_registered_context(case,parent,neighbors,
        expected_context_sha256=context_fingerprint(neighbors),expected_neighbor_ids=['distant'])
    if damage=='other_case':case['case_id']='other'
    else:report['rows'][0]['after']['status']='CONTAINMENT'
    with pytest.raises(ValueError):case_with_context(case,report)


def test_fresh_measurement_archives_prior_context_and_its_binding():
    parent,case,neighbors=fixture()
    audit=case['inspection']['registered_shape_edit']
    previous={'context':{'status':'UNKNOWN','case_revision':'old'},
              'context_binding':{'report_sha256':'previous-report'}}
    audit.update(deepcopy(previous))
    before=deepcopy(case)
    report=inspect_registered_context(case,parent,neighbors,
        expected_context_sha256=context_fingerprint(neighbors),expected_neighbor_ids=['distant'])
    result=case_with_context(case,report)
    current=result['inspection']['registered_shape_edit']
    assert 'context_binding' not in current
    assert current['context_history']==[previous]
    assert current['context']==report
    assert current['neighboring_vessels']=='PASS'
    assert case==before
    assert result['surface_parts']==case['surface_parts']
    assert result['edges']==case['edges']
    assert current['accepted_for_generation'] is False
