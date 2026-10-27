import numpy as np
import pytest
from vv_toolbox.section_radius_correction import correct_radially


def test_radius_correction_changes_radius_preserves_axis_and_fixed_vertices():
    points = np.array([[1.,0,0],[2.,0,0],[0.,0,0],[1.,0,1]])
    result = correct_radially(points, [[0,0,-2],[0,0,2]], [1.3,1.3], [1,0,1,1])
    np.testing.assert_allclose(result, [[1.3,0,0],[2,0,0],[0,0,0],[1.3,0,1]], atol=1e-15)
    np.testing.assert_array_equal(result[1:3], points[1:3])


@pytest.mark.parametrize('gains,weights', [([0,1],[1]),([1,1],[1.1]),([1,float('nan')],[1])])
def test_invalid_correction_rejected(gains, weights):
    with pytest.raises(ValueError):
        correct_radially([[1,0,0]], [[0,0,-1],[0,0,1]], gains, weights)
