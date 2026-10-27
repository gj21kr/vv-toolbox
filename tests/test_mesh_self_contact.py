import numpy as np
from vv_toolbox.mesh_self_contact import inspect_self_contact


def test_crossing_disconnected_triangles():
    v=np.array([[0,0,0],[2,0,0],[0,2,0],[.5,.5,-1],[.5,.5,1],[1.5,.5,0.]])
    r=inspect_self_contact(v,[[0,1,2],[3,4,5]])
    assert r['status']=='CONTACT_DETECTED' and r['contact_pairs']==[[0,1]]


def test_shared_edge_is_allowed_but_duplicate_face_is_not():
    v=np.array([[0,0,0],[1,0,0],[0,1,0],[1,1,0.]])
    assert inspect_self_contact(v,[[0,1,2],[1,3,2]])['status']=='NO_CONTACT_DETECTED'
    assert inspect_self_contact(v,[[0,1,2],[2,1,0]])['status']=='CONTACT_DETECTED'


def test_exhausted_budget_never_means_clear():
    v=np.array([[0,0,0],[1,0,0],[0,1,0.]])
    r=inspect_self_contact(v,[[0,1,2]]*3,max_pairs=1)
    assert r['status']=='UNKNOWN' and r['coverage']=='pair budget exhausted'


def test_degenerate_input_never_means_clear():
    r=inspect_self_contact([[0,0,0],[1,0,0],[2,0,0]],[[0,1,2]])
    assert r['status']=='UNKNOWN'
    assert r['degenerate_face_ids']==[0]
