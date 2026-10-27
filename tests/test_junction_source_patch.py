import numpy as np
import pytest
import trimesh

from vv_toolbox.junction_source_patch import clip_source_junction


def fixture():
    mesh = trimesh.creation.icosphere(subdivisions=2)
    angles = np.arange(3)*2*np.pi/3
    normals = np.column_stack((np.cos(angles), np.sin(angles), np.zeros(3)))
    return mesh, .8*normals, normals


def test_three_ports_preserve_source_surface_and_input():
    source, origins, normals = fixture()
    before = source.vertices.copy(), source.faces.copy()
    patch, lineage, report = clip_source_junction(source, origins, normals, [0,0,0])
    assert len(report['port_boundary_vertex_ids']) == 3
    assert len(lineage) == len(patch.faces)
    assert not patch.is_watertight
    assert patch.euler_number == -1  # sphere with three openings
    assert np.array_equal(source.vertices, before[0])
    assert np.array_equal(source.faces, before[1])
    assert report['source_partition_identity'] == 'PASS'
    for i, loop in enumerate(report['port_boundary_vertex_ids']):
        assert np.max(np.abs((patch.vertices[loop]-origins[i])@normals[i])) < 1e-8
    expected = source.triangles[lineage]
    for corner in range(3):
        bary = trimesh.triangles.points_to_barycentric(expected, patch.triangles[:,corner])
        assert bary.min() > -1e-8
        assert np.allclose(np.einsum('ij,ijk->ik', bary, expected), patch.triangles[:,corner], atol=1e-8)


def test_missing_port_is_rejected():
    mesh, origins, normals = fixture()
    origins[0] *= 2
    with pytest.raises(ValueError, match='Every branch port'):
        clip_source_junction(mesh, origins, normals, [0,0,0])


def test_planes_cannot_exclude_junction():
    mesh, origins, normals = fixture()
    with pytest.raises(ValueError, match='strictly inside'):
        clip_source_junction(mesh, origins, -normals, [0,0,0])
