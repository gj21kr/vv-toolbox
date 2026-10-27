import numpy as np
import pytest
from vv_toolbox.triangle_contact import triangle_contacts


@pytest.mark.parametrize('other,expected', [
    ([[.2, .2, -1], [.2, .2, 1], [.7, .2, 0]], True),
    ([[2, 0, 0], [3, 0, 0], [2, 1, 0]], False),
    ([[.1, .1, 0], [.4, .1, 0], [.1, .4, 0]], True),
    ([[0, 0, 1], [1, 0, 1], [0, 1, 1]], False),
    ([[1, 0, 0], [2, 0, 0], [1, 1, 0]], True),
])
def test_contacts_and_rigid_transform(other, expected):
    a = np.array([[[0., 0., 0.], [1., 0., 0.], [0., 1., 0.]]])
    b = np.array([other], dtype=float)
    assert bool(triangle_contacts(a, b)[0]) == expected
    rotation = np.array([[0., -1., 0.], [1., 0., 0.], [0., 0., 1.]])
    assert bool(triangle_contacts(a@rotation+1500, b@rotation+1500)[0]) == expected


def test_degenerate_input_is_not_declared_clear():
    with pytest.raises(ValueError, match='degenerate'):
        triangle_contacts(np.zeros((1, 3, 3)), np.zeros((1, 3, 3)))
