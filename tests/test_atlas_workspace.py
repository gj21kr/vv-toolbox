import copy
import json
from types import SimpleNamespace
import numpy as np
import pytest
from test_venous_backend import workspace


def test_atlas_modification_is_absolute_exportable_and_resettable(workspace,monkeypatch):
    work,_=workspace
    points=np.column_stack([np.linspace(0,40,41),3*np.sin(np.linspace(0,np.pi,41)),np.zeros(41)])
    v=np.concatenate([points+[0,0,1],points-[0,0,1]])
    part=dict(id='a',name='a',layer='arterial',vertices=v,faces=np.array([[0,1,41]]))
    work.atlas=SimpleNamespace(meshes=[part])
    work.server.get_clients=lambda:{}
    edge=dict(id='e',part_id='a',layer='arterial',start='s',end='t',points=points.tolist(),radii=np.ones(41).tolist())
    work.atlas_centerlines=dict(edges=[edge],nodes=[dict(id='s',part_id='a',kind='terminal',point=points[0].tolist()),dict(id='t',part_id='a',kind='terminal',point=points[-1].tolist())],links=[],summary={})
    work.atlas_original_centerlines=copy.deepcopy(work.atlas_centerlines)
    work.set_source('atlas')
    # The fake renderer does not store line points; geometry is checked directly.
    monkeypatch.setattr(work,'select_atlas_part',lambda pid:None)
    request=dict(part_id='a',radius_scale=1.3,tortuosity=.4,torsion_deg=45.)
    work.modify_atlas_part(request)
    modified=work.atlas_modified_parts['a']['vertices'].copy()
    assert not np.allclose(modified,v)
    np.testing.assert_array_equal(part['vertices'],v)
    work.modify_atlas_part(request)
    np.testing.assert_array_equal(work.atlas_modified_parts['a']['vertices'],modified)
    bundle=json.loads(work.export_bundle())
    assert bundle['edit_checks']['a']['checks']['endpoint_positions_and_radii']=='PASS'
    assert bundle['edit_checks']['a']['self_intersection']=='PASS'
    assert bundle['edit_checks']['a']['self_contact_screen']['status']=='NO_CONTACT_DETECTED'
    status=work.snapshot()
    assert status['atlas_edit_checks']['a']==bundle['edit_checks']['a']
    status['atlas_edit_checks']['a']['checks']['positive_radii']='FAIL'
    assert work.snapshot()['atlas_edit_checks']['a']['checks']['positive_radii']=='PASS'
    assert bundle['modifications']['a']['radius_scale']==1.3
    assert 'a' in bundle['modified_surfaces']
    work.modify_atlas_part(dict(part_id='a',radius_scale=1.,tortuosity=0.,torsion_deg=0.))
    assert not work.atlas_modifications and not work.atlas_modified_parts
    np.testing.assert_array_equal(work.atlas_centerlines['edges'][0]['points'],points)


def test_available_atlas_is_default_editing_workspace(workspace,monkeypatch):
    from vv_toolbox import app,atlas,atlas_neck,reference
    from test_venous_backend import server_fixture
    monkeypatch.setattr(atlas,'load_atlas',lambda:SimpleNamespace(metadata={},meshes=[]))
    monkeypatch.setattr(reference,'load_reference',lambda:(_ for _ in ()).throw(ValueError('No reference')))
    monkeypatch.setattr(atlas_neck,'build_neck_repairs',lambda atlas:([],{}))
    work=app.Workspace(server_fixture())
    assert work.source=='atlas'
    assert work.atlas_info['available']
    assert work.snapshot()['layers']['arterial']['edges']==[]
    assert work.graph is not None  # Legacy parameters are retained internally.


def test_atlas_retains_original_coordinates_without_synthetic_overlay(workspace):
    work,_=workspace
    vertices=np.array([[100.,20.,30.],[102.,20.,30.],[100.,22.,30.]])
    work.atlas=SimpleNamespace(meshes=[dict(id='fixture',name='Fixture',layer='arterial',
        vertices=vertices,faces=np.array([[0,1,2]]))])
    work.atlas_info=dict(available=True,title='Fixture atlas')
    work.server.get_clients=lambda:{}
    original=copy.deepcopy(work.parameters)
    work.server.scene.calls.clear()
    work.set_source('atlas')
    assert [name for name,_ in work.server.scene.calls]==['/atlas/fixture']
    assert all(not layer['edges'] for layer in work.snapshot()['layers'].values())
    assert work.snapshot()['clearance'] is None
    assert json.loads(work.export_bundle())['schema']=='vv-toolbox.atlas-workspace/1'
    np.testing.assert_array_equal(work.atlas.meshes[0]['vertices'],vertices)
    work.set_source('schematic')
    assert work.parameters==original
    assert work.snapshot()['layers']['arterial']['edges']


def test_missing_atlas_cannot_be_selected(workspace):
    work,_=workspace
    with pytest.raises(ValueError):
        work.set_source('atlas')
    assert work.source=='schematic'


def test_atlas_selection_focus_preserves_geometry_and_parameters(workspace):
    work,_=workspace
    v=np.array([[100.,20.,1300.],[102.,20.,1320.],[100.,22.,1300.]])
    parts=[dict(id=name,name=name,layer='arterial',vertices=v.copy(),faces=np.array([[0,1,2]])) for name in ('a','b')]
    work.atlas=SimpleNamespace(meshes=parts)
    camera=SimpleNamespace(position=None,look_at=None)
    work.server.get_clients=lambda:{1:SimpleNamespace(camera=camera)}
    work.set_source('atlas')
    parameters=copy.deepcopy(work.parameters)
    work.select_atlas_part('a')
    assert work.snapshot()['atlas_selection']=='a'
    assert work.atlas_part_handles['a'].color==(255,222,125)
    work.select_atlas_part('b')
    assert work.atlas_part_handles['a'].color==(230,76,83)
    np.testing.assert_allclose(camera.look_at,(v.min(0)+v.max(0))/2000)
    assert work.parameters==parameters
    np.testing.assert_array_equal(parts[0]['vertices'],v)
    with pytest.raises(ValueError):work.select_atlas_part('unknown')


def test_estimated_neck_parts_remain_distinct_and_respect_visibility(workspace):
    work,_=workspace
    v=np.array([[0.,0.,0.],[1.,0.,0.],[0.,1.,0.]])
    part=dict(id='source',name='Source',layer='arterial',vertices=v,faces=np.array([[0,1,2]]))
    work.atlas=SimpleNamespace(meshes=[part])
    work.neck_parts=[dict(part,id='estimated')]
    work.neck_info=dict(available=True,parts=[dict(id='estimated',kind='estimated')])
    work.server.get_clients=lambda:{}
    work.neck_repairs_visible=False
    work.set_source('atlas')
    work.set_visibility(dict(arterial=True,systemic_venous=True,hepatic_portal=True))
    assert all(not h.visible for h in work.neck_handles['arterial'])
    assert all(h.visible for h in work.layer_handles['arterial'])
    assert json.loads(work.export_bundle())['neck_repairs']==work.neck_info


def test_atlas_centerlines_toggle_with_layer_and_export_without_candidate_geometry(workspace):
    work,_=workspace
    v=np.array([[0.,0.,0.],[1.,0.,0.],[0.,1.,0.]])
    work.atlas=SimpleNamespace(meshes=[dict(id='a',name='a',layer='arterial',vertices=v,faces=np.array([[0,1,2]]))])
    work.server.get_clients=lambda:{}
    work.atlas_centerlines=dict(edges=[dict(part_id='a',layer='arterial',points=[[0,0,0],[0,0,1]])],links=[dict(status='candidate')])
    work.set_source('atlas')
    handle=work.atlas_centerline_handles['a']
    assert handle.visible
    assert work.atlas_part_handles['a'].opacity==.25
    assert len([name for name,_ in work.server.scene.calls if name.startswith('/atlas-centerlines/')])==1
    work.set_visibility(dict(arterial=False,systemic_venous=True,hepatic_portal=True))
    assert not handle.visible
    work.atlas_centerlines_visible=False;work.update_atlas_centerline_visibility()
    assert work.atlas_part_handles['a'].opacity==1.
    assert json.loads(work.export_bundle())['centerlines']==work.atlas_centerlines
