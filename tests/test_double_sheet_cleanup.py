import numpy as np
import pytest
import trimesh

from vv_toolbox.double_sheet_cleanup import remove_isolated_double_sheets


def test_only_isolated_opposite_sheet_removed():
    box=trimesh.creation.box()
    sheet=trimesh.Trimesh([[3.,0,0],[4,0,0],[3,1,0]],[[0,1,2],[0,2,1]],process=False)
    source=trimesh.util.concatenate([box,sheet])
    original=source.triangles.copy()
    result,report=remove_isolated_double_sheets(source)
    assert report['removed_source_face_ids']==[12,13]
    assert np.array_equal(result.triangles,original[:12])
    assert np.array_equal(source.triangles,original)
    assert result.is_volume and result.volume==pytest.approx(box.volume)
    assert report['self_contact']['status']=='NO_CONTACT_DETECTED'


def test_valid_box_not_silently_changed():
    with pytest.raises(ValueError,match='No isolated'):
        remove_isolated_double_sheets(trimesh.creation.box())


def test_sheet_attached_along_existing_edge_not_removed():
    box=trimesh.creation.box()
    faces=np.vstack([box.faces,box.faces[0],box.faces[0][::-1]])
    with pytest.raises(ValueError,match='No isolated'):
        remove_isolated_double_sheets(trimesh.Trimesh(box.vertices,faces,process=False))
