from copy import deepcopy
import numpy as np
import trimesh
from test_bifurcation_saccular import fixture
from vv_toolbox.bifurcation_saccular import bifurcation_saccular_spec
from vv_toolbox.source_sac_union import build_source_sac_union


def test_closed_union_has_no_neck_cap_and_preserves_exterior():
    case,p=fixture();p.update(neck_center_mm=[0,0,2],outward_normal=[0,0,1],width_direction=[1,0,0])
    spec=bifurcation_saccular_spec(case,**p);source=trimesh.creation.box(extents=[4,4,4]);before=deepcopy(case)
    v,f,meta=build_source_sac_union(case,spec,source.vertices,source.faces,source_part_id='synthetic-box',axial_rings=4)
    mesh=trimesh.Trimesh(vertices=v,faces=f,process=False)
    assert mesh.is_volume and mesh.volume>source.volume
    assert meta['self_contact']['status']=='NO_CONTACT_DETECTED'
    assert meta['retained_triangle_identity']=='PASS' and case==before
    assert meta['source_triangle_containment']=='PASS'
    retained=meta['retained_output_face_ids']
    assert len(retained)>0
    lineage=np.asarray(meta['source_face_ids'])
    np.testing.assert_array_equal(v[f[retained]],source.triangles[lineage[retained]])
    assert np.all(lineage[len(meta['opening']['source_face_ids']):]==-1)
    assert mesh.contains([[0,0,0],[0,0,2],[0,0,3]]).all()
    # Shared neck edges have two incident faces, no third cap face.
    assert np.all(np.bincount(mesh.edges_unique_inverse)==2)
    assert not meta['accepted_for_generation']
