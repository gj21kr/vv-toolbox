from copy import deepcopy
import numpy as np
import pytest

from test_bifurcation_saccular import fixture
from vv_toolbox.bifurcation_saccular import bifurcation_saccular_spec
from vv_toolbox.bifurcation_attachment import inspect_bifurcation_attachment


def inspect(case, p):
    return inspect_bifurcation_attachment(case, bifurcation_saccular_spec(case, **p), burial_margin_mm=.1)


def test_detects_buried_neck_without_modifying_case():
    case,p=fixture(); before=deepcopy(case)
    result=inspect(case,p)
    assert result['status']=='FAIL' and result['rim']['interior_indices']
    assert case==before and not result['accepted_for_generation']
    assert set(result['checks'].values())=={'NOT RUN'}


def test_disconnected_sac_reports_unburied_extension():
    case,p=fixture();p['neck_center_mm']=[100,100,100]
    result=inspect(case,p)
    assert result['status']=='FAIL'
    assert len(result['buried_rim']['insufficient_burial_indices'])==64
    assert all(o['status']=='PASS' for o in result['outlets'])


def test_clear_synthetic_attachment_passes_only_sampled_conditions():
    case,p=fixture()
    normal=-np.ones(3)/np.sqrt(3)
    p.update(neck_center_mm=(2*normal).tolist(), outward_normal=normal.tolist(),
             width_direction=(np.array([1,-1,0])/np.sqrt(2)).tolist())
    result=inspect(case,p)
    assert result['status']=='PASS'
    assert not result['rim']['interior_indices']
    assert not result['buried_rim']['insufficient_burial_indices']
    assert not result['accepted_for_generation']
    assert result['checks']['branch_patency']=='NOT RUN'


def test_outlet_overlap_is_unknown_not_claimed_collision():
    case,p=fixture();p['outlet_distances_mm']={key:1 for key in p['outlet_distances_mm']}
    result=inspect(case,p)
    assert all(o['status']=='UNKNOWN' for o in result['outlets'])


def test_rigid_transform_preserves_attachment_results():
    case,p=fixture();first=inspect(case,p)
    rotation=np.array([[0,-1,0],[1,0,0],[0,0,1]]);shift=np.array([9,-3,7])
    transform=lambda v:(np.asarray(v)@rotation.T+shift).tolist()
    for node in case['nodes'].values():node['position_mm']=transform(node['position_mm'])
    for edge in case['edges']:edge['centerline_mm']=transform(edge['centerline_mm'])
    p['neck_center_mm']=transform(p['neck_center_mm'])
    for key in ('outward_normal','width_direction'):p[key]=(rotation@p[key]).tolist()
    second=inspect(case,p)
    assert first['status']==second['status']
    assert first['rim']['interior_indices']==second['rim']['interior_indices']
    assert np.allclose(first['rim']['field_values_mm'],second['rim']['field_values_mm'])
    assert np.allclose([o['clearance_lower_bound_mm'] for o in first['outlets']],
                       [o['clearance_lower_bound_mm'] for o in second['outlets']])


@pytest.mark.parametrize('margin',[0,-1,float('nan'),float('inf'),True])
def test_invalid_burial_margin_rejected(margin):
    case,p=fixture()
    with pytest.raises(ValueError):
        inspect_bifurcation_attachment(case,bifurcation_saccular_spec(case,**p),burial_margin_mm=margin)
