from copy import deepcopy

import pytest

from vv_toolbox.lesions import concentric_stenosis


def inputs():
    case = {'schema':'vv-toolbox.case/1', 'case_id':'base', 'base_model_id':'anatomy',
        'model_kind':'source','split':'unassigned','generation':None,
        'frame':{'id':'fixture','units':'mm','axes':'LPS','origin':'fixture'},
        'sources':[{'id':'s','sha256':'a'*64,'license_ref':'fixture'}],
        'nodes':{n:{'kind':'unresolved','evidence_status':'unresolved','position_mm':p}
                 for n,p in [('a',[0,0,0]),('b',[20,0,0])]},
        'edges':[{'id':'e','start':'a','end':'b','source_ids':['s'],
            'geometry_kind':'source','evidence_status':'unresolved',
            'anatomy':{'artery':'ACA','side':'L','segment':'A2','branch_id':'e'},
            'centerline_mm':[[0,0,0],[20,0,0]],'radii_mm':[2,2]}]}
    kwargs = dict(edge_id='e',lesion_id='l1',case_id='derived',region='aca',center_mm=10,
                  length_mm=8,severity_percent=75,measurement_method='local_baseline_area',
                  sample_spacing_mm=1,seed=42)
    return case, kwargs


def test_area_vs_diameter_and_immutable_source():
    case, kwargs = inputs()
    before = deepcopy(case)
    area = concentric_stenosis(case, **kwargs)
    assert min(area['edges'][0]['radii_mm']) == pytest.approx(1)
    assert area['lesions'][0]['profile_center_percent'] == pytest.approx(75)
    kwargs['measurement_method'] = 'local_baseline_diameter'
    diameter = concentric_stenosis(case, **kwargs)
    assert min(diameter['edges'][0]['radii_mm']) == pytest.approx(.5)
    assert case == before
    assert area['nodes'] == case['nodes']
    assert area['base_model_id'] == case['base_model_id']
    assert area['edges'][0]['evidence_status'] == 'synthetic_estimate'


def test_support_endpoints_and_determinism():
    case, kwargs = inputs()
    one = concentric_stenosis(case, **kwargs)
    assert one == concentric_stenosis(case, **kwargs)
    e = one['edges'][0]
    for p, r in zip(e['centerline_mm'], e['radii_mm']):
        if p[0] <= 6 or p[0] >= 14:
            assert r == 2


@pytest.mark.parametrize('key,value', [('center_mm',2),('length_mm',0),('severity_percent',100),
    ('severity_percent',float('nan')),('sample_spacing_mm',0),('seed',True),
    ('measurement_method','NASCET_diameter'),('case_id','base'),('region','unknown')])
def test_invalid_operation_preserves_input(key,value):
    case, kwargs = inputs()
    before = deepcopy(case)
    kwargs[key] = value
    with pytest.raises(ValueError):
        concentric_stenosis(case, **kwargs)
    assert case == before


def test_second_lesion_requires_spatial_clearance():
    case, kwargs = inputs()
    derived = concentric_stenosis(case, **kwargs)
    kwargs['case_id'] = 'second'
    kwargs['lesion_id'] = 'l2'
    with pytest.raises(ValueError, match='clearance'):
        concentric_stenosis(derived, **kwargs)


def test_multiple_separated_lesions_preserve_existing_profile():
    case, kwargs = inputs()
    kwargs.update(center_mm=4,length_mm=2,min_spacing_mm=1)
    first = concentric_stenosis(case, **kwargs)
    kwargs.update(center_mm=16,case_id='second',lesion_id='l2')
    second = concentric_stenosis(first, **kwargs)
    assert len(second['lesions']) == 2
    assert second['edges'][0]['lesion_ids'] == ['l1','l2']
    original = dict(zip(map(tuple,first['edges'][0]['centerline_mm']),first['edges'][0]['radii_mm']))
    for p,r in zip(second['edges'][0]['centerline_mm'],second['edges'][0]['radii_mm']):
        if p[0] <= 5:
            assert r == original[tuple(p)]
    assert second['lesions'][1]['spacing_checks'][0]['clearance_lower_bound_mm'] == pytest.approx(6)


def test_different_edge_lesions_checked_in_3d():
    case, kwargs = inputs()
    for n,p in [('c',[0,1,0]),('d',[20,1,0])]:
        case['nodes'][n] = {'kind':'unresolved','evidence_status':'unresolved','position_mm':p}
    other = deepcopy(case['edges'][0])
    other.update(id='other',start='c',end='d',centerline_mm=[[0,1,0],[20,1,0]])
    case['edges'].append(other)
    first = concentric_stenosis(case, **kwargs)
    before = deepcopy(first)
    kwargs.update(edge_id='other',case_id='second',lesion_id='l2')
    with pytest.raises(ValueError,match='clearance'):
        concentric_stenosis(first, **kwargs)
    assert first == before


def test_prior_minimum_spacing_cannot_be_reduced():
    case, kwargs = inputs()
    kwargs.update(center_mm=4,length_mm=2,min_spacing_mm=8)
    first = concentric_stenosis(case, **kwargs)
    kwargs.update(center_mm=16,case_id='second',lesion_id='l2',min_spacing_mm=0)
    with pytest.raises(ValueError,match='spacing'):
        concentric_stenosis(first, **kwargs)


def test_cli_saved_derivative_roundtrip(tmp_path):
    import json
    from vv_toolbox.case_cli import main
    from vv_toolbox.case_io import load_case, save_case
    case, kwargs = inputs()
    source, settings, output = (tmp_path / n for n in ('source.json', 'settings.json', 'derived.json'))
    save_case(source, case)
    before = source.read_bytes()
    settings.write_text(json.dumps(kwargs))
    assert main(['stenosis', str(source), str(settings), str(output)]) == 0
    restored, _ = load_case(output)
    assert restored == concentric_stenosis(case, **kwargs)
    assert source.read_bytes() == before
