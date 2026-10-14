"""Arterial ostial curvature and envelope regressions, not just connectivity."""
import numpy as np
from scipy.spatial import cKDTree
from vv_toolbox.model import Segment,VesselGraph
from vv_toolbox.surface import network_mesh,_aortic_radius_profiles,_brachiocephalic_taper
from vv_toolbox import generate
import pytest


def ostium_graph(split=False):
    nodes={'a':np.array([0.,0.,-30.]),'j':np.zeros(3),'b':np.array([0.,0.,30.]),'branch':np.array([25.,0.,0.])}
    records=[('aortic_arch','a','j',4),('aortic_arch_proximal','j','b',4),('artery','j','branch',2)]
    if split:
        nodes['short']=np.array([0.,0.,-2.])
        records=[('aortic_arch','a','short',4),('aortic_arch_middle','short','j',4)]+records[1:]
    edges=[Segment(name,start,end,np.linspace(nodes[start],nodes[end],64),radius) for name,start,end,radius in records]
    return VesselGraph(nodes,edges,{'radius_scale':1})


def root_dihedral(vertices,faces):
    triangles=vertices[faces].astype(float)
    normal=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0])
    normal/=np.linalg.norm(normal,axis=1)[:,None]
    edges=np.concatenate([faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]]])
    owners=np.tile(np.arange(len(faces)),3)
    key=np.sort(edges,axis=1)
    order=np.lexsort((key[:,1],key[:,0]))
    key,owners=key[order],owners[order]
    shared=np.all(key[:-1]==key[1:],axis=1)
    a,b=owners[:-1][shared],owners[1:][shared]
    centers=vertices[key[:-1][shared]].mean(axis=1)
    root=(centers[:,0]>3)&(centers[:,0]<5.5)&(np.abs(centers[:,1])<.8)&(np.abs(centers[:,2])>1)&(np.abs(centers[:,2])<3)
    assert root.sum()>20
    return np.degrees(np.arccos(np.clip(np.sum(normal[a]*normal[b],axis=1),-1,1)))[root]


def test_ostial_fillet_reduces_root_normal_jump_without_expanding_back_of_arch(monkeypatch):
    graph=ostium_graph()
    smooth,sf=network_mesh(graph)
    monkeypatch.setattr('vv_toolbox.surface._arterial_junctions',lambda graph:{})
    hard,hf=network_mesh(graph)
    new,old=root_dihedral(smooth,sf),root_dihedral(hard,hf)
    assert np.quantile(new,.95)<.8*np.quantile(old,.95)
    assert new.max()<.75*old.max()
    opposite=smooth[(smooth[:,0]<-2)&(np.abs(smooth[:,2])<1)]
    assert len(opposite)>10
    assert np.max(np.abs(np.linalg.norm(opposite[:,:2],axis=1)-4))<.18


def test_short_trunk_segment_does_not_create_a_blended_radius_bump():
    unsplit,_=network_mesh(ostium_graph())
    split,_=network_mesh(ostium_graph(split=True))
    assert cKDTree(unsplit).query(split)[0].max()<.005
    assert cKDTree(split).query(unsplit)[0].max()<.005


def test_whole_trunk_radius_profile_is_monotone_continuous_and_nonovershooting():
    graph=ostium_graph(split=True)
    radii={'aortic_arch':4,'aortic_arch_middle':3,'aortic_arch_proximal':2,'artery':1}
    graph.segments=[Segment(e.name,e.start,e.end,e.points,radii[e.name]) for e in graph.segments]
    profiles=_aortic_radius_profiles(graph)
    order=['aortic_arch','aortic_arch_middle','aortic_arch_proximal']
    values=np.concatenate([profiles[name] for name in order])
    assert np.all(np.diff(values)<=1e-12)
    assert values.min()>=2 and values.max()<=4
    for first,second in zip(order,order[1:]):
        assert profiles[first][-1]==profiles[second][0]


@pytest.mark.parametrize('variant,local',[
    ('standard',{}),('left_carotid_from_brachiocephalic',{}),
    ('standard',{'right_common_carotid':{'radius_scale':1.5},'right_subclavian':{'radius_scale':.5}}),
])
def test_brachiocephalic_parent_matches_actual_daughter_area_only_at_outlet(variant,local):
    graph=generate(arch_variant=variant,vessel_parameters=local)
    parent=next(edge for edge in graph.segments if edge.name=='brachiocephalic')
    daughters=[edge.radius_mm for edge in graph.segments if edge.start=='brachiocephalic']
    arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(parent.points,axis=0),axis=1))]
    radii=_brachiocephalic_taper(graph,parent,np.full(len(arc),parent.radius_mm),arc)
    assert radii[-1]==pytest.approx(np.linalg.norm(daughters))
    np.testing.assert_array_equal(radii[arc<.4*arc[-1]],parent.radius_mm)
    assert radii.min()>=min(parent.radius_mm,np.linalg.norm(daughters))-1e-10
    assert radii.max()<=max(parent.radius_mm,np.linalg.norm(daughters))+1e-10


def test_brachiocephalic_surface_no_longer_retains_oversized_parent_cap():
    nodes={'arch_right':np.array([-40.,0.,0.]),'brachiocephalic':np.zeros(3),'carotid':np.array([0.,0.,40.]),'subclavian':np.array([40.,0.,10.])}
    records=[('brachiocephalic','arch_right','brachiocephalic',7),('right_common_carotid','brachiocephalic','carotid',3.5),('right_subclavian','brachiocephalic','subclavian',4)]
    graph=VesselGraph(nodes,[Segment(name,a,b,np.linspace(nodes[a],nodes[b],64),radius) for name,a,b,radius in records],{'radius_scale':1})
    vertices,_=network_mesh(graph)
    # Outward y-normal cuts through the former7mm cap while avoiding daughter axes.
    root=vertices[(np.abs(vertices[:,0])<.35)&(np.abs(vertices[:,2])<.35)]
    assert len(root)>0
    assert np.abs(root[:,1]).max()<5.8
    upstream=vertices[(np.abs(vertices[:,0]+30)<.35)]
    assert len(upstream)>4
    assert np.max(np.abs(np.linalg.norm(upstream[:,1:],axis=1)-7))<.2
