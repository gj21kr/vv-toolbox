import numpy as np
import pytest

from test_union_radius import fixture
from vv_toolbox.union_shape import deform_selected_shape, ShapeEditFailure


def deform(mesh, lineage, **options):
    parameters = dict(bend_mm=.1, bend_direction=[1, 0, 0], twist_deg=10.,
                      collar_mm=.1, transition_mm=1., max_displacement_mm=.5)
    parameters.update(options)
    return deform_selected_shape(mesh, lineage, 'middle', [[0, 0, 0], [0, 0, 2], [0, 0, 4]], **parameters)


def test_bend_twist_preserves_interfaces_and_maps_path():
    mesh, lineage = fixture()
    before = mesh.vertices.copy()
    changed, path, audit = deform(mesh, lineage)
    middle = np.isclose(before[:, 2], 2)
    assert np.array_equal(changed.vertices[~middle], before[~middle])
    assert np.array_equal(changed.faces, mesh.faces)
    assert np.array_equal(mesh.vertices, before)
    assert path[1, 0] == pytest.approx(.1)
    np.testing.assert_array_equal(path[[0, -1]], [[0, 0, 0], [0, 0, 4]])
    assert audit['fixed_vertices_unchanged']
    assert audit['centerline_containment']['status'] == 'PASS'
    assert audit['neighboring_vessels'] == 'NOT RUN'
    assert changed.is_volume


def test_zero_shape_is_identity():
    mesh, lineage = fixture()
    changed, path, _ = deform(mesh, lineage, bend_mm=0, twist_deg=0)
    np.testing.assert_array_equal(changed.vertices, mesh.vertices)
    np.testing.assert_array_equal(path, [[0, 0, 0], [0, 0, 2], [0, 0, 4]])


def test_internal_graph_junction_stays_fixed_in_shared_field():
    mesh, lineage = fixture()
    changed, path, audit = deform(mesh, lineage, protected_points_mm=[[0, 0, 2]])
    np.testing.assert_array_equal(path[1], [0, 0, 2])
    assert audit['protected_graph_points'] == 1
    assert audit['protected_graph_points_fixed']
    assert not np.array_equal(changed.vertices, mesh.vertices)
    assert audit['centerline_containment']['status'] == 'PASS'


@pytest.mark.parametrize('points', [[[float('nan'), 0, 0]], [0, 0, 2], [[0, 1]]])
def test_invalid_graph_protection_rejected(points):
    mesh, lineage = fixture()
    with pytest.raises(ValueError, match='protected graph'):
        deform(mesh, lineage, protected_points_mm=points)


def test_rejection_records_actual_surface_and_path_displacement():
    mesh, lineage = fixture()
    original = mesh.vertices.copy()
    with pytest.raises(ShapeEditFailure) as failure:
        deform(mesh, lineage, bend_mm=4, twist_deg=0)
    record = failure.value.measurements
    assert record['path_maximum_mm'] == pytest.approx(4)
    assert record['surface_maximum_mm'] == pytest.approx(4)
    assert record['displacement_bound_mm'] == .5
    np.testing.assert_array_equal(mesh.vertices, original)


@pytest.mark.parametrize('parameters', [dict(bend_mm=4), dict(twist_deg=True),
    dict(collar_mm=-1), dict(transition_mm=0), dict(bend_direction=[0, 0, 1])])
def test_invalid_or_excessive_shape_rejected(parameters):
    mesh, lineage = fixture()
    with pytest.raises(ValueError):
        deform(mesh, lineage, **parameters)
