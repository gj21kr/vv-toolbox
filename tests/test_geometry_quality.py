from copy import deepcopy

import pytest

from vv_toolbox.geometry_quality import segment_distance, screen_nonincident_clearance, screen_junction_clearance, screen_self_clearance
from vv_toolbox.case_surface import build_case_surface


@pytest.mark.parametrize('points,expected', [
    (([-10,0,0],[10,0,0],[0,-10,0],[0,10,0]),0),
    (([0,0,0],[10,0,0],[2,3,0],[8,3,0]),3),
    (([0,0,0],[1,0,0],[2,1,0],[2,2,0]),2**.5),
    (([0,0,0],[10,0,0],[5,0,2],[5,4,2]),2)])
def test_continuous_segment_distance(points,expected):
    assert segment_distance(*points) == pytest.approx(expected)
    assert segment_distance(points[2],points[3],points[0],points[1]) == pytest.approx(expected)


def crossing():
    points = {'a':[-10,0,0],'b':[10,0,0],'c':[0,-10,0],'d':[0,10,0]}
    return {'schema':'vv-toolbox.case/1','case_id':'test','base_model_id':'fixture',
      'model_kind':'synthetic','split':'unassigned',
      'generation':{'seed':0,'generator_version':'fixture','config':{}},
      'frame':{'id':'fixture','units':'mm','axes':'LPS','origin':'fixture'},
      'sources':[{'id':'s','sha256':'a'*64,'license_ref':'fixture'}],
      'nodes':{n:{'kind':'unresolved','evidence_status':'unresolved','position_mm':p} for n,p in points.items()},
      'edges':[{'id':ident,'start':a,'end':b,'source_ids':['s'],'geometry_kind':'estimated',
        'evidence_status':'synthetic_estimate',
        'anatomy':{'artery':'fixture','side':'unknown','segment':'unresolved','branch_id':ident},
        'centerline_mm':[points[a],points[b]],'radii_mm':[1,1]}
        for ident,a,b in [('first','a','b'),('second','c','d')]]}


def test_sparse_crossing_cannot_pass_using_endpoint_distance():
    case = crossing()
    before = deepcopy(case)
    report = screen_nonincident_clearance(case,['first','second'])
    assert report['status'] == 'UNKNOWN'
    assert report['potential_contacts'][0]['clearance_lower_bound_mm'] == pytest.approx(-2)
    with pytest.raises(ValueError,match='clearance'):
        build_case_surface(case,['first','second'],spacing_mm=.3)
    assert case == before


def test_focused_screen_keeps_every_surrounding_obstacle_but_excludes_unrelated_pairs():
    case = crossing()
    third = deepcopy(case['edges'][0])
    third.update(id='third',start='e',end='f',centerline_mm=[[-10,0,20],[10,0,20]])
    for node, point in zip(['e','f'],third['centerline_mm']):
        case['nodes'][node] = dict(case['nodes']['a'],position_mm=point)
    case['edges'].append(third)
    selected = ['first','second','third']
    focused = screen_nonincident_clearance(case,selected,focus_edge_ids=['first'])
    assert focused['status']=='UNKNOWN'
    assert focused['potential_contacts'][0]['edges']==['first','second']
    assert focused['coverage']['selected_edge_ids']==selected
    assert focused['coverage']['focus_edge_ids']==['first']
    isolated = screen_nonincident_clearance(case,selected,focus_edge_ids=['third'])
    assert isolated['status']=='PASS' and isolated['bbox_separated_pairs']==2
    assert screen_nonincident_clearance(case,selected)['status']=='UNKNOWN'


@pytest.mark.parametrize('focus',[[],['absent'],['first','first'],'first',[None]])
def test_invalid_focused_scope_is_rejected(focus):
    with pytest.raises(ValueError, match='focus'):
        screen_nonincident_clearance(crossing(),['first','second'],focus_edge_ids=focus)


def test_separated_edges_and_margin():
    case = crossing()
    for n in ['c','d']:
        case['nodes'][n]['position_mm'][2] = 3
    assert screen_nonincident_clearance(case,['first','second'])['status'] == 'PASS'
    assert screen_nonincident_clearance(case,['first','second'],margin_mm=1)['status'] == 'UNKNOWN'


def test_shared_node_not_misreported_as_checked():
    case = crossing()
    e = case['edges'][1]
    e['start'] = 'a'
    e['centerline_mm'][0] = case['nodes']['a']['position_mm']
    del case['nodes']['c']
    report = screen_nonincident_clearance(case,['first','second'])
    assert report['shared_node_pairs_not_checked'] == [['first','second']]
    assert report['checked_segment_pairs'] == 0
    assert report['final_surface_collision'] == 'NOT RUN'


def test_budget_exhaustion_is_unknown_not_safe():
    case = crossing()
    case['edges'][0]['centerline_mm'].insert(1,[-5,0,0])
    case['edges'][0]['radii_mm'].insert(1,1)
    report = screen_nonincident_clearance(case,['first','second'],max_segment_pairs=1)
    assert report['status'] == 'UNKNOWN'
    assert report['reason'] == 'pair_budget_exhausted'


def junction_case(recross=False):
    case = crossing()
    case['nodes'] = {n: {'kind':'junction' if n=='a' else 'scope_boundary',
                        'evidence_status':'synthetic_estimate', 'position_mm':p}
                     for n,p in {'a':[0,0,0],'b':[20,0,0],'d':[20,20,0]}.items()}
    for edge, end, points in zip(case['edges'], ['b','d'],
            [[[0,0,0],[20,0,0]], [[0,0,0],[0,12,0],[14,-4,0],[20,20,0]] if recross
             else [[0,0,0],[0,20,0],[20,20,0]]]):
        edge.update(start='a',end=end,centerline_mm=points,radii_mm=[1]*len(points))
    return case


def test_shared_junction_remote_crossing_is_not_exempt():
    case = junction_case(True)
    original = deepcopy(case)
    # Old nonincident-only screen intentionally skips this pair.
    assert screen_nonincident_clearance(case,['first','second'])['status']=='PASS'
    report = screen_junction_clearance(case,['first','second'],collars_mm={'a':4})
    assert report['status']=='UNKNOWN'
    assert report['potential_contacts'] and report['checked_segment_pairs']>0
    assert case==original
    with pytest.raises(ValueError,match='shared-junction'):
        build_case_surface(case,['first','second'],spacing_mm=.3)


def test_local_junction_allowed_but_rest_is_checked_even_with_sparse_samples():
    report=screen_junction_clearance(junction_case(),['first','second'],collars_mm={'a':4})
    assert report['status']=='PASS'
    assert report['exempt_segment_pairs']==1 and report['checked_segment_pairs']>0
    assert report['inside_junction_collars']=='NOT CHECKED'
    assert report['final_surface_collision']=='NOT RUN'


def test_junction_screen_independent_of_edge_orientation_and_sampling():
    case=junction_case(True)
    for edge in case['edges']:
        edge['start'],edge['end']=edge['end'],edge['start']
        edge['centerline_mm'].reverse()
        edge['radii_mm'].reverse()
    assert screen_junction_clearance(case,['second','first'],collars_mm={'a':4})['status']=='UNKNOWN'
    case=junction_case()
    case['edges'][0]['centerline_mm'].insert(1,[10,0,0])
    case['edges'][0]['radii_mm'].insert(1,1)
    assert screen_junction_clearance(case,['first','second'],collars_mm={'a':4})['status']=='PASS'


def test_junction_collars_cannot_hide_an_entire_short_edge():
    report=screen_junction_clearance(junction_case(),['first','second'],collars_mm={'a':21})
    assert report['status']=='UNKNOWN'
    assert report['collar_consumed_edge_pairs']==[['first','second']]


def test_missing_collar_and_budget_fail_closed():
    with pytest.raises(ValueError,match='explicit collar'):
        screen_junction_clearance(junction_case(),['first','second'],collars_mm={})
    report=screen_junction_clearance(junction_case(),['first','second'],collars_mm={'a':4},max_segment_pairs=1)
    assert report['status']=='UNKNOWN' and report['reason']=='pair_budget_exhausted'


def test_valid_junction_surface_records_collar_policy():
    vertices, faces, metadata=build_case_surface(junction_case(),['first','second'],spacing_mm=.3)
    assert len(vertices)>0 and len(faces)>0
    report=metadata['junction_clearance_screen']
    assert report['status']=='PASS' and report['collars_mm']['a']==pytest.approx(3.6)
    assert metadata['checks']['watertight']=='PASS'
    assert report['inside_junction_collars']=='NOT CHECKED'


def self_case(points):
    case=crossing()
    case['nodes']={key:{'kind':'scope_boundary','evidence_status':'synthetic_estimate','position_mm':p}
                   for key,p in [('a',points[0]),('b',points[-1])]}
    case['edges']=case['edges'][:1]
    case['edges'][0].update(centerline_mm=points,radii_mm=[1]*len(points))
    return case


@pytest.mark.parametrize('points',[
    [[0,0,0],[20,0,0],[20,10,0],[10,-10,0]],
    [[0,0,0],[20,0,0],[2,0,0]],  # adjacent sparse intervals double back
    [[0,0,0],[20,0,0],[20,1,0],[0,1,0]],  # nearby parallel body return
])
def test_self_recontact_is_blocked_including_adjacent_coarse_intervals(points):
    case=self_case(points)
    report=screen_self_clearance(case,['first'],local_windows_mm={'first':4})
    assert report['status']=='UNKNOWN' and report['potential_contacts']
    with pytest.raises(ValueError,match='within-vessel'):
        build_case_surface(case,['first'],spacing_mm=.3)


def test_dense_straight_path_does_not_fail_on_neighbor_capsules():
    case=self_case([[float(i),0,0] for i in range(21)])
    report=screen_self_clearance(case,['first'],local_windows_mm={'first':4})
    assert report['status']=='PASS' and report['locally_exempt_segment_pairs']>0
    assert report['checked_segment_pairs']>0 and report['local_folding']=='NOT CHECKED'
    reversed_case=self_case(list(reversed(case['edges'][0]['centerline_mm'])))
    assert screen_self_clearance(reversed_case,['first'],local_windows_mm={'first':4})['status']=='PASS'


def test_self_screen_sampling_orientation_and_3d_separation():
    points=[[0,0,0],[20,0,0],[20,10,0],[10,-10,0]]
    for p in [points,list(reversed(points)),[[0,0,0],[10,0,0],*points[1:]]]:
        assert screen_self_clearance(self_case(p),['first'],local_windows_mm={'first':4})['status']=='UNKNOWN'
    raised=[[0,0,0],[20,0,0],[20,10,8],[10,-10,8]]
    # Lifting the crossing does not resolve the acute fold in intervals 1/2.
    folded=screen_self_clearance(self_case(raised),['first'],local_windows_mm={'first':4})
    assert folded['status']=='UNKNOWN' and folded['potential_contacts'][0]['intervals']==[1,2]
    assert folded['potential_contacts'][0]['clearance_lower_bound_mm']==pytest.approx(-.4467589904)
    separated=[[0,0,0],[20,0,0],[20,10,0],[20,10,8],[10,10,8],[10,-10,8]]
    assert screen_self_clearance(self_case(separated),['first'],local_windows_mm={'first':4})['status']=='PASS'


def test_self_screen_budget_and_invalid_window():
    case=self_case([[float(i),0,0] for i in range(21)])
    report=screen_self_clearance(case,['first'],local_windows_mm={'first':4},max_segment_pairs=1)
    assert report['status']=='UNKNOWN' and report['reason']=='pair_budget_exhausted'
    for value in [True,float('nan'),-1,2]:
        with pytest.raises(ValueError,match='local window'):
            screen_self_clearance(case,['first'],local_windows_mm={'first':value})
