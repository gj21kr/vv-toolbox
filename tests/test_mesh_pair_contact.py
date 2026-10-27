import numpy as np
from vv_toolbox.mesh_pair_contact import inspect_pair_contact


def test_touching_crossing_and_separated():
    a=np.array([[[0.,0,0],[2,0,0],[0,2,0]]])
    b=np.array([[[.5,.5,-1],[.5,.5,1],[1.5,.5,0]]])
    assert inspect_pair_contact(a,b)['status']=='CONTACT_DETECTED'
    assert inspect_pair_contact(a,a)['contact_pairs']==[[0,0]]
    r=inspect_pair_contact(a,b+10)
    assert r['status']=='NO_SURFACE_CONTACT_DETECTED'
    assert r['containment']=='NOT RUN'


def test_unfinished_and_degenerate_candidates_are_unknown():
    a=np.array([[[0.,0,0],[2,0,0],[0,2,0]]])
    assert inspect_pair_contact(a,np.repeat(a,2,axis=0),max_pairs=1)['status']=='UNKNOWN'
    b=np.array([[[0.,0,0],[1,0,0],[2,0,0]]])
    assert inspect_pair_contact(a,b)['status']=='UNKNOWN'


def test_distant_faces_keep_original_contact_indices_and_budget():
    crossing=np.array([[.5,.5,-1],[.5,.5,1],[1.5,.5,0]])
    triangle=np.array([[0.,0,0],[2,0,0],[0,2,0]])
    first=np.stack([triangle+100,triangle,triangle-100])
    result=inspect_pair_contact(first,crossing[None])
    assert result['contact_pairs']==[[1,0]] and result['checked_pairs']==1
    limited=inspect_pair_contact(first,np.stack([crossing,crossing]),max_pairs=1)
    assert limited['status']=='UNKNOWN' and limited['checked_pairs']==0


def test_pair_candidates_match_exhaustive_triangle_test():
    from vv_toolbox.triangle_contact import triangle_contacts
    rng=np.random.default_rng(721)
    a=rng.normal(size=(30,3,3))
    b=rng.normal(size=(20,3,3)) + [2,0,0]
    a[::3]+=100
    expected=[]
    for i,first in enumerate(a):
        for j,second in enumerate(b):
            if (np.all(first.min(0)<=second.max(0)+1e-8)
                    and np.all(second.min(0)<=first.max(0)+1e-8)
                    and triangle_contacts(first[None],second[None],1e-8)[0]):
                expected.append([i,j])
    result=inspect_pair_contact(a,b)
    assert sorted(result['contact_pairs'])==expected
    assert result['complete']
