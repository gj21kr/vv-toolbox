import numpy as np
import trimesh

from test_union_radius import fixture
from vv_toolbox.disjoint_containment import _SurfaceValidationCache
from vv_toolbox.union_radius import scale_selected_radius
from vv_toolbox.radius_context import inspect_radius_context


def test_geometry_and_context_results_identical_with_request_local_reuse():
    mesh, lineage = fixture()
    parameters = dict(scale=.9, transition_mm=1., max_displacement_mm=.2)
    points = [[0, 0, 0], [0, 0, 4]]
    plain, audit = scale_selected_radius(mesh, lineage, 'middle', points, **parameters)
    cache = _SurfaceValidationCache()
    reused, reused_audit = scale_selected_radius(mesh, lineage, 'middle', points,
                                                _validation_cache=cache, **parameters)
    assert np.array_equal(plain.vertices, reused.vertices)
    assert np.array_equal(plain.faces, reused.faces)
    assert audit == reused_audit
    assert cache.misses == 1
    neighbor = trimesh.creation.box(extents=[.2, .2, .2])
    neighbor.apply_translation([0, 0, 2])
    expected = inspect_radius_context(mesh, plain, {'inside': neighbor})
    actual = inspect_radius_context(mesh, reused, {'inside': neighbor}, _validation_cache=cache)
    assert actual == expected
    assert cache.misses == 3 and cache.hits >= 2


def test_cached_check_is_detached_and_geometry_changes_recheck():
    mesh, _ = fixture()
    cache = _SurfaceValidationCache()
    result = cache.self_contact_check(mesh)
    result['status'] = 'tampered'
    assert cache.self_contact_check(mesh)['status'] == 'NO_CONTACT_DETECTED'
    assert cache.misses == 1
    changed = mesh.copy()
    changed.apply_translation([2, 0, 0])
    assert cache.self_contact_check(changed)['status'] == 'NO_CONTACT_DETECTED'
    assert cache.misses == 2
