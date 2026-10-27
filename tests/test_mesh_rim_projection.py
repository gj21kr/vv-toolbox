import numpy as np
import pytest
import trimesh
from vv_toolbox.mesh_rim_projection import project_rim_to_mesh


def test_projects_to_actual_box_faces_with_original_face_indices():
    mesh=trimesh.creation.box(extents=[4,4,4])
    rim=np.array([[.7,0,3],[0,.7,3],[-.7,0,3],[0,-.7,3]])
    result=project_rim_to_mesh(mesh.vertices,mesh.faces,rim,[0,0,1],lower_mm=-3,upper_mm=1)
    assert result['resolved_sample_count']==4
    np.testing.assert_allclose(np.asarray(result['curve_mm'])[:,2],2)
    np.testing.assert_allclose(np.asarray(result['curve_mm'])[:,:2],rim[:,:2])
    for sample in result['samples']:
        assert np.all(mesh.triangles[sample['source_face_index'],:,2]==2)
    assert not result['accepted_for_generation']


def test_missing_and_multiple_exits_are_not_auto_selected():
    mesh=trimesh.creation.box(extents=[2,2,2]);other=mesh.copy();other.apply_translation([0,0,4])
    mesh=trimesh.util.concatenate([mesh,other]);rim=[[.2,0,0],[0,.2,0],[-.2,0,0]]
    result=project_rim_to_mesh(mesh.vertices,mesh.faces,rim,[0,0,1],lower_mm=-2,upper_mm=6)
    assert result['curve_mm'] is None and all(r['exit_count']==2 for r in result['samples'])
    result=project_rim_to_mesh(mesh.vertices,mesh.faces,rim,[0,0,1],lower_mm=6,upper_mm=7)
    assert result['resolved_sample_count']==0


def test_open_mesh_is_rejected():
    with pytest.raises(ValueError,match='closed'):
        project_rim_to_mesh([[0,0,0],[1,0,0],[0,1,0]],[[0,1,2]],[[0,0,1],[1,0,1],[0,1,1]],[0,0,1],lower_mm=-2,upper_mm=2)
