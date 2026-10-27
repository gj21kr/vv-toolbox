import importlib.util
from pathlib import Path
from copy import deepcopy
from test_bifurcation_saccular import fixture

module_spec=importlib.util.spec_from_file_location('bifurcation_audit',
    Path(__file__).resolve().parents[1]/'scripts/inspect_atlas_bifurcation_inputs.py')
audit=importlib.util.module_from_spec(module_spec);module_spec.loader.exec_module(audit)


def test_structural_pass_is_not_anatomical_acceptance():
    case,_=fixture();before=deepcopy(case);report=audit.inspect(case)
    assert report['junction_count']==report['structural_pass_count']==1
    assert report['junctions'][0]['anatomical_acceptance']=='UNKNOWN'
    assert not report['accepted_for_generation'] and case==before


def test_missing_centerline_and_endpoint_gap_are_reported():
    case,_=fixture()
    case['edges'][0]['centerline_mm']=None
    case['edges'][1]['centerline_mm'][0]=[1,0,0]
    report=audit.inspect(case);row=report['junctions'][0]
    assert report['structural_pass_count']==0
    assert 'e: unresolved centerline' in row['reasons']
    assert 'c: centerline does not meet junction' in row['reasons']
