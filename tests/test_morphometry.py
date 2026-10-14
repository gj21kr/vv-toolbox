import json
import numpy as np
import pytest
from vv_toolbox.model import Segment,VesselGraph
from vv_toolbox.morphometry import centerline_metrics,branch_angle,arch_height_ratio


def test_straight_line_length_zero_curvature_and_undefined_torsion():
    points=np.column_stack((np.array([0.,1.,3.,8.,10.]),np.zeros((5,2))))
    result=centerline_metrics(points)
    assert result['length_mm']==10
    assert result['curvature']['maximum']==0
    assert result['torsion']['status']=='UNKNOWN'
    assert result['torsion_undefined_samples']==256


def test_circle_curvature_and_planar_torsion():
    theta=np.linspace(0,np.pi,301)
    radius=12.
    points=np.column_stack((radius*np.cos(theta),radius*np.sin(theta),np.zeros_like(theta)))
    result=centerline_metrics(points)
    assert result['length_mm']==pytest.approx(np.pi*radius,rel=1e-5)
    assert result['curvature']['mean']==pytest.approx(1/radius,rel=1e-4)
    assert abs(result['torsion']['mean'])<1e-10


def test_helix_curvature_and_torsion_use_3d_arc_parameter():
    theta=np.linspace(0,2*np.pi,601)**1.03
    radius,rise=10.,2.
    points=np.column_stack((radius*np.cos(theta),radius*np.sin(theta),rise*theta))
    result=centerline_metrics(points)
    assert result['curvature']['median']==pytest.approx(radius/(radius**2+rise**2),rel=1e-3)
    assert result['torsion']['median']==pytest.approx(rise/(radius**2+rise**2),rel=2e-3)


def test_closed_circle_and_short_polyline_are_explicit():
    theta=np.linspace(0,2*np.pi,101)
    result=centerline_metrics(np.column_stack((np.cos(theta),np.sin(theta),np.zeros_like(theta))))
    assert result['closed'] is True
    assert result['curvature']['mean']==pytest.approx(1,rel=.001)
    short=centerline_metrics([[0,0,0],[1,0,0]])
    assert short['length_mm']==1 and short['curvature']['status']=='UNKNOWN'


def test_fixed_window_branch_angle_azimuth_and_endpoint_orientation():
    parent=np.array([[-10.,0,0],[0,0,0]])
    daughter=np.array([[0.,0,0],[0,0,10]])
    result=branch_angle(parent,daughter,window_mm=5,reference_direction=(0,1,0))
    assert result['status']=='PASS' and result['angle_deg']==pytest.approx(90)
    assert result['azimuth_deg']==pytest.approx(90)
    reversed_result=branch_angle(parent[::-1],daughter[::-1],window_mm=5,parent_end='start',daughter_end='end')
    assert reversed_result['angle_deg']==pytest.approx(90)
    assert branch_angle(parent,daughter,window_mm=11)['status']=='UNKNOWN'
    assert branch_angle(parent,daughter+1,window_mm=5)['status']=='UNKNOWN'


def test_window_changes_are_reported_not_silently_shortened():
    parent=[[-10,0,0],[0,0,0]]
    daughter=[[0,0,0],[2,0,0],[2,8,0]]
    assert branch_angle(parent,daughter,window_mm=1)['angle_deg']==0
    assert branch_angle(parent,daughter,window_mm=6)['angle_deg']>60
    assert branch_angle(parent,daughter,window_mm=6)['window_mm']==6


@pytest.mark.parametrize('ratio,expected',[(.5,'Type I'),(1,'Type II'),(2,'Type II'),(2.5,'Type III')])
def test_arch_surrogate_boundaries_and_left_cca_denominator(ratio,expected):
    result=arch_height_ratio([[0,0,0],[0,1,7*ratio]],[0,0,0],7)
    assert result['ratio']==ratio and result['surrogate_type']==expected
    assert result['clinical_classification'] is False
    assert result['kind']=='centerline-landmark-surrogate'
    axis=np.array([0.,0.,2.])
    arch_height_ratio([[0,0,0],[0,1,7*ratio]],[0,0,0],7,superior_axis=axis)
    np.testing.assert_array_equal(axis,[0,0,2])


@pytest.mark.parametrize('points',[[],[[0,0,0]],[[0,0,0],[0,0,0]],[[0,0,0],[1,float('nan'),0]]])
def test_invalid_centerlines_fail(points):
    with pytest.raises(ValueError):centerline_metrics(points)


@pytest.mark.parametrize('profile',[[1],[[1],[2]],[1,0],[1,-1],[1,float('nan')],[1,float('inf')]])
def test_invalid_radius_profiles_rejected(profile):
    with pytest.raises(ValueError):
        Segment('edge','a','b',np.array([[0.,0,0],[1,0,0]]),1,profile)


def test_profile_export_preserves_coordinates_provenance_and_nominal_compatibility():
    points=np.array([[0.,0,0],[1,0,0],[2,0,0]])
    profile=np.array([1.,1.4,2.])
    edge=Segment('edge','a','b',points,1.4,profile)
    profile[0]=99
    graph=VesselGraph({'a':points[0],'b':points[-1]},[edge],{},
                      provenance={'kind':'external-reference','source':'test synthetic fixture'},coordinates='source-native axes; millimeters')
    record=json.loads(graph.to_json())
    assert record['segments'][0]['radius_profile_mm']==[1,1.4,2]
    assert record['segments'][0]['radius_mm']==1.4
    assert record['coordinates']=='source-native axes; millimeters'
    assert record['provenance']['kind']=='external-reference'
    edge.radius_profile_mm[1]=0
    with pytest.raises(ValueError,match='radius profile'):graph.validate()


def test_generated_arch_reports_requested_and_measured_types_separately():
    from vv_toolbox.model import generate
    graph=generate(radius_scale=2,arch_height_ratio=1.5,tortuosity=0)
    result=graph.parameters['arch_measurement']
    assert result['requested_type']=='Type II'
    assert result['measured_type']=='Type I'
    assert result['type_mismatch'] is True
    assert result['clinical_classification'] is False
    assert result['left_cca_diameter_mm']==14
    assert result['measured_centerline_ratio']==pytest.approx(
        (result['arch_top_centerline_z_mm']-result['innominate_origin_centerline_z_mm'])/14)
    reproduced=generate(**graph.generation_kwargs())
    assert reproduced.parameters==graph.parameters


def test_cerebral_fractional_labels_are_explicitly_estimated_not_source_annotation():
    from vv_toolbox.model import generate
    graph=generate()
    definitions=graph.parameters['segment_definitions']
    assert len(definitions)==18
    assert set(definitions)<=set(edge.name for edge in graph.segments)
    for definition in definitions.values():
        assert definition['status']=='ESTIMATED_SUBDIVISION'
        assert definition['source_annotated'] is False
        assert definition['anatomical_landmarks_validated'] is False
    assert 'segment_definitions' not in graph.generation_kwargs()
