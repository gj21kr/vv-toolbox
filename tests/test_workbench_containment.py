from copy import deepcopy
from types import SimpleNamespace

import pytest
import trimesh

from vv_toolbox import atlas
from vv_toolbox.case_io import case_digest
from vv_toolbox.label_workbench import process_request
from test_label_workbench import request


def bound_request(monkeypatch):
    req = request()
    req.pop('assignments')
    req.update(action='containment', parameters={'edge_id': 'a'})
    case = req['snapshot']['case']
    case['frame'] = dict(id='bodyparts3d_native_LPS', axes='LPS', units='mm',
                        origin='unchanged BodyParts3D native origin')
    case['sources'][0]['sha256'] = atlas.PINNED['isa_BP3D_4.0_obj_99.zip']
    case['edges'][0]['source_part_id'] = 'surface'
    mesh = trimesh.creation.box(extents=[40, 40, 40])
    loaded = SimpleNamespace(metadata={'sha256': case['sources'][0]['sha256']},
                             meshes=[dict(id='surface', vertices=mesh.vertices, faces=mesh.faces)])
    monkeypatch.setattr(atlas, 'load_atlas', lambda: loaded)
    req['snapshot']['revision'] = case_digest(case)
    return req


def test_bound_readonly_inspection(monkeypatch):
    req = bound_request(monkeypatch)
    before = deepcopy(req)
    result = process_request(req)['inspection']
    assert result['status'] == 'PASS'
    assert result['case_revision'] == req['snapshot']['revision']
    assert result['source_part_id'] == 'surface'
    assert result['containment']['segment_count'] == 1
    assert result['anatomical_validation'] == 'NOT RUN'
    assert req == before


@pytest.mark.parametrize('damage', ['frame', 'hash', 'part', 'edge_binding', 'missing_part'])
def test_unbound_comparison_is_unknown(monkeypatch, damage):
    req = bound_request(monkeypatch)
    case = req['snapshot']['case']
    if damage == 'frame':
        case['frame']['origin'] = 'different origin'
    elif damage == 'hash':
        case['sources'][0]['sha256'] = 'b' * 64
    elif damage == 'part':
        case['edges'][0].pop('source_part_id')
    elif damage == 'missing_part':
        case['edges'][0]['source_part_id'] = 'not-present'
    else:
        case['sources'].append(dict(id='other', sha256='b'*64, license_ref='fixture'))
        case['edges'][0]['source_ids'] = ['other']
    req['snapshot']['revision'] = case_digest(case)
    result = process_request(req)['inspection']
    assert result['status'] == 'UNKNOWN'
    assert 'containment' not in result


def test_outside_centerline_reports_fail_without_edit(monkeypatch):
    req = bound_request(monkeypatch)
    case = req['snapshot']['case']
    case['edges'][0]['centerline_mm'].insert(1, [30, 30, 0])
    case['edges'][0]['radii_mm'].insert(1, 1)
    req['snapshot']['revision'] = case_digest(case)
    before = deepcopy(req)
    result = process_request(req)['inspection']
    assert result['status'] == 'FAIL'
    assert result['containment']['outside_witnesses']
    assert req == before


def test_unavailable_atlas_is_unknown(monkeypatch):
    req = bound_request(monkeypatch)
    def unavailable():
        raise FileNotFoundError('private local path must not be returned')
    monkeypatch.setattr(atlas, 'load_atlas', unavailable)
    result = process_request(req)['inspection']
    assert result['status'] == 'UNKNOWN'
    assert 'private local path' not in str(result)
