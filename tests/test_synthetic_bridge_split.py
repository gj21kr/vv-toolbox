from copy import deepcopy

import pytest

from vv_toolbox.case_io import case_digest
from vv_toolbox.synthetic_junctions import split_synthetic_bridge
from vv_toolbox.synthetic_routes import build_synthetic_routes
from vv_toolbox.junction_continuity import inspect_bridge_continuity
from test_synthetic_routes import fixture


def parent_and_spec():
    source, request = fixture()
    parent = build_synthetic_routes(source, request, case_id='parent')
    spec = dict(schema='vv-toolbox.synthetic-bridge-split/1', parent_case_sha256=case_digest(parent),
                source_hashes={s['id']: s['sha256'] for s in parent['sources']},
                edge_id='bridge', interval_index=4, fraction=.5, node_id='junction',
                child_edge_ids=['b0', 'b1'], rationale='synthetic fixture branch site', evidence_refs=['fixture'])
    return parent, spec


def test_split_bridge_retains_geometry_external_anchors_and_continuity():
    parent, spec = parent_and_spec()
    before = deepcopy(parent)
    result = split_synthetic_bridge(parent, spec, case_id='split')
    assert parent == before
    assert result['synthetic_route_inspection']['bridge_ids'] == ['b0', 'b1']
    a, b = result['edges'][-2:]
    assert a['centerline_mm'][-1] == b['centerline_mm'][0] == [14.5, 0, 0]
    assert a['derivation']['anchors'][0] == parent['edges'][-1]['derivation']['anchors'][0]
    assert b['derivation']['anchors'][1] == parent['edges'][-1]['derivation']['anchors'][1]
    assert result['synthetic_junctions']['history'][-1]['parent_edge'] == parent['edges'][-1]
    report = inspect_bridge_continuity(result, max_angle_deg=1., max_radius_jump_mm=0.)
    assert report['status'] == 'PASS' and len(report['attachments']) == 4


def test_split_rejects_nonbridge_and_stale_hash():
    parent, spec = parent_and_spec()
    for changes in [{'edge_id': 'a'}, {'parent_case_sha256': '0'*64}]:
        with pytest.raises(ValueError):
            split_synthetic_bridge(parent, {**spec, **changes}, case_id='bad')


def test_continuity_rejects_forged_sibling_reference():
    parent, spec = parent_and_spec()
    result = split_synthetic_bridge(parent, spec, case_id='split')
    result['edges'][-1]['bridge_split']['parent_case_revision'] = '0'*64
    with pytest.raises(ValueError, match='reciprocal'):
        inspect_bridge_continuity(result, max_angle_deg=1., max_radius_jump_mm=0.)


def test_side_branch_override_stays_only_at_external_start():
    parent, spec = parent_and_spec()
    parent['edges'][-1]['derivation'].update(attachment_mode='side_branch',
        from_direction_xyz=[1., 0., 0.], from_radius_mm=2.)
    spec['parent_case_sha256'] = case_digest(parent)
    result = split_synthetic_bridge(parent, spec, case_id='split')
    first, second = result['edges'][-2:]
    assert first['derivation']['from_radius_mm'] == 2.
    assert 'from_radius_mm' not in second['derivation']
    assert inspect_bridge_continuity(result, max_angle_deg=1., max_radius_jump_mm=0.)['status'] == 'PASS'


def test_cli_bridge_split_roundtrip(tmp_path):
    import json
    from vv_toolbox.case_io import save_case, load_case
    from vv_toolbox.case_cli import main
    parent, spec = parent_and_spec()
    source, request, output = [tmp_path/name for name in ['parent.json', 'spec.json', 'output.json']]
    save_case(source, parent)
    request.write_text(json.dumps(spec))
    before = source.read_bytes()
    assert main(['split-bridge', str(source), str(request), str(output), '--case-id', 'split']) == 0
    case, _ = load_case(output)
    assert inspect_bridge_continuity(case, max_angle_deg=1., max_radius_jump_mm=0.)['status'] == 'PASS'
    assert source.read_bytes() == before


def test_nested_split_is_explicitly_rejected_without_mutation():
    parent, spec = parent_and_spec()
    result = split_synthetic_bridge(parent, spec, case_id='split')
    before = deepcopy(result)
    spec.update(parent_case_sha256=case_digest(result), edge_id='b0', child_edge_ids=['c0', 'c1'], node_id='another')
    with pytest.raises(ValueError, match='nested'):
        split_synthetic_bridge(result, spec, case_id='nested')
    assert result == before
