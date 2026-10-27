from copy import deepcopy

import pytest
import numpy as np
import trimesh

from vv_toolbox.case_app_service import CaseWorkspace, CaseWorkspaceConflict
from vv_toolbox.case_io import load_case, save_case


@pytest.fixture
def source():
    preview = {'schema': 'vv-toolbox.atlas-centerlines/1', 'algorithm': 'fixture', 'units': 'mm',
        'parts': [{'id': 'p', 'layer': 'arterial'}, {'id': 'v', 'layer': 'systemic_venous'}],
        'nodes': [{'id': 'a', 'part_id': 'p', 'point': [0, 0, 0], 'kind': 'endpoint'},
                  {'id': 'b', 'part_id': 'p', 'point': [1, 0, 0], 'kind': 'endpoint'}],
        'edges': [{'id': 'e', 'part_id': 'p', 'start': 'a', 'end': 'b',
                   'provenance': 'source-mesh-voxel-medial', 'points': [[0, 0, 0], [1, 0, 0]],
                   'radii': [1, 1]}], 'links': [{'part_a': 'p', 'part_b': 'q', 'status': 'candidate'}]}
    metadata = {'sha256': 'a'*64, 'parts': [
        {'id': 'p', 'layer': 'arterial', 'name': 'left test artery', 'sha256': 'b'*64},
        {'id': 'v', 'layer': 'systemic_venous', 'name': 'test vein', 'sha256': 'c'*64}]}
    return dict(preview=preview, metadata=metadata)


def test_prepare_save_reload_preserves_sources_and_uncertainty(tmp_path, source):
    before = deepcopy(source)
    store = CaseWorkspace(tmp_path/'case.json')
    result = store.update({'action': 'prepare', 'version': 0}, **source)
    assert result['summary']['edges'] == result['summary']['unresolved_edges'] == 1
    assert not result['rendered'] and not result['includes_atlas_edits']
    assert source == before
    store.update({'action': 'save', 'version': 1})
    reloaded = CaseWorkspace(store.path)
    result = reloaded.update({'action': 'reload', 'version': 0}, **source)
    assert result['summary'] == store.status()['summary']
    assert reloaded.download() == store.download()
    assert reloaded.case['inspection']['candidate_links'] == source['preview']['links']
    assert reloaded.case['edges'][0]['anatomy']['segment'] == 'unresolved'
    assert load_case(store.path)[0] == store.case


def test_stale_clients_and_existing_disk_require_explicit_reload(tmp_path, source):
    first = CaseWorkspace(tmp_path/'case.json')
    first.update({'action': 'prepare', 'version': 0}, **source)
    with pytest.raises(CaseWorkspaceConflict):
        first.update({'action': 'save', 'version': 0})
    first.update({'action': 'save', 'version': 1})
    second = CaseWorkspace(first.path)
    second.update({'action': 'prepare', 'version': 0}, **source)
    with pytest.raises(CaseWorkspaceConflict):
        second.update({'action': 'save', 'version': 1})
    second.update({'action': 'reload', 'version': 1}, **source)
    second.update({'action': 'save', 'version': 2})


def test_corrupt_reload_and_bad_prepare_preserve_workspace(tmp_path, source):
    store = CaseWorkspace(tmp_path/'case.json')
    store.update({'action': 'prepare', 'version': 0}, **source)
    before = store.download()
    store.path.write_text('{broken')
    with pytest.raises(ValueError):
        store.update({'action': 'reload', 'version': 1}, **source)
    source['preview']['edges'][0]['radii'] = [-1, 1]
    with pytest.raises(ValueError):
        store.update({'action': 'prepare', 'version': 1}, **source)
    assert store.download() == before and store.version == 1
    assert store.path.read_text() == '{broken'


def test_wrong_source_rejected_and_download_isolated(tmp_path, source):
    store = CaseWorkspace(tmp_path/'case.json')
    store.update({'action': 'prepare', 'version': 0}, **source)
    download = store.download()
    download['case']['sources'][0]['sha256'] = 'd'*64
    save_case(store.path, download['case'])
    before = store.download()
    with pytest.raises(ValueError, match='match'):
        store.update({'action': 'reload', 'version': 1}, **source)
    assert store.download() == before


@pytest.mark.parametrize('payload', [None, {}, {'action': 'save', 'version': True},
    {'action': 'unknown', 'version': 0}, {'action': 'save', 'version': 0, 'path': '../x'}])
def test_invalid_controls_no_writes(tmp_path, payload):
    store = CaseWorkspace(tmp_path/'case.json')
    with pytest.raises(ValueError):
        store.update(payload)
    assert not store.path.exists() and store.version == 0


def test_unloaded_and_unready_errors(tmp_path):
    store = CaseWorkspace(tmp_path/'case.json')
    for action in ('save', 'prepare'):
        with pytest.raises(ValueError):store.update({'action': action, 'version': 0})
    with pytest.raises(ValueError):store.download()
    assert store.status()['loaded'] is False


def test_current_surface_capture_preserves_geometry_and_interval_provenance(tmp_path, source):
    mesh = trimesh.creation.box(extents=[1., 2., 3.])
    parts = [dict(id='p', layer='arterial', vertices=mesh.vertices.copy(), faces=mesh.faces.copy()),
             dict(id='missing', layer='arterial', vertices=mesh.vertices.copy(), faces=mesh.faces.copy())]
    records = {'p': [dict(operation_index=1, provenance='synthetic test fixture')]}
    store = CaseWorkspace(tmp_path/'current.json')
    result = store.update({'action':'prepare_current','version':0}, **source,
                          surface_parts=parts, interval_edits=records)
    assert result['includes_atlas_edits'] and result['summary']['surface_parts'] == 1
    assert store.case['model_kind'] == 'synthetic'
    assert store.case['surface_parts'][0]['provenance'] == 'estimated'
    assert np.array_equal(store.case['surface_parts'][0]['vertices_mm'], mesh.vertices)
    assert store.case['inspection']['atlas_scene_capture']['omitted_arterial_parts'] == ['missing']
    assert store.case['edges'][0]['derivation']['radius_status'] == 'reference_profile_not_current_surface_measurement'
    assert store.case['generation']['config']['interval_edits'] == records
    store.update({'action':'save','version':1})
    reloaded = CaseWorkspace(store.path)
    reloaded.update({'action':'reload','version':0}, **source)
    assert reloaded.download() == store.download()
    assert np.array_equal(parts[0]['vertices'], mesh.vertices)


def test_current_capture_without_edits_stays_source(tmp_path, source):
    mesh = trimesh.creation.box()
    store = CaseWorkspace(tmp_path/'current.json')
    result = store.update({'action':'prepare_current','version':0}, **source,
        surface_parts=[dict(id='p',layer='arterial',vertices=mesh.vertices,faces=mesh.faces)])
    assert not result['includes_atlas_edits']
    assert store.case['model_kind'] == 'source'
    assert store.case['surface_parts'][0]['provenance'] == 'source'


def test_failed_surface_capture_preserves_previous_case(tmp_path, source):
    store = CaseWorkspace(tmp_path/'current.json')
    store.update({'action':'prepare','version':0}, **source)
    before = store.download()
    with pytest.raises(ValueError, match='lack corresponding'):
        store.update({'action':'prepare_current','version':1}, **source, surface_parts=[])
    assert store.download() == before and store.version == 1


def test_current_capture_includes_authored_artery_as_estimate_without_joining(tmp_path, source):
    mesh = trimesh.creation.box()
    source['preview']['parts'].append(dict(id='neck',layer='arterial',status='AUTHORED_ESTIMATE'))
    source['preview']['nodes'].extend([
        dict(id='neck-a',part_id='neck',point=[1,0,0],kind='authored'),
        dict(id='neck-b',part_id='neck',point=[2,0,0],kind='authored')])
    source['preview']['edges'].append(dict(id='neck-edge',part_id='neck',layer='arterial',
        start='neck-a',end='neck-b',provenance='authored-estimated',
        points=[[1,0,0],[2,0,0]],radii=[1,1]))
    parts = [dict(id='p',layer='arterial',vertices=mesh.vertices,faces=mesh.faces),
             dict(id='neck',name='Estimated neck',layer='arterial',vertices=mesh.vertices,faces=mesh.faces,
                  metadata=dict(kind='test-estimate',original_atlas_geometry=False,
                                source_endpoint_ids=['p'],limits='Test fixture; no union'))]
    store = CaseWorkspace(tmp_path/'neck.json')
    status = store.update({'action':'prepare_current','version':0},**source,surface_parts=parts)
    assert status['includes_estimates'] and not status['includes_atlas_edits']
    assert status['summary']['surface_parts'] == 2
    assert store.case['model_kind'] == 'synthetic'
    assert store.case['edges'][1]['geometry_kind'] == 'estimated'
    assert store.case['surface_parts'][1]['provenance'] == 'estimated'
    assert 'b' in store.case['nodes'] and 'neck-a' in store.case['nodes']
    assert store.case['inspection']['atlas_scene_capture']['estimated_metadata']['neck']['limits'] == 'Test fixture; no union'
    store.update({'action':'save','version':1})
    loaded = CaseWorkspace(store.path)
    loaded.update({'action':'reload','version':0},**source)
    assert loaded.download()==store.download()
