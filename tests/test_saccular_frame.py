from copy import deepcopy
import numpy as np
import pytest
from test_lesions import inputs
from vv_toolbox.saccular_frame import propose_saccular_frame
from vv_toolbox.saccular import saccular_spec
from test_saccular_spec import parameters


def bent_case():
    case,_=inputs()
    points=[[0,0,0],[5,5,0],[20,5,0]]
    case['edges'][0].update(centerline_mm=points,radii_mm=[2,2,2])
    case['nodes']['b']['position_mm']=points[-1]
    return case


def test_parallel_reference_uses_nearby_transport_and_preserves_source():
    case=bent_case()
    before=deepcopy(case)
    frame=propose_saccular_frame(case,'e',10.,[1,0,0],search_mm=4.)
    assert frame['method']=='nearby segment parallel transport'
    assert frame['seed_interval']==0 and frame['target_interval']==1
    np.testing.assert_allclose(frame['outward_normal'],[0,-1,0],atol=1e-12)
    assert case==before
    p=parameters()
    p.update(station_mm=10.,**{k:frame[k] for k in ('neck_center_mm','outward_normal','width_direction')})
    assert saccular_spec(case,**p)['parent_anchor']['interval_index']==1


def test_no_arbitrary_axis_when_entire_window_parallel():
    case,_=inputs()
    with pytest.raises(ValueError,match='explicit alternative'):
        propose_saccular_frame(case,'e',10.,[1,0,0],search_mm=4.)
    with pytest.raises(ValueError,match='explicit alternative'):
        propose_saccular_frame(bent_case(),'e',10.,[1,0,0],search_mm=1.)


def test_transport_rigid_transform_equivariance():
    case=bent_case()
    original=propose_saccular_frame(case,'e',10.,[1,0,0],search_mm=4.)
    angle=.72
    rotation=np.array([[np.cos(angle),-np.sin(angle),0],[np.sin(angle),np.cos(angle),0],[0,0,1]])
    offset=np.array([12.,-35.,7.])
    for node in case['nodes'].values():
        node['position_mm']=(rotation@node['position_mm']+offset).tolist()
    case['edges'][0]['centerline_mm']=[(rotation@p+offset).tolist() for p in case['edges'][0]['centerline_mm']]
    result=propose_saccular_frame(case,'e',10.,(rotation@np.array([1.,0,0])).tolist(),search_mm=4.)
    np.testing.assert_allclose(result['outward_normal'],rotation@original['outward_normal'],atol=1e-12)
    np.testing.assert_allclose(result['neck_center_mm'],rotation@original['neck_center_mm']+offset,atol=1e-12)


def test_cli_direct_frame(tmp_path,capsys):
    import json
    from vv_toolbox.case_cli import main
    from vv_toolbox.case_io import save_case
    case,_=inputs()
    path=tmp_path/'case.json'
    save_case(path,case)
    before=path.read_bytes()
    assert main(['saccular-frame',str(path),'--edge','e','--station-mm','10',
                 '--reference-direction','0','1','0','--search-mm','4'])==0
    result=json.loads(capsys.readouterr().out)
    assert result['method']=='direct projection'
    assert result['neck_center_mm']==[10,2,0]
    assert path.read_bytes()==before
