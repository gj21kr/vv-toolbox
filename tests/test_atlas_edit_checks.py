from copy import deepcopy
import numpy as np
import pytest
from vv_toolbox.atlas_edit_checks import inspect_edit
from vv_toolbox.atlas_edit_checks import require_self_contact_clearance, AtlasEditCheckFailure


def fixture():
    part=dict(vertices=np.array([[0.,0,0],[1,0,0],[0,1,0],[2,0,0]]),
              faces=np.array([[0,1,2],[0,1,3]]))
    edges=[dict(id='e',start='a',end='b',points=[[0,0,0],[1,0,0],[2,0,0]],radii=[1,1,1])]
    return part,edges


def test_inherited_defect_is_counted_without_claiming_valid_surface():
    part,edges=fixture()
    report=inspect_edit(part,part,edges,edges)
    assert report['basic_invariants']=='PASS'
    assert report['source_degenerate_triangles']==1
    assert report['newly_degenerate_face_ids']==[]
    assert report['self_intersection']=='NOT RUN'
    assert report['junction_smoothness']=='NOT RUN'


def test_new_collapse_is_detected():
    part,edges=fixture()
    edited=deepcopy(part);edited['vertices'][2]=[.5,0,0]
    report=inspect_edit(part,edited,edges,edges)
    assert report['basic_invariants']=='FAIL'
    assert report['newly_degenerate_face_ids']==[0]


@pytest.mark.parametrize('field',['points','radii','end'])
def test_endpoint_change_is_not_accepted(field):
    part,edges=fixture();changed=deepcopy(edges)
    if field=='points':changed[0][field][0][0]=.1
    elif field=='radii':changed[0][field][-1]=.5
    else:changed[0][field]='different'
    assert inspect_edit(part,part,edges,changed)['checks']['endpoint_positions_and_radii']=='FAIL'


def test_nonpositive_interior_radius_is_detected():
    part,edges=fixture();changed=deepcopy(edges);changed[0]['radii'][1]=0
    assert inspect_edit(part,part,edges,changed)['checks']['positive_radii']=='FAIL'


def test_contact_screen_rejects_crossing_and_unknown_but_accepts_separated():
    part=dict(vertices=np.array([[-1.,-1,0],[1,-1,0],[0,1,0],
                                 [0,-.5,-1],[0,-.5,1],[0,.5,0]]),
              faces=np.array([[0,1,2],[3,4,5]]))
    with pytest.raises(AtlasEditCheckFailure,match='FAIL'):
        require_self_contact_clearance(part)
    assert part['edit_checks']['self_intersection']=='FAIL'
    part['vertices'][3:]+=10
    require_self_contact_clearance(part)
    assert part['edit_checks']['self_intersection']=='PASS'
    part['vertices'][2]=part['vertices'][1]
    with pytest.raises(AtlasEditCheckFailure,match='UNKNOWN'):
        require_self_contact_clearance(part)
