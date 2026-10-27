import numpy as np
import pytest
from vv_toolbox.projected_annulus import triangulate_annulus
from vv_toolbox.patch_boundary import patch_boundary_loops


@pytest.mark.parametrize("engine,improve", [('delaunay', False), ('earcut', False), ('earcut', True)])
def test_projected_annulus_keeps_two_exact_boundaries(engine, improve):
    if engine == 'earcut':
        pytest.importorskip('mapbox_earcut')
    angles = np.arange(16)*2*np.pi/16
    ring = np.column_stack([np.cos(angles), np.sin(angles), np.zeros(16)])
    vertices = np.vstack([ring, ring*2])
    faces = triangulate_annulus(vertices, np.arange(16), np.arange(16, 32),
                                np.zeros(3), np.eye(3), engine=engine, improve=improve)
    loops = patch_boundary_loops(faces, np.arange(len(faces)))
    assert {frozenset(loop) for loop in loops} == {frozenset(range(16)), frozenset(range(16, 32))}
    assert len(faces) == 32


@pytest.mark.parametrize("engine", ['delaunay', 'earcut'])
def test_crossing_rings_not_accepted_as_annulus(engine):
    if engine == 'earcut':
        pytest.importorskip('mapbox_earcut')
    angles = np.arange(16)*2*np.pi/16
    ring = np.column_stack([np.cos(angles), np.sin(angles), np.zeros(16)])
    vertices = np.vstack([ring, ring+np.array([1., 0., 0.])])
    with pytest.raises(ValueError):
        triangulate_annulus(vertices, np.arange(16), np.arange(16, 32),
                            np.zeros(3), np.eye(3), engine=engine)
