import numpy as np
import pytest
import trimesh

from vv_toolbox.voxel_output import Grid, Surface, crop, voxelize


def surface(mesh, instance=1, label=7, provenance='source', frame='test_LPS'):
    return Surface(instance, label, provenance, mesh.vertices, mesh.faces, frame, 'synthetic-test-fixture')


def test_box_centres_boundary_and_metadata():
    grid = Grid((5, 5, 5), (1., 1., 1.), (-2., -2., -2.), 'test_LPS')
    output = voxelize([surface(trimesh.creation.box(extents=[2, 2, 2]))], grid)
    assert output.foreground.sum() == 27  # includes faces, edges, vertices
    assert output.anatomical[2, 2, 2] == 7
    assert output.instance[2, 2, 2] == 1
    assert output.metadata()['array_order'] == 'zyx'
    assert output.metadata()['dtypes']['membership'] == 'bool'


def test_crop_retains_independent_anatomical_registry():
    from copy import deepcopy
    from vv_toolbox.anatomical_labels import REGISTRY
    grid = Grid((5,5,5),(1.,1.,1.),(-2.,-2.,-2.),'test_LPS')
    output = voxelize([surface(trimesh.creation.box(extents=[2,2,2]))],grid)
    output.anatomical_registry = deepcopy(REGISTRY)
    cropped = crop(output,[1,1,1],[4,4,4])
    assert cropped.metadata()['anatomical_registry']==REGISTRY
    cropped.anatomical_registry['labels'][0]['id']=999
    assert output.anatomical_registry==REGISTRY


def test_sphere_and_tube_agree_with_analytic_interiors():
    grid = Grid((9, 9, 9), (.5, .5, .5), (-2., -2., -2.), 'test_LPS')
    z, y, x = np.indices(grid.shape_zyx) * .5 - 2
    radius = np.sqrt(x*x + y*y + z*z)
    sphere = voxelize([surface(trimesh.creation.icosphere(subdivisions=2, radius=1.5))], grid)
    assert sphere.foreground[radius < 1.4].all()
    assert not sphere.foreground[radius > 1.5].any()
    tube = voxelize([surface(trimesh.creation.cylinder(radius=1.5, height=2., sections=32))], grid)
    r = np.sqrt(x*x + y*y)
    assert tube.foreground[(r < 1.4) & (np.abs(z) <= 1.)].all()
    assert not tube.foreground[(r > 1.5) | (np.abs(z) > 1.)].any()


def test_overlaps_preserve_memberships_and_conflicting_labels():
    mesh = trimesh.creation.box(extents=[2, 2, 2])
    inputs = [surface(mesh, 9, 8, 'estimated'), surface(mesh, 2, 7), surface(mesh, 4, 7)]
    grid = Grid((3, 3, 3), (1., 1., 1.), (-1., -1., -1.), 'test_LPS')
    output = voxelize(inputs, grid)
    reverse = voxelize(inputs[::-1], grid)
    assert (output.instance == 2).all()
    assert (output.anatomical == 0).all()
    assert (output.provenance == 3).all()
    assert (output.overlap_count == 3).all()
    assert output.membership.all()
    assert np.array_equal(output.membership, reverse.membership)
    assert [s['instance_id'] for s in output.instances] == [2, 4, 9]


def test_unknown_anatomy_is_foreground_not_background():
    output = voxelize([surface(trimesh.creation.box(), label=0)], Grid((1, 1, 1), (1, 1, 1), (0, 0, 0), 'test_LPS'))
    assert output.foreground.item() and output.anatomical.item() == 0


def test_crop_world_coordinates_and_independent_storage():
    grid = Grid((7, 8, 9), (.5, 1., 2.), (10., 20., 30.), 'test_LPS')
    mesh = trimesh.creation.box(extents=[5, 10, 20])
    mesh.apply_translation([12, 24, 36])
    whole = voxelize([surface(mesh)], grid)
    roi = crop(whole, (2, 3, 1), (6, 7, 8))
    local = np.array([2, 1, 3, 1])
    global_index = local + np.array([1, 3, 2, 0])
    assert np.array_equal(roi.grid.affine_xyz @ local, whole.grid.affine_xyz @ global_index)
    assert np.array_equal(roi.membership, whole.membership[:, 2:6, 3:7, 1:8])
    roi.foreground[:] = False
    assert whole.foreground.any()
    # A finer independently sampled grid shares the same physical frame.
    fine_grid = Grid((3, 3, 3), (.25, .5, 1.), (11., 23., 34.), 'test_LPS')
    fine = voxelize([surface(mesh)], fine_grid)
    assert np.array_equal(fine.grid.affine_xyz @ [2, 2, 2, 1], grid.affine_xyz @ [3, 4, 3, 1])


@pytest.mark.parametrize('mutation', ['open', 'inverted', 'degenerate', 'invalid_index', 'nan'])
def test_invalid_meshes_rejected(mutation):
    mesh = trimesh.creation.box()
    vertices, faces = mesh.vertices.copy(), mesh.faces.copy()
    if mutation == 'open': faces = faces[:-1]
    if mutation == 'inverted': faces = faces[:, ::-1]
    if mutation == 'degenerate': vertices[0] = vertices[1]
    if mutation == 'invalid_index': faces[0, 0] = len(vertices)
    if mutation == 'nan': vertices[0, 0] = np.nan
    s = Surface(1, 1, 'source', vertices, faces, 'test_LPS', 'fixture')
    with pytest.raises(ValueError):
        voxelize([s], Grid((3, 3, 3), (1, 1, 1), (0, 0, 0), 'test_LPS'))


def test_memory_frame_duplicate_id_and_invalid_grid():
    s = surface(trimesh.creation.box())
    grid = Grid((3, 3, 3), (1, 1, 1), (0, 0, 0), 'test_LPS')
    with pytest.raises(ValueError, match='budget'): voxelize([s], grid, max_bytes=1024)
    with pytest.raises(ValueError, match='frame'): voxelize([s], Grid((1, 1, 1), (1, 1, 1), (0, 0, 0), 'other'))
    with pytest.raises(ValueError, match='unique'): voxelize([s, s], grid)
    with pytest.raises(ValueError): Grid((True, 1, 1), (1, 1, 1), (0, 0, 0), 'x')
    with pytest.raises(ValueError): Grid((1, 1, 1), (0, 1, 1), (0, 0, 0), 'x')
    with pytest.raises(ValueError): crop(voxelize([s], grid), (0, 0, 0), (4, 2, 2))
