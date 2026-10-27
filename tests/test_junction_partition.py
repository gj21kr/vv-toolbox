import numpy as np
import trimesh

from vv_toolbox.junction_partition import partition_source_junction
from vv_toolbox.patch_boundary import patch_boundary_loops


def test_full_source_reassembly_has_shared_seams_and_complete_coverage():
    source = trimesh.creation.icosphere(subdivisions=2)
    angles = np.arange(3)*2*np.pi/3
    normals = np.column_stack((np.cos(angles), np.sin(angles), np.zeros(3)))
    original = source.vertices.copy(), source.faces.copy()
    mesh, lineage, labels, report = partition_source_junction(source, .8*normals, normals, [0,0,0])
    assert mesh.is_watertight and mesh.euler_number == source.euler_number
    assert np.isclose(mesh.area, source.area, rtol=1e-10)
    assert np.isclose(mesh.volume, source.volume, rtol=1e-10)
    assert set(lineage) == set(range(len(source.faces)))
    assert set(labels) == {0,1,2,3}
    for i, boundary in enumerate(report['port_boundary_vertex_ids']):
        loops = patch_boundary_loops(mesh.faces, np.flatnonzero(labels == i+1))
        assert len(loops) == 1 and set(loops[0]) == set(boundary)
    assert np.array_equal(source.vertices, original[0])
    assert np.array_equal(source.faces, original[1])


def test_translated_rotated_source_preserves_partition():
    source = trimesh.creation.icosphere(subdivisions=2)
    angles = np.arange(3)*2*np.pi/3
    normals = np.column_stack((np.cos(angles), np.sin(angles), np.zeros(3)))
    transform = trimesh.transformations.rotation_matrix(.37, [1,2,3])
    rotation = transform[:3,:3]
    origin = np.array([-2., -150., 1542.])
    source.vertices = source.vertices @ rotation.T + origin
    normals = normals @ rotation.T
    mesh, _, labels, report = partition_source_junction(source, .8*normals+origin, normals, origin)
    assert mesh.is_watertight and set(labels) == {0,1,2,3}
    assert report['source_face_coverage'] == 'PASS'
