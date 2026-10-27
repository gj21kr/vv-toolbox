from copy import deepcopy

import numpy as np
import pytest
import trimesh

from vv_toolbox.profile_scale import scale_section, scale_profile_interval
from vv_toolbox.source_sections import extract_source_sections
from vv_toolbox.profile_loft import loft_source_profiles


def profile():
    return extract_source_sections(
        trimesh.creation.box(extents=[2, 4, 8]),
        [[.2, 0, -1], [.2, 0, 0], [.2, 0, 1]])['profiles'][0]


def test_eccentric_rectangle_preserves_outline_and_distinct_radius_meanings():
    source = profile()
    before = deepcopy(source)
    result = scale_section(source, 1.5)
    assert source == before
    assert result['origin_mm'] == source['origin_mm']
    assert result['area_mm2'] == pytest.approx(18)
    assert result['center_boundary_distance_mm'] == pytest.approx(1.2)
    assert result['area_equivalent_radius_mm'] == pytest.approx(np.sqrt(18 / np.pi))
    assert result['centroid_xyz_mm'] == pytest.approx([-.1, 0, 0])
    assert np.asarray(result['contour_uv_mm']) == pytest.approx(
        np.asarray(source['contour_uv_mm']) * 1.5)


def test_inverse_scale_recovers_original_geometry():
    source = profile()
    restored = scale_section(scale_section(source, .75), 1 / .75)
    assert np.asarray(restored['contour_xyz_mm']) == pytest.approx(np.asarray(source['contour_xyz_mm']))
    assert restored['area_mm2'] == pytest.approx(source['area_mm2'])


@pytest.mark.parametrize('factor', [0, -1, True, float('nan'), float('inf')])
def test_invalid_factors_rejected(factor):
    with pytest.raises(ValueError):
        scale_section(profile(), factor)


@pytest.mark.parametrize('field,value', [
    ('status', 'UNKNOWN'), ('normal', [0, 0, 2]),
    ('contour_xyz_mm', [[0, 0, 0]])])
def test_invalid_geometry_rejected(field, value):
    source = profile()
    source[field] = value
    with pytest.raises(ValueError):
        scale_section(source, 1.2)


def profiles():
    return extract_source_sections(
        trimesh.creation.box(extents=[2, 4, 20]),
        [[.2, 0, z] for z in range(-4, 5)])['profiles']


def test_interval_preserves_end_sections_and_uses_physical_distance():
    source = profiles()
    before = deepcopy(source)
    result = scale_profile_interval(source, start_mm=0, end_mm=6, factor=.5,
                                    protected_indices=[1, 7])
    assert source == before
    assert result['profiles'][0] == source[0]
    assert result['profiles'][-1] == source[-1]
    assert result['scales'][3] == pytest.approx(.5)
    assert result['profiles'][3]['area_mm2'] == pytest.approx(2)
    assert result['scales'] == pytest.approx(result['scales'][::-1])


def test_protected_internal_section_rejects_without_changes():
    source = profiles()
    before = deepcopy(source)
    with pytest.raises(ValueError, match='protected'):
        scale_profile_interval(source, start_mm=0, end_mm=6, factor=1.5,
                               protected_indices=[4])
    assert source == before


@pytest.mark.parametrize('start,end', [(-1, 6), (0, 7), (2, 2), (.1, .9)])
def test_invalid_or_unsampled_intervals_rejected(start, end):
    with pytest.raises(ValueError):
        scale_profile_interval(profiles(), start_mm=start, end_mm=end, factor=.5)


def test_identity_interval_is_exact_and_allows_protected_stations():
    source = profiles()
    result = scale_profile_interval(source, start_mm=0, end_mm=6, factor=1,
                                    protected_indices=[4])
    assert result['profiles'] == source


def test_nonuniform_spacing_and_loft_consume_modified_contours():
    source = extract_source_sections(
        trimesh.creation.box(extents=[2, 4, 20]),
        [[.2, 0, z] for z in [-4, -3, -2.9, 0, 2.8, 3, 4]])['profiles']
    result = scale_profile_interval(source, start_mm=0, end_mm=6, factor=.7)
    assert result['arclength_mm'] == pytest.approx([0, .1, 3, 5.8, 6])
    assert result['scales'][1] > .99
    assert result['scales'][2] == pytest.approx(.7)
    original, _ = loft_source_profiles(source)
    modified, _ = loft_source_profiles(result['profiles'])
    assert np.array_equal(original.faces, modified.faces)
    assert np.array_equal(original.vertices[:64], modified.vertices[:64])
    assert np.array_equal(original.vertices[-64:], modified.vertices[-64:])
    assert not np.array_equal(original.vertices[128:192], modified.vertices[128:192])
