from copy import deepcopy

import pytest

from test_case_surface import example
from test_union_radius import fixture
from vv_toolbox.case_source_surfaces import attach_surfaces
from vv_toolbox.case_io import case_digest
from vv_toolbox.registered_shape_edit import deform_registered_source


def sample():
    case = example(); mesh, lineage = fixture()
    case['nodes']['b']['position_mm'] = [0,0,4]
    case['edges'][0].update(centerline_mm=[[0,0,0],[0,0,2],[0,0,4]], radii_mm=[1,1,1], source_part_id='middle')
    case = attach_surfaces(case, [dict(part_id='union', edge_ids=['e'], frame_id='fixture',
        provenance='source', source_ids=['s'], vertices_mm=mesh.vertices.tolist(), faces=mesh.faces.tolist(),
        face_lineage=lineage)])
    case['inspection'] = {'prior': {'status':'PASS'}}
    case['geometry_quality'] = {'status':'PASS'}
    return case


def edit(case, **kwargs):
    parameters = dict(bend_mm=.1, bend_direction=[1,0,0], twist_deg=5., collar_mm=.1,
                      transition_mm=1., max_displacement_mm=.5)
    parameters.update(kwargs)
    return deform_registered_source(case, edge_id='e', **parameters)


def test_registered_shape_updates_surface_graph_and_preserves_parent():
    case = sample(); before = deepcopy(case)
    result = edit(case)
    assert case == before
    assert result['nodes'] == case['nodes']
    assert result['edges'][0]['centerline_mm'] != case['edges'][0]['centerline_mm']
    assert result['surface_parts'][0]['vertices_mm'] != case['surface_parts'][0]['vertices_mm']
    assert result['surface_parts'][0]['faces'] == case['surface_parts'][0]['faces']
    assert result['surface_parts'][0]['provenance'] == 'estimated'
    report = result['inspection']['registered_shape_edit']
    assert report['parent_inspection'] == case['inspection']
    assert 'geometry_quality' not in result
    assert report['parent_geometry_metadata']['geometry_quality'] == case['geometry_quality']
    assert report['accepted_for_generation'] is False
    assert report['neighboring_vessels'] == 'NOT RUN'
    assert report['checked_paths'][0]['containment']['status'] == 'PASS'
    assert case_digest(result) == case_digest(edit(case))


def test_integer_and_float_shape_controls_have_same_revision():
    case=sample()
    a=edit(case, twist_deg=0,transition_mm=1,max_displacement_mm=1,collar_mm=0)
    b=edit(case, twist_deg=0.,transition_mm=1.,max_displacement_mm=1.,collar_mm=0.)
    assert case_digest(a)==case_digest(b)


@pytest.mark.parametrize('damage', ['ownership','lineage','displacement'])
def test_unsupported_or_excessive_change_keeps_source(damage):
    case = sample()
    if damage == 'ownership': case['edges'][0].pop('source_part_id')
    if damage == 'lineage': case['surface_parts'][0].pop('face_lineage')
    before = deepcopy(case)
    with pytest.raises(ValueError):
        edit(case, bend_mm=5 if damage=='displacement' else .1)
    assert case == before


def test_other_bound_path_must_also_pass(monkeypatch):
    case = sample()
    other = deepcopy(case['edges'][0]); other.update(id='other', source_part_id='rest')
    case['edges'].append(other)
    part = case.pop('surface_parts')[0]; part['edge_ids'].append('other')
    case = attach_surfaces(case, [part]); before = deepcopy(case)
    monkeypatch.setattr('vv_toolbox.registered_shape_edit.inspect_centerline_containment',
                        lambda *a, **k: {'status':'UNKNOWN'})
    with pytest.raises(ValueError, match='Affected surface graph containment'):
        edit(case)
    assert case == before


def test_workbench_shape_action_and_explicit_parameter_contract():
    from vv_toolbox.label_workbench import process_request
    case=sample()
    req=dict(action='shape', snapshot=dict(schema='vv-toolbox.case-snapshot/1',
        revision=case_digest(case),case=case), parameters=dict(edge_id='e',bend_mm=.1,
        bend_direction=[1,0,0],twist_deg=0.,collar_mm=.1,transition_mm=1.,max_displacement_mm=.5))
    response=process_request(req)
    assert response['snapshot']['case']['inspection']['registered_shape_edit']['accepted_for_generation'] is False
    req['parameters']['protected_points_mm']=[]
    with pytest.raises(ValueError, match='Explicit registered shape parameters'):
        process_request(req)


def split_sample(reverse=False):
    case=sample();part=case.pop('surface_parts')[0]
    case['nodes']['mid']=dict(kind='unresolved',evidence_status='unresolved',position_mm=[0,0,2])
    first=case['edges'][0]
    second=deepcopy(first)
    first.update(end='mid',centerline_mm=[[0,0,0],[0,0,1],[0,0,2]])
    second.update(id='e2',start='mid',end='b',centerline_mm=[[0,0,2],[0,0,3],[0,0,4]])
    if reverse:
        second.update(start='b',end='mid',centerline_mm=second['centerline_mm'][::-1])
    case['edges'].append(second);part['edge_ids']=['e','e2']
    return attach_surfaces(case,[part])


@pytest.mark.parametrize('reverse',[False,True])
def test_split_source_has_one_field_fixed_junction_and_preserved_labels(reverse):
    case=split_sample(reverse);before=deepcopy(case)
    result=edit(case,twist_deg=0.)
    assert case==before and result['nodes']==case['nodes']
    for original,changed in zip(case['edges'],result['edges']):
        assert changed['centerline_mm'][0]==original['centerline_mm'][0]
        assert changed['centerline_mm'][-1]==original['centerline_mm'][-1]
        assert changed['centerline_mm'][1]!=original['centerline_mm'][1]
        assert changed['anatomy']==original['anatomy']
        assert changed['radii_mm']==original['radii_mm']
    audit=result['inspection']['registered_shape_edit']
    assert audit['audit']['affected_edge_ids']==['e','e2']
    assert len(audit['checked_paths'])==2
    assert all(row['containment']['status']=='PASS' for row in audit['checked_paths'])
    assert audit['accepted_for_generation'] is False


def test_split_source_missing_junction_position_is_rejected():
    case=split_sample();case['nodes']['mid']['position_mm']=None
    with pytest.raises(ValueError,match='exact junction coordinates'):edit(case)


def test_split_source_refuses_branch_and_disconnected_topology():
    from vv_toolbox.registered_shape_edit import _source_chain
    edges=split_sample()['edges']
    branch=deepcopy(edges[1]);branch.update(id='branch',end='extra')
    with pytest.raises(ValueError,match='branch-aware'):_source_chain([*edges,branch])
    disconnected=deepcopy(edges[1]);disconnected.update(id='apart',start='x',end='y')
    with pytest.raises(ValueError):_source_chain([*edges,disconnected])


def test_workbench_exposes_whole_source_scope_and_missing_ownership_reason():
    from vv_toolbox.label_workbench import process_request
    from vv_toolbox.registered_shape_edit import source_edit_options
    case=split_sample(reverse=True)
    response=process_request(dict(action='inspect',snapshot=dict(schema='vv-toolbox.case-snapshot/1',
        revision=case_digest(case),case=case),assignments=[]))
    for edge_id in ('e','e2'):
        assert response['shape_edit_options'][edge_id]==dict(eligible=True,reason=None,affected_edge_ids=['e','e2'])
    for edge in case['edges']:edge.pop('source_part_id')
    options=source_edit_options(case)
    assert not options['e']['eligible'] and options['e']['reason']
    assert options['e']['affected_edge_ids']==[]


def test_source_chain_geometry_is_independent_of_selected_segment_and_edge_order():
    case=split_sample(reverse=True)
    first=edit(case)
    reordered=deepcopy(case);reordered['edges'].reverse()
    second=deform_registered_source(reordered,edge_id='e2',bend_mm=.1,bend_direction=[1,0,0],
        twist_deg=5.,collar_mm=.1,transition_mm=1.,max_displacement_mm=.5)
    assert first['surface_parts'][0]['vertices_mm']==second['surface_parts'][0]['vertices_mm']
    assert first['surface_parts'][0]['faces']==second['surface_parts'][0]['faces']
    assert {e['id']:e['centerline_mm'] for e in first['edges']}=={
        e['id']:e['centerline_mm'] for e in second['edges']}
