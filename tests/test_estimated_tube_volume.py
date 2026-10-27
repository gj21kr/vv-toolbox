import numpy as np
import pytest
import trimesh

from vv_toolbox.estimated_tube_volume import cap_estimated_neck


def tube():
    mesh=trimesh.creation.cylinder(radius=1.,height=5.,sections=16)
    keep=np.abs(mesh.face_normals[:,2])<.5
    return dict(id='estimate',layer='arterial',vertices=mesh.vertices.copy(),faces=mesh.faces[keep].copy(),
                metadata=dict(kind='estimated-neck-connector',original_atlas_geometry=False))


def test_caps_preserve_source_triangles_and_make_closed_volume():
    part=tube()
    before=part['vertices'][part['faces']].copy()
    result=cap_estimated_neck(part,max_planarity_mm=.001)
    assert np.array_equal(result['vertices'][result['faces'][:len(part['faces'])]],before)
    assert np.array_equal(part['vertices'][part['faces']],before)
    assert trimesh.Trimesh(result['vertices'],result['faces'],process=False).is_volume
    assert result['metadata']['volume_derivation']['added_faces']==32
    assert 'volume_derivation' not in part['metadata']


def test_original_mesh_cannot_be_capped_as_an_estimate():
    part=tube();part['metadata']['original_atlas_geometry']=True
    with pytest.raises(ValueError,match='explicitly estimated'):
        cap_estimated_neck(part,max_planarity_mm=.001)


def test_distorted_end_rejected_without_modifying_source():
    part=tube()
    used=np.unique(part['faces'])
    index=next(int(i) for i in used if part['vertices'][i,2]>0)
    part['vertices'][index,2]+=.1
    before=part['vertices'].copy()
    with pytest.raises(ValueError,match='planarity'):
        cap_estimated_neck(part,max_planarity_mm=.001)
    assert np.array_equal(before,part['vertices'])
