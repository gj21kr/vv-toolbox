from contextlib import nullcontext
from copy import deepcopy
import hashlib
import json
import threading
from types import SimpleNamespace

import numpy as np
import pytest

from vv_toolbox.atlas_edit_session import AtlasEditSession, AtlasEditConflict, regenerate, source_identity
from vv_toolbox.atlas_modification import deform_part
from vv_toolbox.case_io import _encode
from vv_toolbox.model import tube_mesh


@pytest.fixture
def source():
    t = np.linspace(0, 1, 101)
    points = np.column_stack((40*t, 6*np.sin(np.pi*t), 0*t))
    vertices, faces = tube_mesh(points, 1, sides=16)
    part = dict(id='test', name='test artery', layer='arterial', vertices=vertices, faces=faces)
    edge = dict(id='edge', part_id='test', layer='arterial', start='a', end='b', points=points.tolist(), radii=np.ones(101).tolist())
    original = dict(edges=[edge], nodes=[dict(id=k, part_id='test', kind='terminal', point=points[i].tolist(), radius=1) for k,i in [('a',0),('b',-1)]], summary={})
    return [part], original, dict(radius_scale=1.3,tortuosity=.3,torsion_deg=35.)


def test_parameter_snapshot_regenerates_identical_geometry(tmp_path, source):
    parts, original, params = source
    original_copy = deepcopy(original)
    identity = source_identity({'sha256':'a'*64}, original, parts)
    store = AtlasEditSession(tmp_path/'edits.json')
    revision = store.save(identity, {'test':params})
    modifications, loaded_revision = store.read(identity)
    assert loaded_revision == revision
    graph, surfaces, normalized = regenerate(parts, original, modifications)
    expected_part, expected_edges = deform_part(parts[0],original['edges'],params)
    np.testing.assert_array_equal(surfaces['test']['vertices'], expected_part['vertices'])
    assert graph['edges'] == expected_edges
    assert normalized == modifications and original == original_copy
    assert 'vertices' not in json.loads(store.path.read_text())['payload']


def test_cas_prevents_stale_and_missing_file_overwrites(tmp_path, source):
    parts, original, params = source
    identity = source_identity({'sha256':'a'*64}, original, parts)
    first, second = AtlasEditSession(tmp_path/'edits.json'), AtlasEditSession(tmp_path/'edits.json')
    first.save(identity, {'test':params})
    with pytest.raises(AtlasEditConflict):second.save(identity, {})
    _,second.revision = second.read(identity)
    second.save(identity,{})
    before=first.path.read_bytes()
    with pytest.raises(AtlasEditConflict):first.save(identity,{'test':params})
    assert first.path.read_bytes()==before
    first.path.unlink()
    with pytest.raises(AtlasEditConflict):first.save(identity,{})


@pytest.mark.parametrize('change', ['source','generator','parameters','digest','duplicate'])
def test_invalid_saved_document_rejected_and_preserved(tmp_path, source, change):
    parts, original, params=source
    identity=source_identity({'sha256':'a'*64}, original, parts)
    store=AtlasEditSession(tmp_path/'edits.json')
    store.save(identity,{'test':params})
    value=json.loads(store.path.read_text())
    if change=='source':value['payload']['source']['archive_sha256']='b'*64
    elif change=='generator':value['payload']['generator']='future-version'
    elif change=='parameters':value['payload']['modifications']['test']['radius_scale']=True
    if change!='digest':value['revision']=hashlib.sha256(_encode(value['payload'])).hexdigest()
    else:value['revision']='c'*64
    text=json.dumps(value)
    if change=='duplicate':text=text.replace('"schema":', '"schema":"duplicate", "schema":',1)
    store.path.write_text(text)
    with pytest.raises(ValueError):store.read(identity)
    with pytest.raises(ValueError):store.save(identity,{})
    assert store.path.read_text()==text


def make_workspace(tmp_path, source):
    from vv_toolbox.app import Workspace
    parts, original, params=source
    ws=Workspace.__new__(Workspace)
    ws.lock=threading.RLock()
    ws.server=SimpleNamespace(atomic=nullcontext)
    ws.source='atlas';ws.busy=False;ws.generation=5
    ws.graph=None;ws.metrics=SimpleNamespace(content='original legend')
    ws.atlas=SimpleNamespace(meshes=parts, metadata={'sha256':'a'*64})
    ws.neck_parts=[];ws.atlas_original_centerlines=original
    ws.atlas_centerlines=deepcopy(original);ws.atlas_centerline_status={'summary':{}}
    ws.atlas_modifications={};ws.atlas_modified_parts={}
    ws.atlas_selection='test';ws.visibility={'arterial':False}
    ws._atlas_edit_identity_cache=None
    ws.atlas_edit_session=AtlasEditSession(tmp_path/'edits.json')
    points=np.asarray(original['edges'][0]['points'],dtype=np.float32)/1000
    ws.atlas_part_handles={'test':SimpleNamespace(vertices=parts[0]['vertices']/1000)}
    ws.atlas_centerline_handles={'test':SimpleNamespace(points=np.stack([points[:-1],points[1:]],axis=1))}
    return ws


def test_workspace_reload_restores_edits_and_default_without_changing_view(tmp_path,source):
    ws=make_workspace(tmp_path,source)
    params=source[2]
    ws.atlas_modifications={'test':params}
    ws.atlas_modified_parts={'test':deform_part(source[0][0],source[1]['edges'],params)[0]}
    status=ws.update_atlas_edit_session({'action':'save','expected_generation':5})
    assert not status['dirty'] and status['modified_parts']==1 and status['generation']==5
    ws.atlas_modifications={}
    result=ws.update_atlas_edit_session({'action':'reload','expected_generation':5})
    assert result['generation']==6 and ws.atlas_modifications=={'test':params}
    assert '1 modified vessel(s)' in ws.metrics.content
    expected,_=deform_part(source[0][0],source[1]['edges'],params)
    np.testing.assert_array_equal(ws.atlas_part_handles['test'].vertices,expected['vertices']/1000)
    assert ws.visibility=={'arterial':False} and ws.atlas_selection=='test'
    ws.atlas_edit_session.save(ws.atlas_edit_identity(),{})
    ws.update_atlas_edit_session({'action':'reload','expected_generation':6})
    assert ws.atlas_modifications=={} and ws.atlas_modified_parts=={}
    assert '0 modified vessel(s)' in ws.metrics.content
    np.testing.assert_array_equal(ws.atlas_part_handles['test'].vertices,source[0][0]['vertices']/1000)


def test_regeneration_failure_does_not_publish(tmp_path,source):
    ws=make_workspace(tmp_path,source)
    ws.atlas_edit_session.save(ws.atlas_edit_identity(),{'missing':source[2]})
    old_graph=ws.atlas_centerlines
    with pytest.raises(ValueError,match='Unknown atlas vessel'):
        ws.update_atlas_edit_session({'action':'reload','expected_generation':5})
    assert ws.atlas_centerlines is old_graph and ws.generation==5 and not ws.atlas_modifications


def test_scene_failure_rolls_back_prior_geometry_and_data(tmp_path,source):
    ws=make_workspace(tmp_path,source)
    ws.atlas_edit_session.save(ws.atlas_edit_identity(),{'test':source[2]})
    old_points=ws.atlas_centerline_handles['test'].points.copy()
    class FailOnce:
        def __init__(self):self._points=old_points;self.fail=True
        @property
        def points(self):return self._points
        @points.setter
        def points(self,value):
            if self.fail:
                self.fail=False
                raise RuntimeError('scene failure')
            self._points=value
    ws.atlas_centerline_handles['test']=FailOnce()
    before=ws.atlas_part_handles['test'].vertices.copy()
    old_graph=ws.atlas_centerlines
    with pytest.raises(RuntimeError):ws.update_atlas_edit_session({'action':'reload','expected_generation':5})
    np.testing.assert_array_equal(ws.atlas_part_handles['test'].vertices,before)
    np.testing.assert_array_equal(ws.atlas_centerline_handles['test'].points,old_points)
    assert ws.generation==5 and ws.atlas_centerlines is old_graph and not ws.atlas_modifications


@pytest.mark.parametrize('generation',[4,True,'5',None])
def test_stale_or_invalid_generation_rejected(tmp_path,source,generation):
    ws=make_workspace(tmp_path,source)
    with pytest.raises(AtlasEditConflict):ws.update_atlas_edit_session({'action':'save','expected_generation':generation})
    assert not ws.atlas_edit_session.path.exists()


def test_failed_self_contact_save_preserves_snapshot_bytes(tmp_path,source):
    from vv_toolbox.atlas_edit_checks import AtlasEditCheckFailure
    ws=make_workspace(tmp_path,source)
    ws.atlas_edit_session.save(ws.atlas_edit_identity(),{})
    before=ws.atlas_edit_session.path.read_bytes()
    ws.atlas_modifications={'test':source[2]}
    ws.atlas_modified_parts={'test':dict(
        vertices=np.array([[-1.,-1,0],[1,-1,0],[0,1,0],[0,-.5,-1],[0,-.5,1],[0,.5,0]]),
        faces=np.array([[0,1,2],[3,4,5]]))}
    with pytest.raises(AtlasEditCheckFailure,match='FAIL'):
        ws.update_atlas_edit_session({'action':'save','expected_generation':5})
    assert ws.atlas_edit_session.path.read_bytes()==before


@pytest.mark.parametrize('operation',['modify','reload'])
def test_self_contact_rejection_precedes_scene_mutation(tmp_path,source,monkeypatch,operation):
    import vv_toolbox.atlas_modification as modification
    import vv_toolbox.atlas_edit_session as sessions
    from vv_toolbox.atlas_edit_checks import AtlasEditCheckFailure
    ws=make_workspace(tmp_path,source)
    ws.atlas_edit_session.save(ws.atlas_edit_identity(),{'test':source[2]})
    before=ws.atlas_edit_session.path.read_bytes()
    graph=ws.atlas_centerlines
    def bad_deformation(*args,**kwargs):
        part=deepcopy(source[0][0])
        part['vertices']=np.array([[-1.,-1,0],[1,-1,0],[0,1,0],[0,-.5,-1],[0,-.5,1],[0,.5,0]])
        part['faces']=np.array([[0,1,2],[3,4,5]])
        return part,deepcopy(source[1]['edges'])
    monkeypatch.setattr(modification,'deform_part',bad_deformation)
    monkeypatch.setattr(sessions,'deform_part',bad_deformation)
    with pytest.raises(AtlasEditCheckFailure,match='FAIL'):
        if operation=='modify':
            ws.modify_atlas_part(dict(part_id='test',**source[2]))
        else:
            ws.update_atlas_edit_session({'action':'reload','expected_generation':5})
    assert ws.atlas_centerlines is graph and ws.generation==5
    assert ws.atlas_modifications=={} and ws.atlas_modified_parts=={}
    assert ws.atlas_edit_session.path.read_bytes()==before


@pytest.mark.parametrize('failure_stage',['draw','selection'])
def test_modification_render_failure_restores_saveable_state(tmp_path,source,monkeypatch,failure_stage):
    ws=make_workspace(tmp_path,source)
    old_graph=ws.atlas_centerlines
    old_modifications=ws.atlas_modifications
    old_surfaces=ws.atlas_modified_parts
    draws=[]
    failed=False
    def draw():
        nonlocal failed
        draws.append(dict(ws.atlas_modifications))
        if failure_stage=='draw' and not failed:
            failed=True
            raise RuntimeError('render failed')
    def select(pid):
        nonlocal failed
        if failure_stage=='selection' and not failed:
            failed=True
            raise RuntimeError('selection failed')
    monkeypatch.setattr(ws,'draw_atlas',draw)
    monkeypatch.setattr(ws,'select_atlas_part',select)
    with pytest.raises(RuntimeError,match='failed'):
        ws.modify_atlas_part(dict(part_id='test',**source[2]))
    assert ws.generation==5 and ws.atlas_centerlines is old_graph
    assert ws.atlas_modifications is old_modifications
    assert ws.atlas_modified_parts is old_surfaces
    assert draws[0]=={'test':source[2]} and draws[-1]=={}
    assert ws.metrics.content=='original legend'
    ws.update_atlas_edit_session({'action':'save','expected_generation':5})
    saved,_=ws.atlas_edit_session.read(ws.atlas_edit_identity())
    assert saved=={}


@pytest.mark.parametrize('operation',['modify','reload'])
def test_failed_recovery_blocks_further_edits_and_preserves_saved_file(tmp_path,source,monkeypatch,operation):
    ws=make_workspace(tmp_path,source)
    ws.atlas_edit_session.save(ws.atlas_edit_identity(),{'test':source[2]})
    saved=ws.atlas_edit_session.path.read_bytes()
    if operation=='modify':
        def broken_draw():
            raise RuntimeError('persistent renderer failure')
        monkeypatch.setattr(ws,'draw_atlas',broken_draw)
        with pytest.raises(RuntimeError,match='restart the demo server'):
            ws.modify_atlas_part(dict(part_id='test',**source[2]))
    else:
        class BrokenHandle:
            @property
            def points(self):return np.zeros((1,2,3))
            @points.setter
            def points(self,value):raise RuntimeError('persistent renderer failure')
        ws.atlas_centerline_handles['test']=BrokenHandle()
        with pytest.raises(RuntimeError,match='restart the demo server'):
            ws.update_atlas_edit_session({'action':'reload','expected_generation':5})
    status=ws.atlas_edit_status()
    assert not status['available']
    assert 'restart the demo server' in status['error']
    # Clearing the ordinary UI error must not clear the persistent recovery gate.
    ws.error=None
    for action in ('save','reload'):
        with pytest.raises(AtlasEditConflict,match='restart the demo server'):
            ws.update_atlas_edit_session({'action':action,'expected_generation':5})
    with pytest.raises(AtlasEditConflict,match='restart the demo server'):
        ws.modify_atlas_part(dict(part_id='test',**source[2]))
    assert ws.atlas_edit_session.path.read_bytes()==saved
    assert ws.generation==5 and not ws.atlas_modifications


def test_cli_passes_separate_edit_snapshot_without_loading_default(tmp_path,monkeypatch):
    import sys
    from vv_toolbox import app
    path=tmp_path/'separate-edits.json'
    calls=[]
    stopped=[]
    def serve(port,*,atlas_edit_session_path):
        calls.append((port,atlas_edit_session_path))
        return SimpleNamespace(stop=lambda:stopped.append(True))
    def stop_loop(seconds):raise KeyboardInterrupt
    monkeypatch.setattr(app,'serve',serve)
    monkeypatch.setattr(app.time,'sleep',stop_loop)
    monkeypatch.setattr(sys,'argv',['vv-toolbox.app','--port','8093','--atlas-edit-session',str(path)])
    app.main()
    assert calls==[(8093,path)] and stopped==[True]
    assert not path.exists()


def test_failed_basic_geometry_check_cannot_publish_or_reload(tmp_path,source,monkeypatch):
    from vv_toolbox import atlas_modification
    ws=make_workspace(tmp_path,source)
    original_graph=ws.atlas_centerlines
    ws.atlas_edit_session.save(ws.atlas_edit_identity(),{'test':source[2]})
    saved=ws.atlas_edit_session.path.read_bytes()
    monkeypatch.setattr(atlas_modification,'inspect_edit',lambda *args:dict(
        basic_invariants='FAIL',checks={'no_new_degenerate_triangles':'FAIL'}))
    with pytest.raises(ValueError,match='no_new_degenerate_triangles'):
        ws.modify_atlas_part(dict(part_id='test',**source[2]))
    with pytest.raises(ValueError,match='no_new_degenerate_triangles'):
        ws.update_atlas_edit_session({'action':'reload','expected_generation':5})
    assert ws.atlas_centerlines is original_graph
    assert ws.generation==5 and not ws.atlas_modifications
    assert ws.atlas_edit_session.path.read_bytes()==saved
