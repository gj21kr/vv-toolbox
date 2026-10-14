import numpy as np
import pytest

from vv_toolbox.model import Segment, VesselGraph
from vv_toolbox.surface import network_mesh


def tapered_fixture(name='aortic_arch', minimum=1.):
    z=np.linspace(0,30,61)
    points=np.column_stack([z*0,z*0,z])
    profile=np.linspace(3*minimum,minimum,len(z))
    edge=Segment(name,'a','b',points,12.,profile)
    return VesselGraph({'a':points[0],'b':points[-1]},[edge],{}),profile


def cross_radius(vertices,z,window=.25):
    section=vertices[np.abs(vertices[:,2]-z)<window]
    assert len(section)>5
    return np.median(np.linalg.norm(section[:,:2],axis=1))


def test_explicit_profile_overrides_nominal_aortic_spline_without_mutation():
    graph,profile=tapered_fixture()
    vertices,faces=network_mesh(graph)
    for z in (5,15,25):
        assert cross_radius(vertices,z)==pytest.approx(3-2*z/30,abs=.14)
    np.testing.assert_array_equal(graph.segments[0].radius_profile_mm,profile)
    edges=np.sort(np.concatenate([faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]]]),axis=1)
    assert np.all(np.unique(edges,axis=0,return_counts=True)[1]==2)


def test_resolution_uses_smallest_profile_not_nominal_radius():
    graph,_=tapered_fixture(minimum=.3)
    with pytest.raises(ValueError,match='minimum radius'):
        network_mesh(graph,spacing=.45)
    vertices,_=network_mesh(graph)
    assert cross_radius(vertices,25)==pytest.approx(.4,abs=.10)


def test_explicit_profile_bypasses_named_parent_outlet_taper(monkeypatch):
    import vv_toolbox.surface as surface
    graph,_=tapered_fixture(name='brachiocephalic')
    parent=graph.segments[0]
    nodes={'a':parent.points[0],'brachiocephalic':parent.points[-1]}
    segments=[Segment(parent.name,'a','brachiocephalic',parent.points,12.,parent.radius_profile_mm)]
    for name,x in [('daughter_left',-10.),('daughter_right',10.)]:
        points=np.linspace(parent.points[-1],[x,0,40],21)
        nodes[name]=points[-1]
        segments.append(Segment(name,'brachiocephalic',name,points,1.,np.ones(21)))
    graph=VesselGraph(nodes,segments,{})
    def forbidden(*args):
        raise AssertionError('Explicit measured radii must not be replaced by authored taper')
    monkeypatch.setattr(surface,'_brachiocephalic_taper',forbidden)
    vertices,_=network_mesh(graph)
    assert cross_radius(vertices,20)==pytest.approx(3-40/30,abs=.14)

