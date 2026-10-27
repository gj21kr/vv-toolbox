import numpy as np
import pytest
import trimesh

from vv_toolbox.estimated_tube_volume import cap_estimated_neck
from vv_toolbox.profile_loft import loft_source_profiles


def test_nonconvex_measured_contour_cap_preserves_side_triangles():
    contour=np.array([[0,0],[3,0],[3,1],[1,1],[1,3],[0,3],[0,0]],float)
    profiles=[dict(status='MEASURED',index=i,normal=[0.,0.,1.],
                   contour_xyz_mm=np.column_stack([contour,np.full(len(contour),z)]).tolist())
              for i,z in enumerate([0.,4.])]
    mesh,_=loft_source_profiles(profiles,samples=24)
    part=dict(vertices=mesh.vertices,faces=mesh.faces,
              metadata=dict(kind='estimated-neck-connector',original_atlas_geometry=False))
    result=cap_estimated_neck(part,max_planarity_mm=.001,cap_method='planar-earcut')
    volume=trimesh.Trimesh(result['vertices'],result['faces'],process=False)
    assert volume.is_volume
    assert volume.volume==pytest.approx(20.)
    assert np.array_equal(volume.triangles[:len(mesh.faces)],mesh.triangles)
    assert result['metadata']['volume_derivation']['self_contact']['status']=='NO_CONTACT_DETECTED'
