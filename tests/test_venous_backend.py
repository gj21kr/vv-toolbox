"""Backend circulation separation without expensive mesh fixtures or live servers."""
import copy
import json
from contextlib import nullcontext
from types import SimpleNamespace

import numpy as np
import pytest

from vv_toolbox import app, generate
from vv_toolbox.veins import generate_veins


class Handle:
    def __init__(self):
        self.visible=True
        self.removed=False
    def remove(self):
        self.removed=True


class Scene:
    def __init__(self):
        self.calls=[]
    def add_mesh_simple(self,name,*args,**kwargs):
        self.calls.append((name,kwargs))
        return Handle()
    def add_line_segments(self,name,*args,**kwargs):
        self.calls.append((name,kwargs))
        return Handle()


def server_fixture():
    return SimpleNamespace(scene=Scene(),gui=SimpleNamespace(add_markdown=lambda text:SimpleNamespace(content=text)),atomic=nullcontext)


@pytest.fixture
def workspace(monkeypatch):
    calls=[]
    def mesh(graph):
        calls.append(graph)
        return np.zeros((3,3),dtype=np.float32),np.array([[0,1,2]],dtype=np.uint32)
    app.cached_surface.cache_clear()
    app.cached_venous_surface.cache_clear()
    monkeypatch.setattr(app,'network_mesh',mesh)
    result=app.Workspace(server_fixture(),load_reference_source=False)
    assert result.error is None
    yield result,calls
    app.cached_surface.cache_clear()
    app.cached_venous_surface.cache_clear()


def test_snapshot_and_meshes_keep_three_circuits_separate(workspace):
    work,calls=workspace
    state=work.snapshot()
    assert len(calls)==3
    assert set(state['layers'])==set(app.LAYERS)
    assert state['nodes']==state['layers']['arterial']['nodes']
    assert state['edges']==state['layers']['arterial']['edges']
    node_sets=[set(state['layers'][name]['nodes']) for name in app.LAYERS]
    assert not node_sets[0]&node_sets[1] and not node_sets[1]&node_sets[2] and not node_sets[0]&node_sets[2]
    rendered={name:settings['color'] for name,settings in work.server.scene.calls if name.endswith('/surface')}
    assert rendered=={f'/layers/{name}/surface':app.LAYER_COLORS[name] for name in app.LAYERS}
    assert all(settings['opacity']==1 for name,settings in work.server.scene.calls if name.endswith('/surface'))
    assert state['clearance']==work.clearance
    assert json.loads(work.export_bundle())['clearance']==state['clearance']
    state['parameters']['venous']['radius_scale']=2
    assert work.parameters['venous']['radius_scale']==1


def test_visibility_is_only_a_handle_update_even_during_rebuild(workspace):
    work,calls=workspace
    generation=work.generation
    render_count=len(work.server.scene.calls)
    work.busy=True
    visibility=dict(arterial=False,systemic_venous=True,hepatic_portal=False)
    work.set_visibility(visibility)
    assert len(calls)==3 and work.generation==generation
    assert len(work.server.scene.calls)==render_count
    assert all(not handle.visible for handle in work.layer_handles['arterial'])
    assert all(handle.visible for handle in work.layer_handles['systemic_venous'])
    assert all(not handle.visible for handle in work.layer_handles['hepatic_portal'])
    assert work.snapshot()['visibility']==visibility


def test_independent_rebuild_cache_and_local_namespace_validation(workspace):
    work,calls=workspace
    before_arterial=work.graph
    settings=copy.deepcopy(work.parameters)
    settings['venous']['imv_drainage']='superior_mesenteric'
    settings['venous']['vessel_parameters']={'ven_splenic_distal':{'radius_scale':1.4,'tortuosity':.6}}
    cleaned=app.validate_parameters(settings,work.known,work.known_venous)
    work.rebuild(cleaned)
    assert work.error is None and work.graph is before_arterial
    assert len(calls)==5  # two venous surfaces; arterial cache reused
    before_veins=work.venous
    settings=copy.deepcopy(work.parameters)
    settings['arch_variant']='common_origin'
    work.rebuild(app.validate_parameters(settings,work.known,work.known_venous))
    assert work.venous is before_veins and len(calls)==6
    wrong=copy.deepcopy(settings)
    wrong['vessel_parameters']={'ven_splenic_distal':{'radius_scale':1,'tortuosity':.3}}
    with pytest.raises(ValueError,match='Unknown vessel'):
        app.validate_parameters(wrong,work.known,work.known_venous)
    wrong=copy.deepcopy(settings)
    wrong['venous']['vessel_parameters']={'left_mca_m1':{'radius_scale':1,'tortuosity':.3}}
    with pytest.raises(ValueError,match='Unknown venous vessel'):
        app.validate_parameters(wrong,work.known,work.known_venous)


def test_combined_export_is_reproducible_and_preserves_exchange_metadata(workspace):
    work,_=workspace
    bundle=json.loads(work.export_bundle())
    assert bundle['schema']=='vv-toolbox.workspace/1'
    assert bundle['generation']==work.generation
    assert bundle['venous']['unmodeled_exchange']['render_as_vessel'] is False
    params=bundle['parameters']
    artery=generate(**{key:value for key,value in params.items() if key!='venous'})
    veins=generate_veins(**params['venous'])
    assert json.loads(artery.to_json())==bundle['arterial']
    assert json.loads(veins.to_json())==bundle['venous']
    assert bundle['venous']['provenance']['patient_derived'] is False


@pytest.mark.parametrize('bad',[{}, {'arterial':True,'systemic_venous':True,'hepatic_portal':1}, {'arterial':True,'systemic_venous':False,'hepatic_portal':True,'extra':False}])
def test_visibility_rejects_partial_or_non_boolean_mapping(bad):
    with pytest.raises(ValueError):
        app.validate_visibility(bad)


@pytest.mark.parametrize('field,value',[('radius_scale',float('nan')),('samples',True),('samples',3),('imv_drainage','arterial'),('transverse_dominance','none')])
def test_invalid_venous_parameters(field,value):
    settings=app.defaults()
    settings['venous'][field]=value
    with pytest.raises(ValueError):
        app.validate_parameters(settings,set(),set())


@pytest.mark.parametrize('header',[None,'','-1','1.0','1e0','NaN',' 1','1 ','99999999999999999999999999999',1,True])
def test_generation_header_required_and_strict(header):
    assert not app.expected_generation_matches(header,1)


def test_stale_editor_generation_rejected_after_other_edit(workspace):
    work,_=workspace
    editor_revision=str(work.snapshot()['generation'])
    assert app.expected_generation_matches(editor_revision,work.generation)
    changed=copy.deepcopy(work.parameters)
    changed['venous']['imv_drainage']='confluence'
    work.rebuild(changed)
    assert work.error is None
    assert not app.expected_generation_matches(editor_revision,work.generation)
    assert app.expected_generation_matches(str(work.snapshot()['generation']),work.generation)
