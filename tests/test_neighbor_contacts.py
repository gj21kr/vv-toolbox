from copy import deepcopy

import numpy as np
import trimesh

from vv_toolbox.neighbor_contacts import inspect_neighbor_contacts


def box(ident, x=0):
    mesh = trimesh.creation.box()
    mesh.apply_translation([x, 0, 0])
    return dict(id=ident, vertices=mesh.vertices.copy(), faces=mesh.faces.copy())


def test_new_and_removed_contacts_fail():
    source = box('source')
    other = box('other', 2)
    changed = box('source', 1.25)
    for a, b in [(source, changed), (changed, source)]:
        result = inspect_neighbor_contacts(a, b, [other], expected_ids=['other'])
        assert result['status'] == 'FAIL' and result['complete']


def test_unchanged_contacts_and_all_neighbors_checked():
    source = box('source')
    neighbors = [box('near', .75), box('far', 10)]
    result = inspect_neighbor_contacts(source, deepcopy(source), neighbors, expected_ids=['near', 'far'])
    assert result['status'] == 'PASS' and len(result['rows']) == 2
    assert result['containment'] == 'NOT RUN'


def test_incomplete_registry_or_pair_budget_unknown():
    source = box('source')
    assert inspect_neighbor_contacts(source, source, [], expected_ids=['missing'])['status'] == 'UNKNOWN'
    neighbor = box('other', .5)
    result = inspect_neighbor_contacts(source, source, [neighbor], expected_ids=['other'], max_pairs=1)
    assert result['status'] == 'UNKNOWN' and not result['complete']


def test_changed_face_correspondence_rejected():
    source = box('source')
    changed = deepcopy(source)
    changed['faces'] = np.roll(changed['faces'], 1, axis=0)
    assert inspect_neighbor_contacts(source, changed, [], expected_ids=[])['status'] == 'UNKNOWN'


def test_new_complete_enclosure_cannot_pass_surface_only_check():
    source = box('source', 5)
    changed = box('source')
    neighbor = box('other')
    neighbor['vertices'] *= 4
    result = inspect_neighbor_contacts(source, changed, [neighbor], expected_ids=['other'])
    assert result['status'] == 'FAIL'
    row = result['rows'][0]
    assert row['gained'] == row['lost'] == []
    assert row['disjoint_containment']['status'] == 'FAIL'
