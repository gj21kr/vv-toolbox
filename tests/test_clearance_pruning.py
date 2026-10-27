"""Check accelerated interval pruning against unpruned first-witness search."""
import numpy as np
import pytest
from test_geometry_quality import crossing
from vv_toolbox.geometry_quality import segment_distance, screen_nonincident_clearance


@pytest.mark.parametrize('seed',range(12))
def test_first_witness_and_budget_count_match_brute_force(seed):
    rng=np.random.default_rng(seed)
    case=crossing()
    for edge in case['edges']:
        p=rng.normal(size=(9,3))*8
        edge['centerline_mm']=p.tolist();edge['radii_mm']=rng.uniform(.1,2,9).tolist()
        case['nodes'][edge['start']]['position_mm']=p[0].tolist()
        case['nodes'][edge['end']]['position_mm']=p[-1].tolist()
    a,b=case['edges'];p,q=np.array(a['centerline_mm']),np.array(b['centerline_mm'])
    expected=None;count=0
    for i in range(8):
        for j in range(8):
            count+=1
            gap=segment_distance(p[i],p[i+1],q[j],q[j+1])-max(a['radii_mm'][i:i+2])-max(b['radii_mm'][j:j+2])
            if gap<=.7:expected=(i,j,gap);break
        if expected is not None:break
    actual=screen_nonincident_clearance(case,['first','second'],margin_mm=.7)
    assert actual['checked_segment_pairs']==count
    if expected is None:
        assert actual['potential_contacts']==[]
    else:
        witness=actual['potential_contacts'][0]
        assert witness['intervals']==list(expected[:2])
        assert witness['clearance_lower_bound_mm']==pytest.approx(expected[2])
