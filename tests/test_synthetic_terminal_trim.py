from copy import deepcopy

import pytest

from vv_toolbox.case_contract import validate_case
from vv_toolbox.case_io import case_digest
from vv_toolbox.synthetic_junctions import trim_synthetic_terminal
from vv_toolbox.synthetic_routes import build_synthetic_routes
from test_synthetic_junctions import spec
from test_synthetic_routes import fixture


def declaration(case, endpoint='start'):
    result = spec(case)
    result.update(schema='vv-toolbox.synthetic-terminal-trim/1', remove_endpoint=endpoint)
    return result


@pytest.mark.parametrize('endpoint', ['start', 'end'])
def test_trim_preserves_source_and_archives_tail(endpoint):
    source, _ = fixture()
    before = deepcopy(source)
    result = trim_synthetic_terminal(source, declaration(source, endpoint), case_id='trimmed')
    assert source == before
    assert result['edges'][-1] == source['edges'][-1]
    kept = result['edges'][0]
    assert kept['centerline_mm'] == ([[4., 0., 0.], [10, 0, 0]] if endpoint == 'start' else [[0, 0, 0], [4., 0., 0.]])
    assert kept['radii_mm'] == ([1.4, 2] if endpoint == 'start' else [1, 1.4])
    assert len(validate_case(result)['new']) == 1
    history = result['synthetic_junctions']['history'][-1]
    assert history['parent_edge'] == source['edges'][0]
    assert history['removed_tail']['id'] not in {e['id'] for e in result['edges']}
    assert history['removed_node_id'] not in result['nodes']
    assert result['nodes']['new']['kind'] == 'unresolved'


def test_trim_rejects_connected_tail_but_rebinds_retained_bridge():
    source, bridge_spec = fixture()
    parent = build_synthetic_routes(source, bridge_spec, case_id='bridged')
    before = deepcopy(parent)
    with pytest.raises(ValueError, match='free terminal'):
        trim_synthetic_terminal(parent, declaration(parent, 'end'), case_id='bad')
    result = trim_synthetic_terminal(parent, declaration(parent), case_id='trimmed')
    bridge = next(e for e in result['edges'] if e['id'] == 'bridge')
    assert bridge['derivation']['anchors'][0]['edge_id'] == 'a1'
    assert not result['synthetic_route_inspection']['source_nodes_preserved']
    assert parent == before


@pytest.mark.parametrize('field,value', [('parent_case_sha256', '0'*64), ('source_hashes', {}), ('remove_endpoint', 'nearest')])
def test_invalid_trim_is_atomic(field, value):
    source, _ = fixture()
    before = deepcopy(source)
    request = declaration(source)
    request[field] = value
    with pytest.raises(ValueError):
        trim_synthetic_terminal(source, request, case_id='bad')
    assert case_digest(source) == case_digest(before)


def test_trim_cli_roundtrip_and_source_overwrite_guard(tmp_path):
    import json
    from vv_toolbox.case_cli import main
    from vv_toolbox.case_io import save_case, load_case
    source, _ = fixture()
    snapshot, request, output = [tmp_path / name for name in ('source.json', 'trim.json', 'out.json')]
    save_case(snapshot, source)
    request.write_text(json.dumps(declaration(source)))
    before = snapshot.read_bytes()
    assert main(['trim-terminal', str(snapshot), str(request), str(output), '--case-id', 'trimmed']) == 0
    derived, _ = load_case(output)
    assert derived['generation']['generator_version'] == 'explicit-terminal-trim-1'
    with pytest.raises(SystemExit) as error:
        main(['trim-terminal', str(snapshot), str(request), str(snapshot), '--case-id', 'bad'])
    assert error.value.code == 2
    assert snapshot.read_bytes() == before
