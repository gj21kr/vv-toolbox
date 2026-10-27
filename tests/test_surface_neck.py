from copy import deepcopy
import numpy as np
import pytest
from test_lesions import inputs
from test_saccular_spec import parameters
from vv_toolbox.saccular import saccular_spec
from vv_toolbox.surface_neck import propose_surface_neck


def test_circular_parent_contour_matches_analytic_cylinder_and_preserves_input():
    case,_=inputs()
    spec=saccular_spec(case,**parameters())
    before=deepcopy((case,spec))
    report=propose_surface_neck(case,spec,ray_half_span_mm=1.,ray_step_mm=.05)
    curve=np.array(report['curve_mm'])
    np.testing.assert_allclose(curve[:,1],np.sqrt(4-curve[:,2]**2),atol=1e-9)
    np.testing.assert_allclose(report['projected_width_depth_mm'],[2,1],atol=1e-9)
    assert (case,spec)==before and report['checks']['generated_sac']=='NOT RUN'


def test_curved_parent_rim_can_move_both_inward_and_outward():
    case,_=inputs()
    points=[[0,0,0],[10,0,0],[20,1,0]]
    case['edges'][0].update(centerline_mm=points,radii_mm=[2,2,2])
    case['nodes']['b']['position_mm']=points[-1]
    p=parameters()
    tangent=np.array([10.,1,0])/np.sqrt(101)
    normal=np.array([-1.,10,0])/np.sqrt(101)
    p.update(width_direction=tangent.tolist(),outward_normal=normal.tolist(),
             neck_center_mm=(np.array([10,0,0])+2*normal).tolist())
    report=propose_surface_neck(case,saccular_spec(case,**p),ray_half_span_mm=1.,ray_step_mm=.05)
    assert report['parent_field_max_abs_residual_mm']<1e-7
    assert report['normal_offset_range_mm'][0]<0<report['normal_offset_range_mm'][1]


@pytest.mark.parametrize('options',[
    {'ray_half_span_mm':.001,'ray_step_mm':.0001},
    {'ray_half_span_mm':1.,'ray_step_mm':float('nan')},
    {'ray_half_span_mm':1.,'ray_step_mm':1e-8}])
def test_invalid_or_unbracketed_ray_rejected(options):
    case,_=inputs()
    with pytest.raises(ValueError):
        propose_surface_neck(case,saccular_spec(case,**parameters()),**options)


def test_multiple_crossings_are_not_silently_reduced_to_one(monkeypatch):
    import vv_toolbox.surface_neck as module
    case,_=inputs()
    def folded_field(world,points,radii):
        z=world[:,1]-2
        return (z+.51)*(z-.01)*(z-.49)
    monkeypatch.setattr(module,'_parent_field',folded_field)
    with pytest.raises(ValueError,match='multiple parent crossings'):
        propose_surface_neck(case,saccular_spec(case,**parameters()),
                             ray_half_span_mm=1.,ray_step_mm=.05)


def test_adaptive_chords_add_projected_points_without_moving_originals(monkeypatch):
    import vv_toolbox.surface_neck as module
    case,_=inputs()
    # A curved graph whose straight chords lie outside: independent analytic field.
    def curved_field(world,points,radii):
        return world[:,1]-2-.002*(world[:,0]-10)**2
    monkeypatch.setattr(module,'_parent_field',curved_field)
    spec=saccular_spec(case,**parameters())
    coarse=propose_surface_neck(case,spec,ray_half_span_mm=1.,ray_step_mm=.05)
    refined=propose_surface_neck(case,spec,ray_half_span_mm=1.,ray_step_mm=.05,refine_chords=True)
    assert coarse['chord_refinement']['status']=='FAIL'
    assert refined['chord_refinement']['status']=='PASS'
    assert 64<len(refined['curve_mm'])<=512
    indices=np.searchsorted(refined['angles_radians'],coarse['angles_radians'])
    np.testing.assert_array_equal(np.asarray(refined['curve_mm'])[indices],coarse['curve_mm'])
    np.testing.assert_allclose(refined['projected_width_depth_mm'],[2,1],atol=1e-10)
