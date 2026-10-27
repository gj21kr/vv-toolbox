from contextlib import nullcontext
from copy import deepcopy
from types import SimpleNamespace

import numpy as np
import pytest

from vv_toolbox.app import Workspace, LAYER_COLORS


class Handle(SimpleNamespace):
    def remove(self):
        self.removed=True


@pytest.fixture
def workspace(monkeypatch):
    calls=[]
    def mesh(name, vertices, faces, **kwargs):
        handle=Handle(name=name,vertices=vertices,faces=faces,removed=False,**kwargs)
        calls.append(handle)
        return handle
    def lines(name, points, colors, **kwargs):
        handle=Handle(name=name,points=points,colors=colors,removed=False,**kwargs)
        calls.append(handle)
        return handle
    client=SimpleNamespace(camera=SimpleNamespace())
    server=SimpleNamespace(atomic=nullcontext,get_clients=lambda:{1:client},
        gui=SimpleNamespace(add_markdown=lambda text:SimpleNamespace(content=text)),
        scene=SimpleNamespace(add_mesh_simple=mesh,add_line_segments=lines))
    monkeypatch.setattr(Workspace,'rebuild',lambda self,p:None)
    ws=Workspace(server,load_reference_source=False)
    ws.mesh=None
    ws.busy=False
    ws.atlas=SimpleNamespace(meshes=[dict(id='original',layer='arterial',name='original',
        vertices=np.array([[0.,0.,0.],[10.,0.,0.],[0.,10.,0.]]),faces=np.array([[0,1,2]]))])
    ws.source='atlas'
    ws.atlas_selection='original'
    ws.atlas_modifications={'original':{'radius_scale':1.2}}
    ws.atlas_modified_parts={'original':dict(ws.atlas.meshes[0],vertices=ws.atlas.meshes[0]['vertices']*2)}
    ws.draw_atlas()
    candidate=dict(summary=dict(id='test',title='Test',scope='two paths',pair_surface_separation='PASS',read_only=True),
        vertices_mm=np.array([[0.,0.,0.],[100.,0.,0.],[0.,100.,0.]]),faces=np.array([[0,1,2]]),
        edges=[dict(id=str(i),points=[[0.,0.,0.],[100.,i+1.,0.]]) for i in range(2)])
    monkeypatch.setattr('vv_toolbox.candidate_preview.load_candidate_preview',lambda root,cid:deepcopy(candidate))
    return ws,calls,candidate


def test_candidate_surface_scale_visibility_and_read_only(workspace):
    ws,calls,candidate=workspace
    previous=ws.handles[0]
    ws.set_source('candidate')
    assert previous.removed and len(ws.handles)==1
    np.testing.assert_array_equal(ws.handles[0].vertices,candidate['vertices_mm']/1000)
    assert ws.handles[0].color==LAYER_COLORS['arterial']
    assert ws.snapshot()['candidate']==candidate['summary']
    assert ws.snapshot()['edges']==[]
    with pytest.raises(ValueError,match='read-only'):ws.export_bundle()
    with pytest.raises(ValueError):ws.modify_atlas_part({})
    ws.set_visibility(dict(arterial=False,systemic_venous=True,hepatic_portal=True))
    assert not ws.handles[0].visible
    assert np.isfinite(ws.server.get_clients()[1].camera.position).all()


def test_candidate_centerlines_only_selected_paths_and_return_preserves_atlas(workspace):
    ws,calls,candidate=workspace
    modifications=deepcopy(ws.atlas_modifications)
    ws.set_source('candidate')
    ws.mode='Centerlines'
    ws.draw(None,None)
    assert ws.snapshot()['mode']=='Centerlines'
    assert ws.snapshot()['access']==ws.access and ws.snapshot()['target']==ws.target
    assert len(ws.handles)==2
    for handle,edge in zip(ws.handles,candidate['edges']):
        np.testing.assert_allclose(handle.points[0],np.array(edge['points'])/1000)
    candidate_handles=list(ws.handles)
    ws.set_source('atlas')
    assert all(h.removed for h in candidate_handles)
    assert ws.atlas_selection=='original' and ws.atlas_modifications==modifications
    assert ws.atlas_part_handles['original'].color==(255,222,125)
    np.testing.assert_array_equal(ws.atlas_part_handles['original'].vertices,ws.atlas_modified_parts['original']['vertices']/1000)


def test_failed_candidate_load_preserves_active_scene(workspace,monkeypatch):
    ws,calls,_=workspace
    original_handles=list(ws.handles)
    before=ws.generation
    def invalid(*args):raise ValueError('hash mismatch')
    monkeypatch.setattr('vv_toolbox.candidate_preview.load_candidate_preview',invalid)
    with pytest.raises(ValueError,match='validation failed'):ws.set_source('candidate')
    assert ws.source=='atlas' and ws.generation==before and ws.candidate is None
    assert ws.handles==original_handles and not any(h.removed for h in original_handles)


def test_mca_selection_uses_case_centerlines_and_context_description(workspace,monkeypatch):
    ws,calls,candidate=workspace
    candidate['summary'].update(id='right-mca-saccular',context_inspection=dict(
        status='REVIEW_REQUIRED',separated_count=7,context_edge_count=8))
    for edge in candidate['edges']:
        edge['centerline_mm']=edge.pop('points')
    requested=[]
    def load(root,cid):
        requested.append(cid)
        return deepcopy(candidate)
    monkeypatch.setattr('vv_toolbox.candidate_preview.load_candidate_preview',load)
    ws.set_source('candidate',candidate_id='right-mca-saccular')
    assert requested==['right-mca-saccular']
    assert 'REVIEW_REQUIRED' in ws.metrics.content
    ws.mode='Centerlines'
    ws.draw(None,None)
    assert len(ws.handles)==2
    np.testing.assert_allclose(ws.handles[0].points[0],
                              np.array(candidate['edges'][0]['centerline_mm'])/1000)
