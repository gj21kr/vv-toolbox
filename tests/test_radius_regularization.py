from copy import deepcopy

import numpy as np
import pytest

from vv_toolbox.radius_regularization import smooth_synthetic_radii
from vv_toolbox.synthetic_routes import build_synthetic_routes
from test_synthetic_routes import fixture


def base():
    case, spec = fixture()
    case = build_synthetic_routes(case,spec,case_id='synthetic')
    edge = case['edges'][-1]
    edge['centerline_mm'] = [[10+x*.1,0,0] for x in range(101)]
    edge['radii_mm'] = [2+x*.01+(.15 if x%2 else -.15) for x in range(101)]
    edge['radii_mm'][0],edge['radii_mm'][-1] = 2,3
    return case


def apply(case, **kwargs):
    return smooth_synthetic_radii(case,['bridge'],sigma_mm=.5,sample_spacing_mm=.1,
                                  max_change_mm=kwargs.get('max_change_mm',.3),case_id='smoothed')


def test_removes_high_frequency_radius_noise_and_preserves_anchors_and_input():
    case = base()
    before = deepcopy(case)
    result = apply(case)
    original = np.asarray(case['edges'][-1]['radii_mm'])
    smoothed = np.asarray(result['edges'][-1]['radii_mm'])
    assert np.std(np.diff(smoothed[20:80],n=2)) < .05*np.std(np.diff(original[20:80],n=2))
    assert smoothed[[0,-1]].tolist() == original[[0,-1]].tolist()
    assert result['edges'][-1]['centerline_mm'] == case['edges'][-1]['centerline_mm']
    assert result['nodes'] == case['nodes'] and result['edges'][:2] == case['edges'][:2]
    assert result['synthetic_route_inspection']['collision_check']=='NOT RUN'
    assert result['edges'][-1]['radius_transform_history'][0]['anatomical_acceptance']=='UNKNOWN'
    assert case == before
    assert apply(case) == result


def test_excess_change_rejected_without_mutation():
    case = base(); before = deepcopy(case)
    with pytest.raises(ValueError,match='bound'): apply(case,max_change_mm=.01)
    assert case == before


def test_prior_node_changes_are_not_reported_as_original_nodes():
    case = base()
    case['synthetic_route_inspection']['source_nodes_preserved'] = False
    assert apply(case)['synthetic_route_inspection']['source_nodes_preserved'] is False


def test_immutable_source_cannot_be_smoothed():
    case,_ = fixture()
    with pytest.raises(ValueError,match='synthetic'):
        smooth_synthetic_radii(case,['a'],sigma_mm=1,sample_spacing_mm=.2,max_change_mm=.3,case_id='new')


def test_constant_profile_is_preserved():
    case = base()
    case['edges'][-1]['radii_mm'] = [2.]*101
    assert apply(case)['edges'][-1]['radii_mm'] == pytest.approx([2.]*101)


def test_old_surface_approval_is_archived_not_inherited():
    case = base()
    case['quality'] = {'status':'PASS','revision':'previous'}
    case['surface_quality'] = {'watertight':'PASS'}
    case['centerline_regularization'] = {'geometry_quality':'PASS'}
    result = apply(case)
    assert 'quality' not in result and 'surface_quality' not in result
    assert result['radius_regularization']['parent_quality_not_applicable']['quality']==case['quality']
    assert result['centerline_regularization']['geometry_quality']=='NOT RUN'
    assert case['centerline_regularization']['geometry_quality']=='PASS'


def test_existing_disease_profile_is_not_smoothed():
    from test_batch import fixture as lesion_fixture
    from vv_toolbox.lesions import concentric_stenosis
    case, parameters = lesion_fixture()
    case = concentric_stenosis(case,**parameters,seed=1,case_id='diseased')
    before = deepcopy(case)
    with pytest.raises(ValueError,match='lesion'):
        smooth_synthetic_radii(case,['e'],sigma_mm=1,sample_spacing_mm=.2,max_change_mm=1,case_id='bad')
    assert case == before


def test_cli_separate_snapshot_and_input_protection(tmp_path,capsys):
    import json
    from vv_toolbox.case_io import save_case,load_case
    from vv_toolbox.case_cli import main
    source,params,output = [tmp_path/name for name in ('input.json','params.json','output.json')]
    revision = save_case(source,base())
    before = source.read_bytes()
    params.write_text(json.dumps(dict(edge_ids=['bridge'],sigma_mm=.5,sample_spacing_mm=.1,
                                      max_change_mm=.3,case_id='new')))
    assert main(['smooth-radii',str(source),str(params),str(output)])==0
    assert load_case(output)[0]['case_id']=='new'
    with pytest.raises(SystemExit):
        main(['smooth-radii',str(source),str(params),str(source),'--expected-revision',revision])
    assert source.read_bytes()==before
