from copy import deepcopy

import pytest

from vv_toolbox.section_target_check import check_section_targets


def section(index=1, area=4.):
    return dict(index=index, area_mm2=area, status='MEASURED',
                origin_mm=[0, 0, index], normal=[0, 0, 1])


def check(a, b, c, tolerance=.01):
    return check_section_targets(a, b, c, absolute_scale_tolerance=tolerance)


def test_area_radius_not_area_ratio_and_source_unchanged():
    original = [section()]
    before = deepcopy(original)
    report = check(original, [section(area=1)], [section(area=1)], 0)
    assert report['status'] == 'PASS' and report['complete']
    assert report['rows'][0]['measured_scale'] == .5
    assert original == before


def test_insufficient_change_fails_even_with_matching_coverage():
    report = check([section()], [section(area=2.56)], [section(area=3.8)])
    assert report['status'] == 'FAIL'


@pytest.mark.parametrize('measured', [[], [section(2)], [section(), section()]])
def test_incomplete_or_ambiguous_coverage_is_unknown(measured):
    result = check([section()], [section()], measured)
    assert result['status'] == 'UNKNOWN' and not result['complete']


@pytest.mark.parametrize('field,value', [
    ('status', 'UNKNOWN'), ('area_mm2', float('nan')), ('area_mm2', 0),
    ('origin_mm', [0, 0, 2]), ('normal', [1, 0, 0]), ('normal', [0, 0, 0])])
def test_unusable_measurement_never_passes(field, value):
    actual = section()
    actual[field] = value
    assert check([section()], [section()], [actual])['status'] == 'UNKNOWN'


@pytest.mark.parametrize('tolerance', [-1, True, float('inf')])
def test_tolerance_must_be_explicit_finite_nonnegative(tolerance):
    with pytest.raises(ValueError):
        check([section()], [section()], [section()], tolerance)


def test_order_independent_but_all_stations_checked():
    source = [section(1), section(2)]
    measured = [section(2, 1), section(1)]
    result = check(source, source, measured)
    assert result['status'] == 'FAIL' and len(result['rows']) == 2
