import numpy as np
import pytest
import trimesh

from vv_toolbox.radius_context import inspect_radius_context, inspect_static_context


def box(x, extent=1):
    mesh = trimesh.creation.box(extents=[extent]*3)
    mesh.apply_translation([x, 0, 0])
    return mesh


def test_clear_context():
    result = inspect_radius_context(box(0), box(.1), {'other':box(4)})
    assert result['status']=='PASS' and not result['remaining_contacts']


def test_new_surface_contact_rejected():
    result = inspect_radius_context(box(0), box(2.4), {'other':box(3)})
    assert result['status']=='FAIL' and result['new_or_extended_contacts']==['other']


def test_fully_contained_edit_detected_without_surface_intersection():
    result = inspect_radius_context(box(5), box(0), {'outer':box(0, 3)})
    assert result['status']=='FAIL'
    assert result['rows'][0]['after']['status']=='CONTAINMENT'


def test_existing_contact_not_called_clear():
    result = inspect_radius_context(box(0), box(0), {'other':box(.4)})
    assert result['status']=='UNKNOWN'
    assert result['decision_reason']=='EXISTING_CONTACT_REQUIRES_JUNCTION_REVIEW'


def test_open_enclosing_context_stays_unknown():
    other = box(0, 3)
    other.update_faces(np.arange(len(other.faces)-1))
    result = inspect_radius_context(box(0), box(0), {'open':other})
    assert result['status']=='UNKNOWN' and result['unknown']==['open']


def test_topology_change_and_empty_context_rejected():
    with pytest.raises(ValueError, match='context'):
        inspect_radius_context(box(0), box(0), {})
    after = box(0)
    after.faces = after.faces[::-1]
    with pytest.raises(ValueError, match='topology'):
        inspect_radius_context(box(0), after, {'other':box(5)})


def test_static_context_matches_both_contact_and_containment():
    neighbors={'contact':box(.4),'enclosing':box(0,3),'far':box(10)}
    result=inspect_static_context(box(0),neighbors)
    assert result['status']=='UNKNOWN'
    assert result['remaining_contacts']==['contact','enclosing']
    assert [row['status'] for row in result['rows']]==['SURFACE_CONTACT','CONTAINMENT','SEPARATED']
