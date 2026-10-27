from copy import deepcopy
import json
import numpy as np
import pytest

from test_case_surface import example
from vv_toolbox.bifurcation_saccular import bifurcation_saccular_spec,validate_bifurcation_saccular_spec
from vv_toolbox.case_io import save_case
from vv_toolbox.case_cli import main


def fixture():
    case=example();case['nodes']['a']['kind']='junction'
    for ident,point in [('c',[0,20,0]),('d',[0,0,20])]:
        case['nodes'][ident]=dict(kind='unresolved',evidence_status='unresolved',position_mm=point)
        edge=deepcopy(case['edges'][0]);edge.update(id=ident,end=ident,centerline_mm=[[0,0,0],point])
        case['edges'].append(edge)
    params=dict(lesion_id='branch-sac',junction_id='a',region='mca',outlet_distances_mm={'e':5,'c':6,'d':7},
        neck_center_mm=[1,1,1],outward_normal=[0,0,1],width_direction=[1,0,0],
        neck_width_mm=2,neck_depth_mm=1,height_perpendicular_mm=5,dome_width_mm=4,dome_depth_mm=3,blending_extent_mm=.5)
    return case,params


def test_spec_preserves_all_branches_and_is_not_generated_geometry():
    case,params=fixture();before=deepcopy(case)
    spec=bifurcation_saccular_spec(case,**params)
    assert case==before and spec['accepted_for_generation'] is False
    assert spec['geometry_status']=='NOT GENERATED' and set(spec['checks'].values())=={'NOT RUN'}
    assert {b['edge_id'] for b in spec['branch_constraints']}=={'c','d','e'}
    expected={'c':[0,6,0],'d':[0,0,7],'e':[5,0,0]}
    for branch in spec['branch_constraints']:
        assert branch['outlet_center_mm']==expected[branch['edge_id']]
        assert branch['outlet_radius_mm']==2 and branch['must_preserve_patent_path']
    assert validate_bifurcation_saccular_spec(case,spec)==spec


def test_reversed_edge_parameterization_preserves_physical_outlet():
    case,params=fixture();first=bifurcation_saccular_spec(case,**params)
    edge=case['edges'][0];edge['start'],edge['end']=edge['end'],edge['start']
    edge['centerline_mm'].reverse();edge['radii_mm'].reverse()
    second=bifurcation_saccular_spec(case,**params)
    a=next(b for b in first['branch_constraints'] if b['edge_id']=='e')
    b=next(b for b in second['branch_constraints'] if b['edge_id']=='e')
    assert a['outlet_center_mm']==b['outlet_center_mm'] and a['outlet_tangent_away']==b['outlet_tangent_away']
    assert b['junction_at_edge_end']


def test_rigid_coordinate_change_preserves_neck_and_outlet_relationships():
    case,p=fixture();first=bifurcation_saccular_spec(case,**p)
    rotation=np.array([[0,-1,0],[1,0,0],[0,0,1]]);shift=np.array([3,-7,11])
    transform=lambda value:(np.asarray(value)@rotation.T+shift).tolist()
    for node in case['nodes'].values():node['position_mm']=transform(node['position_mm'])
    for edge in case['edges']:edge['centerline_mm']=transform(edge['centerline_mm'])
    p['neck_center_mm']=transform(p['neck_center_mm'])
    for key in ('outward_normal','width_direction'):p[key]=(rotation@p[key]).tolist()
    second=bifurcation_saccular_spec(case,**p)
    assert np.allclose(second['neck']['curve_mm'],transform(first['neck']['curve_mm']))
    for a,b in zip(first['branch_constraints'],second['branch_constraints']):
        assert np.allclose(b['outlet_center_mm'],transform(a['outlet_center_mm']))
        assert np.allclose(b['outlet_tangent_away'],rotation@a['outlet_tangent_away'])
        assert b['outlet_radius_mm']==a['outlet_radius_mm']


@pytest.mark.parametrize('damage',['missing_branch','extra_branch','outside','zero','nonunit','small_dome'])
def test_rejects_ambiguous_or_incomplete_inputs(damage):
    case,p=fixture()
    if damage=='missing_branch':p['outlet_distances_mm'].pop('d')
    if damage=='extra_branch':p['outlet_distances_mm']['other']=3
    if damage=='outside':p['outlet_distances_mm']['e']=21
    if damage=='zero':p['outlet_distances_mm']['e']=0
    if damage=='nonunit':p['outward_normal']=[0,0,2]
    if damage=='small_dome':p['dome_width_mm']=1
    with pytest.raises(ValueError):bifurcation_saccular_spec(case,**p)


def test_rejects_changed_case_and_tampered_outlet():
    case,p=fixture();spec=bifurcation_saccular_spec(case,**p)
    modified=deepcopy(spec);modified['branch_constraints'][0]['outlet_radius_mm']=3
    with pytest.raises(ValueError):validate_bifurcation_saccular_spec(case,modified)
    case['case_id']='changed'
    with pytest.raises(ValueError):validate_bifurcation_saccular_spec(case,spec)


def test_cli_generates_same_spec_without_changing_input(tmp_path,capsys):
    case,p=fixture();path=tmp_path/'case.json';save_case(path,case);before=path.read_bytes()
    params=tmp_path/'parameters.json';params.write_text(json.dumps(p))
    assert main(['bifurcation-saccular-spec',str(path),str(params)])==0
    assert json.loads(capsys.readouterr().out)==bifurcation_saccular_spec(case,**p)
    assert path.read_bytes()==before
