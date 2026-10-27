from copy import deepcopy
import numpy as np
from test_lesions import inputs
from vv_toolbox.surface_context import inspect_surface_context


def context():
    case,_=inputs()
    edge=deepcopy(case['edges'][0])
    edge.update(id='other',start='c',end='d',centerline_mm=[[0,0,-2],[0,0,2]],radii_mm=[.5,.5])
    for n,p in [('c',[0,0,-2]),('d',[0,0,2])]:
        case['nodes'][n]=dict(case['nodes']['a'],position_mm=p)
    case['edges'].append(edge)
    return case


def test_triangle_interior_overlap_is_not_passed_by_clear_vertices():
    vertices=np.array([[-2,-1,0],[2,-1,0],[0,2,0]],dtype=float)
    report=inspect_surface_context(context(),vertices,[[0,1,2]],parent_edge_id='e')
    assert report['status']=='REVIEW_REQUIRED'
    assert report['results'][0]['status']=='PROFILE_INTERIOR_WITNESS'
    witness=report['results'][0]['witness']
    assert witness['face_index']==0
    assert np.allclose(np.array(witness['barycentric'])@vertices,witness['position_mm'])
    assert report['results'][0]['overlap_vertices'] is None


def test_profile_witness_and_distant_exclusion():
    case=context()
    vertices=np.array([[0,0,0],[.1,0,0],[0,.1,0]])
    report=inspect_surface_context(case,vertices,[[0,1,2]],parent_edge_id='e')
    assert report['results'][0]['status']=='PROFILE_INTERIOR_WITNESS'
    report=inspect_surface_context(case,vertices+100,[[0,1,2]],parent_edge_id='e')
    assert report['status']=='SEPARATED_PROFILES' and report['aabb_separated_count']==1


def test_unused_vertices_are_not_surface_witnesses_and_original_ids_survive():
    vertices=np.array([[0.,0.,0.],[10.,10.,0.],[11.,10.,0.],[10.,11.,0.]])
    report=inspect_surface_context(context(),vertices,[[1,2,3]],parent_edge_id='e')
    assert report['status']=='SEPARATED_PROFILES'
    assert report['unused_vertex_count']==1
    vertices=np.array([[100.,100.,100.],[0.,0.,0.],[.1,0.,0.],[0.,.1,0.]])
    report=inspect_surface_context(context(),vertices,[[1,2,3]],parent_edge_id='e')
    assert report['results'][0]['witness']['vertex_index']==1
    assert report['results'][0]['overlap_vertices']['vertex_count']==3


def test_missing_context_cannot_be_passed():
    case=context()
    case['edges'][1].update(centerline_mm=None,radii_mm=None)
    report=inspect_surface_context(case,[[10,0,0],[11,0,0],[10,1,0]],[[0,1,2]],parent_edge_id='e')
    assert report['status']=='REVIEW_REQUIRED'


def test_triangle_bound_proves_separation_inside_overlapping_aabbs():
    # Both x/y coordinates are within the capsule AABB, but radial distance
    # stays above .5 everywhere on this small triangle.
    vertices=[[.45,.45,0],[.46,.45,0],[.45,.46,0]]
    report=inspect_surface_context(context(),vertices,[[0,1,2]],parent_edge_id='e')
    assert report['aabb_separated_count']==0
    assert report['results'][0]['lower_bound_mm']>0
    assert report['status']=='SEPARATED_PROFILES'


def test_overlap_summary_accounts_for_every_vertex_and_missing_parent():
    case=context()
    # Set parent equal to context: every context witness is also in parent.
    case['edges'][0]['centerline_mm']=[[0,0,-2],[0,0,2]]
    case['edges'][0]['radii_mm']=[.5,.5]
    case['nodes']['a']['position_mm']=[0,0,-2]
    case['nodes']['b']['position_mm']=[0,0,2]
    vertices=[[0,0,0],[.1,0,0],[0,.1,0]]
    report=inspect_surface_context(case,vertices,[[0,1,2]],parent_edge_id='e')
    summary=report['results'][0]['overlap_vertices']
    assert summary['vertex_count']==summary['baseline_inside_count']==3
    assert summary['baseline_outside_count']==summary['baseline_surface_band_count']==0
    case['edges'][0].update(centerline_mm=None,radii_mm=None)
    report=inspect_surface_context(case,vertices,[[0,1,2]],parent_edge_id='e')
    assert report['results'][0]['overlap_vertices']['baseline_parent_status']=='UNKNOWN'


def test_interior_sampling_budget_never_implies_clearance():
    from vv_toolbox.surface_context import _interior_witness
    triangles=np.array([[[-2,-1,0],[2,-1,0],[0,2,0]]],dtype=float)
    point=np.array([[-.9,-.8,-1],[-.9,-.8,1]])
    # The root centroid misses this thin off-center profile. A bounded miss
    # is inconclusive, even though its interior contains an intersection.
    witness,count=_interior_witness(triangles,[0],point,np.array([.01,.01]),max_samples=1)
    assert witness is None and count==1


def test_subdivision_detects_off_center_intersection_and_retains_face_address():
    from vv_toolbox.surface_context import _interior_witness
    triangles=np.array([[[-2,-1,0],[2,-1,0],[0,2,0]]],dtype=float)
    points=np.array([[-1,-.5,-1],[-1,-.5,1]])
    witness,count=_interior_witness(triangles,[0],points,np.array([.05,.05]),max_depth=1)
    assert witness is not None and count>1
    weights=np.array(witness['barycentric'])
    assert np.isclose(weights.sum(),1) and np.all(weights>=0)
    assert np.allclose(weights@triangles[witness['face_index']],witness['position_mm'])


def test_refined_separation_requires_complete_triangle_coverage():
    from vv_toolbox.surface_context import refine_profile_separation
    vertices=[[-2,.6,0],[2,.6,0],[0,.6,1]]
    points=[[0,0,-2],[0,0,2]]
    limited=refine_profile_separation(vertices,[[0,1,2]],points,[.5,.5],max_cells=1)
    assert limited['status']=='UNKNOWN' and limited['lower_bound_mm'] is None
    result=refine_profile_separation(vertices,[[0,1,2]],points,[.5,.5])
    assert result['status']=='SEPARATED_PROFILE'
    assert 0<result['lower_bound_mm']<=.1
    assert result['unresolved_cells']==0


def test_refined_separation_finds_triangle_interior_witness():
    from vv_toolbox.surface_context import refine_profile_separation
    result=refine_profile_separation([[-2,-1,0],[2,-1,0],[0,2,0]],[[0,1,2]],
                                    [[0,0,-2],[0,0,2]],[.5,.5])
    assert result['status']=='PROFILE_INTERIOR_WITNESS'
    assert result['witness']['profile_field_mm']<0
