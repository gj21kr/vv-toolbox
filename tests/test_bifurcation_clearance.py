from copy import deepcopy
import numpy as np
import pytest
from test_bifurcation_surface import design
from vv_toolbox.bifurcation_saccular import bifurcation_saccular_spec
from vv_toolbox.bifurcation_clearance import _segment_box_distance,inspect_bifurcation_clearance
from vv_toolbox.bifurcation_surface import build_bifurcation_candidate


def neighbor(case,points):
    edge=deepcopy(case['edges'][0]);edge.update(id='neighbor',start='x',end='y',
        centerline_mm=points,radii_mm=[.5,.5] if points is not None else None)
    for index,key in enumerate(('x','y')):
        case['nodes'][key]=dict(kind='unresolved',evidence_status='unresolved',
                                position_mm=points[index] if points is not None else None)
    case['edges'].append(edge)


@pytest.mark.parametrize('a,b,expected',[
    ([-5,0,0],[5,0,0],0),([3,0,0],[3,0,0],2),
    ([-5,3,0],[5,3,0],2),([2,2,2],[3,3,3],np.sqrt(3))])
def test_entire_segment_box_distance(a,b,expected):
    assert _segment_box_distance(a,b,[-1]*3,[1]*3)==pytest.approx(expected)
    assert _segment_box_distance(b,a,[-1]*3,[1]*3)==pytest.approx(expected)


@pytest.mark.parametrize('kind',['far','crossing','missing'])
def test_all_context_paths_are_checked_and_unknown_prevents_generation(kind):
    case,spec=design();p=spec['parameters']
    if kind=='far':points=[[100,100,100],[100,110,100]]
    elif kind=='missing':points=None
    else:
        center=np.asarray(p['neck_center_mm'])+np.asarray(p['outward_normal'])*2
        width=np.asarray(p['width_direction'])
        points=[(center-20*width).tolist(),(center+20*width).tolist()]
    neighbor(case,points);spec=bifurcation_saccular_spec(case,**p);before=deepcopy(case)
    report=inspect_bifurcation_clearance(case,spec,margin_mm=.32)
    assert report['checked_edge_count']==1 and case==before
    assert report['status']==('PASS' if kind=='far' else 'UNKNOWN')
    if kind!='far':
        with pytest.raises(ValueError,match='clearance unresolved'):
            build_bifurcation_candidate(case,spec,spacing_mm=.16)
    else:
        _,_,meta=build_bifurcation_candidate(case,spec,spacing_mm=.16)
        assert meta['checks']['nonincident_clearance']=='PASS'
        assert not meta['accepted_for_generation']


def test_absent_context_is_not_reported_as_inspected():
    case,spec=design()
    assert inspect_bifurcation_clearance(case,spec,margin_mm=.32)['status']=='NOT RUN'
