import numpy as np
import pytest
import trimesh
from test_bifurcation_rim_continuity import inputs
from vv_toolbox.curved_sac_patch import build_curved_sac_patch


def test_patch_keeps_exact_rim_and_declared_dimensions():
    case,spec,rim=inputs()
    v,f,m=build_curved_sac_patch(case,spec,rim,rim_tolerance_mm=.02,axial_rings=4)
    np.testing.assert_array_equal(v[:64],rim['curve_mm'])
    np.testing.assert_allclose(m['measured_width_depth_height_mm'],[4,3,5],atol=1e-6)
    mesh=trimesh.Trimesh(vertices=v,faces=f,process=False)
    assert mesh.euler_number==1 and not mesh.is_watertight and mesh.is_winding_consistent
    assert not m['closed_lumen'] and not m['accepted_for_generation']
    assert m['self_contact']['status']=='NO_CONTACT_DETECTED'


def test_failed_rim_is_not_used_to_generate_surface():
    case,spec,rim=inputs()
    with pytest.raises(ValueError,match='continuity'):
        build_curved_sac_patch(case,spec,rim,rim_tolerance_mm=.0001)


def test_incomplete_contact_check_prevents_candidate_return():
    case,spec,rim=inputs()
    with pytest.raises(ValueError,match='self-contact'):
        build_curved_sac_patch(case,spec,rim,rim_tolerance_mm=.02,axial_rings=4,max_contact_pairs=1)
