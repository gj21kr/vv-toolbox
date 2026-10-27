import json
import os

import pytest

from vv_toolbox.case_cli import main
from vv_toolbox.case_io import case_digest, load_case, save_case
from test_synthetic_routes import fixture, routes_fixture


def test_bridge_snapshot_roundtrip_preserves_source_and_configuration(tmp_path, capsys):
    case, spec = fixture()
    source, config, output = [tmp_path/name for name in ('source.json','config.json','synthetic.json')]
    source_revision = save_case(source, case)
    source_bytes = source.read_bytes()
    config.write_text(json.dumps(spec))
    args = ['synthetic-routes',str(source),str(config),str(output),'--case-id','derived']
    assert main(args) == 0
    assert json.loads(capsys.readouterr().out)['model_kind'] == 'synthetic'
    result, revision = load_case(output)
    assert result['generation']['config'] == spec
    assert result['edges'][:len(case['edges'])] == case['edges']
    assert source.read_bytes() == source_bytes
    assert load_case(source)[1] == source_revision
    before = output.read_bytes()
    with pytest.raises(SystemExit): main(args)
    assert output.read_bytes() == before
    assert main(args + ['--expected-revision',revision]) == 0


@pytest.mark.parametrize('alias', [False, True])
def test_source_cannot_be_overwritten_even_with_revision(tmp_path, alias):
    case, spec = fixture()
    source, config = tmp_path/'source.json', tmp_path/'config.json'
    revision = save_case(source, case)
    config.write_text(json.dumps(spec))
    output = tmp_path/'alias.json' if alias else source
    if alias: os.link(source, output)
    before = source.read_bytes()
    with pytest.raises(SystemExit) as error:
        main(['synthetic-routes',str(source),str(config),str(output),
              '--case-id','derived','--expected-revision',revision])
    assert error.value.code == 2
    assert source.read_bytes() == before


def test_four_route_cli_reports_unresolved_without_mutation(tmp_path, capsys):
    case, routes = routes_fixture()
    case['nodes']['a']['evidence_status'] = 'unresolved'
    source, config = tmp_path/'source.json', tmp_path/'routes.json'
    save_case(source, case)
    config.write_text(json.dumps(routes))
    before = source.read_bytes()
    assert main(['four-routes',str(source),str(config)]) == 3
    report = json.loads(capsys.readouterr().out)
    assert report['status'] == 'UNKNOWN' and len(report['routes']) == 4
    assert report['anatomical_acceptance'] == 'UNKNOWN'
    assert source.read_bytes() == before


def test_duplicate_specification_key_rejected_before_output(tmp_path):
    case, spec = fixture()
    source, config, output = [tmp_path/name for name in ('source.json','config.json','synthetic.json')]
    save_case(source, case)
    config.write_text(json.dumps(spec)[:-1] + ',"bridges":[]}')
    with pytest.raises(SystemExit):
        main(['synthetic-routes',str(source),str(config),str(output),'--case-id','derived'])
    assert not output.exists()


def test_split_then_extend_cli_preserves_inputs_and_creates_three_way_junction(tmp_path, capsys):
    from test_synthetic_route_extension import parent_and_extension
    parent, _ = parent_and_extension()
    original = tmp_path / 'parent.json'
    split_path, output = tmp_path / 'split.json', tmp_path / 'branch.json'
    split_spec, extension_spec = tmp_path / 'split-spec.json', tmp_path / 'extension-spec.json'
    save_case(original, parent)
    before = original.read_bytes()
    split_spec.write_text(json.dumps(dict(schema='vv-toolbox.synthetic-junction/1',
        parent_case_sha256=case_digest(parent), source_hashes={s['id']:s['sha256'] for s in parent['sources']},
        edge_id='a', interval_index=0, fraction=.5, node_id='junction', child_edge_ids=['a1','a2'],
        rationale='explicit fixture junction', evidence_refs=['fixture'])))
    assert main(['split-junction',str(original),str(split_spec),str(split_path),'--case-id','split']) == 0
    split, revision = load_case(split_path)
    split_bytes = split_path.read_bytes()
    extension_spec.write_text(json.dumps(dict(schema='vv-toolbox.synthetic-route-extension/1',
        parent_case_sha256=revision, bridges=[dict(id='side',
            **{'from':dict(edge_id='a1',endpoint='end'),'to':dict(edge_id='c',endpoint='start')},
            attachment_mode='side_branch', from_direction_xyz=[0,1,0], from_radius_mm=.5,
            handle_lengths_mm=[10,10], samples=101, rationale='fixture side branch', evidence_refs=['fixture'])])))
    args = ['extend-routes',str(split_path),str(extension_spec),str(output),'--case-id','extended']
    assert main(args) == 0
    result, _ = load_case(output)
    assert sum('junction' in (e['start'],e['end']) for e in result['edges']) == 3
    assert result['synthetic_route_inspection']['bridge_ids'] == ['bridge','side']
    assert original.read_bytes() == before and split_path.read_bytes() == split_bytes
    saved_output = output.read_bytes()
    with pytest.raises(SystemExit):
        main(args)
    assert output.read_bytes() == saved_output
    with pytest.raises(SystemExit):
        main(['extend-routes',str(split_path),str(extension_spec),str(split_path),
              '--case-id','extended','--expected-revision',revision])
    assert split_path.read_bytes() == split_bytes
