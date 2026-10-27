import numpy as np
import pytest

from vv_toolbox.tangent_patch import hermite_rings


def circle():
    angle = np.arange(24)*2*np.pi/24
    return np.column_stack((np.cos(angle), np.sin(angle), np.zeros(24)))


def test_linear_cylinder_and_translation():
    a = circle()
    d = np.tile([0., 0., 2.], (len(a), 1))
    u = np.linspace(0, 1, 9)
    rings, derivative = hermite_rings(a, a+d, d, d, u)
    np.testing.assert_allclose(rings, a+u[:, None, None]*d, atol=1e-14)
    np.testing.assert_allclose(derivative, np.broadcast_to(d, rings.shape))
    shift = np.array([100., -200., 1500.])
    shifted, _ = hermite_rings(a+shift, a+d+shift, d, d, u)
    np.testing.assert_allclose(shifted-shift, rings, atol=3e-13)


def test_shared_neck_derivative_and_exact_rim():
    neck = circle()
    q = np.tile([0., 0., 1.], (len(neck), 1))
    outer = np.column_stack((neck[:, :2]*1.7, np.full(len(neck), -2.)))
    upper = np.column_stack((neck[:, :2]*1.3, np.full(len(neck), 2.)))
    left, dl = hermite_rings(outer, neck, 2*q, q, [0, .25, .5, .75, 1])
    right, dr = hermite_rings(neck, upper, q, 2*q, [0, .25, .5, .75, 1])
    assert np.array_equal(left[-1], neck)
    assert np.array_equal(right[0], neck)
    assert np.array_equal(dl[-1], dr[0])


@pytest.mark.parametrize("stations", [[0, .5, .5, 1], [.1, 1], [0, np.nan, 1]])
def test_invalid_stations(stations):
    a = circle()
    d = np.ones_like(a)
    with pytest.raises(ValueError):
        hermite_rings(a, a+d, d, d, stations)


def test_zero_derivative_rejected():
    a = circle()
    with pytest.raises(ValueError):
        hermite_rings(a, a+1, np.zeros_like(a), np.ones_like(a), [0, 1])
