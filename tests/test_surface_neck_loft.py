from copy import deepcopy
import numpy as np
import pytest
import trimesh
from test_lesions import inputs
from test_saccular_spec import parameters
from vv_toolbox.saccular import saccular_spec
from vv_toolbox.surface_neck_loft import build_surface_neck_loft


def test_open_patch_keeps_exact_boundary_and_single_tip():
    case,_=inputs()
    spec=saccular_spec(case,**parameters())
    before=deepcopy((case,spec))
    v,f,meta=build_surface_neck_loft(case,spec,ray_half_span_mm=1.,ray_step_mm=.05)
    np.testing.assert_array_equal(v[:64],meta['attachment']['curve_mm'])
    np.testing.assert_allclose(v[-1],[10,7,0],atol=1e-12)
    mesh=trimesh.Trimesh(vertices=v,faces=f,process=False)
    assert mesh.euler_number==1 and not mesh.is_watertight
    assert meta['checks']['closed_lumen']=='NOT RUN'
    assert (case,spec)==before
    assert np.unique(v,axis=0).shape==v.shape
    np.testing.assert_allclose(np.ptp(v,axis=0)[[0,2]],[4,3],atol=.01)


@pytest.mark.parametrize('rings',[0,7,1025,True])
def test_invalid_resolution_rejected(rings):
    case,_=inputs()
    with pytest.raises(ValueError,match='rings'):
        build_surface_neck_loft(case,saccular_spec(case,**parameters()),
            ray_half_span_mm=1.,ray_step_mm=.05,rings=rings)
