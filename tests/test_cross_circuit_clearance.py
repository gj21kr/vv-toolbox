import json
import numpy as np
import pytest

from vv_toolbox.clearance import cross_circuit_clearance, _clearance
from vv_toolbox.model import Segment, VesselGraph, generate
from vv_toolbox.veins import generate_veins


def graph(points,radius,profile=None):
    points=np.array(points,dtype=float)
    edge=Segment('fixture','a','b',points,radius,profile)
    return VesselGraph({'a':points[0],'b':points[-1]},[edge],{})


@pytest.mark.parametrize('current',[False,True])
def test_authored_circuits_have_three_mm_capsule_clearance(current):
    settings=dict(imv_drainage='superior_mesenteric',transverse_dominance='left',
                  vessel_parameters={'ven_inferior_mesenteric':{'radius_scale':1.05,'tortuosity':.3}}) if current else {}
    veins=generate_veins(**settings)
    arteries=generate(absent_communicators=('left_pcom',) if current else ())
    report=cross_circuit_clearance({'arterial':arteries,**veins.graphs})
    assert report['status']=='CLEAR'
    assert report['potential_collisions']==[]
    assert report['minimum_clearance_mm']>=3
    json.dumps(report,allow_nan=False)


def test_interior_crossing_detected_without_dense_sampling():
    a=graph([[-100,0,0],[100,0,0]],1)
    b=graph([[0,-100,1],[0,100,1]],1)
    result=cross_circuit_clearance({'a':a,'b':b})
    assert result['status']=='OVERLAP'
    assert result['minimum_clearance_mm']==pytest.approx(-1)


def test_profiles_conservatively_replace_nominal_radii():
    a=graph([[0,0,0],[10,0,0]],100,[1,2])
    b=graph([[0,5,0],[10,5,0]],100,[1,1])
    assert _clearance(a.segments[0],b.segments[0])==pytest.approx(2)
    b=graph([[0,5,0],[10,5,0]],.1,[4,4])
    assert cross_circuit_clearance({'a':a,'b':b})['status']=='OVERLAP'


def test_parallel_and_endpoint_minima():
    a=graph([[0,0,0],[1,0,0]],.2)
    b=graph([[2,1,0],[2,2,0]],.3)
    assert _clearance(a.segments[0],b.segments[0])==pytest.approx(np.sqrt(2)-.5)
    c=graph([[0,2,0],[1,2,0]],.3)
    assert _clearance(a.segments[0],c.segments[0])==pytest.approx(1.5)
