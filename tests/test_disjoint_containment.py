import trimesh

from vv_toolbox.disjoint_containment import inspect_disjoint_containment, _SurfaceValidationCache


def test_nested_solids_detected_without_surface_intersection():
    big = trimesh.creation.box(extents=[4, 4, 4])
    small = trimesh.creation.box()
    result = inspect_disjoint_containment(big, small)
    assert result['complete'] and result['status'] == 'CONTAINMENT_DETECTED'
    assert len(result['contained_components']) == 1
    assert result['contained_components'][0]['direction'] == 1


def test_all_disconnected_components_checked():
    outside = trimesh.creation.box()
    outside.apply_translation([10, 0, 0])
    combined = trimesh.util.concatenate([outside, trimesh.creation.box()])
    result = inspect_disjoint_containment(combined, trimesh.creation.box(extents=[4, 4, 4]))
    assert result['status'] == 'CONTAINMENT_DETECTED'
    assert result['contained_components'][0]['direction'] == 0


def test_separated_solids_have_no_containment():
    a, b = trimesh.creation.box(), trimesh.creation.box()
    b.apply_translation([5, 0, 0])
    assert inspect_disjoint_containment(a, b)['status'] == 'NO_CONTAINMENT_DETECTED'


def test_surface_intersection_is_not_reported_as_disjoint_clearance():
    a, b = trimesh.creation.box(), trimesh.creation.box()
    b.apply_translation([.5, 0, 0])
    result = inspect_disjoint_containment(a, b)
    assert result['status'] == 'UNKNOWN' and not result['complete']


def test_open_surface_rejected():
    a = trimesh.creation.box()
    a.update_faces(list(range(len(a.faces) - 1)))
    assert inspect_disjoint_containment(a, trimesh.creation.box())['status'] == 'UNKNOWN'


def test_invalid_second_surface_has_bound_diagnostic_and_cache_consistency():
    first, second = trimesh.creation.box(), trimesh.creation.box()
    second.update_faces(list(range(len(second.faces)-1)))
    cache = _SurfaceValidationCache()
    report = inspect_disjoint_containment(first, second, _validation_cache=cache)
    assert report['invalid_surface_index'] == 1
    assert report['invalid_surface_validation']['self_contact'] == 'NOT RUN'
    assert len(report['invalid_surface_validation']['geometry_sha256']) == 64
    assert not report['invalid_surface_validation']['topology']['usable_for_sampled_containment']
    assert inspect_disjoint_containment(first, second, _validation_cache=cache) == report


def test_reuse_matches_uncached_result_and_geometry_changes_invalidate():
    big = trimesh.creation.box(extents=[4, 4, 4])
    small = trimesh.creation.box()
    cache = _SurfaceValidationCache()
    expected = inspect_disjoint_containment(big, small)
    assert inspect_disjoint_containment(big, small, _validation_cache=cache) == expected
    assert cache.misses == 2 and cache.hits == 0
    assert inspect_disjoint_containment(big.copy(), small.copy(), _validation_cache=cache) == expected
    assert cache.misses == 2 and cache.hits == 2
    small.apply_translation([10, 0, 0])
    assert inspect_disjoint_containment(big, small, _validation_cache=cache)['status'] == 'NO_CONTAINMENT_DETECTED'
    assert cache.misses == 3
    small.update_faces(list(range(len(small.faces) - 1)))
    assert inspect_disjoint_containment(big, small, _validation_cache=cache)['status'] == 'UNKNOWN'
    assert cache.misses == 4


def test_frequently_used_surface_survives_bounded_neighbor_rotation(monkeypatch):
    import vv_toolbox.disjoint_containment as module
    monkeypatch.setattr(module, 'inspect_self_contact', lambda *args, **kwargs:
        dict(status='NO_CONTACT_DETECTED', coverage='test stub', checked_pairs=0, contact_pairs=[]))
    cache = _SurfaceValidationCache()
    common = trimesh.creation.box()
    for index in range(40):
        cache.validate(common)
        neighbor = common.copy()
        neighbor.apply_translation([index+1, 0, 0])
        cache.validate(neighbor)
    assert cache.misses == 41
    assert len(cache.entries) == 32
    cache.validate(common)
    assert cache.misses == 41 and cache.hits == 40
