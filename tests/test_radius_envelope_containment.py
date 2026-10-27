import numpy as np
import pytest
import trimesh

from vv_toolbox.centerline_containment import (
    inspect_centerline_containment, inspect_radius_envelope_containment)


def test_inside_centerline_can_have_outside_radius_envelope():
    mesh=trimesh.creation.box()
    points=[[-.1,0,0],[.1,0,0]]
    assert inspect_centerline_containment(mesh,points)['status']=='PASS'
    result=inspect_radius_envelope_containment(mesh,points,[.6,.6])
    assert result['status']=='FAIL'
    assert not result['outside_witnesses']
    assert result['radius_exceedance_witnesses'][0]['excess_mm']==pytest.approx(.1)
    assert result['tube_wall_containment']=='NOT RUN'


def test_variable_radii_are_checked_between_stations():
    mesh=trimesh.creation.box()
    # Radius at the first midpoint fits; increasing radius exits near the end.
    result=inspect_radius_envelope_containment(mesh,[[-.1,0,0],[.1,0,0]],[.1,.6])
    assert result['status']=='FAIL'
    assert result['maximum_depth_used']>0
    assert result['radius_exceedance_witnesses']


def test_positive_clearance_and_tangency_are_distinct():
    mesh=trimesh.creation.box()
    before=mesh.vertices.copy()
    points=[[-.3,0,0],[.3,0,0]]
    inside=inspect_radius_envelope_containment(mesh,points,[.1,.15])
    assert inside['status']=='PASS'
    assert inside['minimum_cover_margin_mm']>0
    tangent=inspect_radius_envelope_containment(mesh,points,[.2,.2],max_depth=8)
    assert tangent['status']=='UNKNOWN'
    limited=inspect_radius_envelope_containment(
        mesh,[[-.3,-.3,0],[.3,.3,0]],[.1,.15],max_cells=1)
    assert limited['status']=='UNKNOWN'
    assert np.array_equal(before,mesh.vertices)


@pytest.mark.parametrize('radii',[None,[],[.1],[.1,0],[.1,-1],[.1,float('nan')],[[.1],[.1]]])
def test_invalid_radii_rejected(radii):
    with pytest.raises(ValueError):
        inspect_radius_envelope_containment(trimesh.creation.box(),[[0,0,0],[.1,0,0]],radii)
