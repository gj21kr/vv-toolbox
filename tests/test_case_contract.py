from copy import deepcopy

import pytest

from vv_toolbox.case_contract import validate_case, validate_collection


@pytest.fixture
def case():
    positions = {'a': [0, 0, 0], 'b': [1, 0, 0], 'c': [1, 1, 0]}
    return {
        'schema': 'vv-toolbox.case/1', 'case_id': 'fixture', 'base_model_id': 'base',
        'model_kind': 'source', 'split': 'unassigned', 'generation': None,
        'frame': {'id': 'fixture', 'origin': 'synthetic fixture origin', 'units': 'mm', 'axes': 'LPS'},
        'sources': [{'id': 's', 'sha256': 'a' * 64, 'license_ref': 'test fixture'}],
        'nodes': {key: {'kind': 'junction', 'evidence_status': 'source_annotation',
                        'position_mm': point} for key, point in positions.items()},
        'edges': [{'id': str(i), 'start': start, 'end': end,
                   'anatomy': {'artery': 'ACA', 'side': 'L', 'segment': 'A2', 'branch_id': str(i)},
                   'source_ids': ['s'], 'geometry_kind': 'source',
                   'evidence_status': 'source_annotation',
                   'centerline_mm': [positions[start], positions[end]], 'radii_mm': [1, 1]}
                  for i, (start, end) in enumerate([('a', 'b'), ('b', 'c'), ('c', 'a')])],
    }


def test_cycle_and_multiple_same_segment_instances_preserved(case):
    before = deepcopy(case)
    assert validate_case(case) == {'a': ['0', '2'], 'b': ['0', '1'], 'c': ['1', '2']}
    assert case == before


@pytest.mark.parametrize('field,value', [('end', 'missing'), ('id', '1'),
    ('source_ids', ['missing']), ('radii_mm', [1, 0]), ('radii_mm', [1, float('nan')]),
    ('radii_mm', [1, True]), ('radii_mm', [1]), ('centerline_mm', [[0, 0, 0], [2, 0, 0]]),
    ('centerline_mm', [[0, 0, 0], [0, 0, 0], [1, 0, 0]]),
    ('centerline_mm', [[0, 0, 0], [float('inf'), 0, 0]])])
def test_invalid_edges_rejected(case, field, value):
    case['edges'][0][field] = value
    with pytest.raises(ValueError):
        validate_case(case)


def test_unresolved_geometry_remains_explicit(case):
    edge = case['edges'][0]
    edge.update(centerline_mm=None, radii_mm=None, evidence_status='unresolved')
    validate_case(case)
    edge['evidence_status'] = 'landmark_reviewed'
    with pytest.raises(ValueError, match='unresolved'):
        validate_case(case)


def test_region_review_is_not_a_point_annotation(case):
    case['nodes']['a'].update(position_mm=None, evidence_status='landmark_reviewed')
    with pytest.raises(ValueError, match='position'):
        validate_case(case)


def test_source_cannot_contain_estimated_geometry(case):
    case['edges'][0].update(geometry_kind='estimated', evidence_status='synthetic_estimate')
    with pytest.raises(ValueError, match='source model'):
        validate_case(case)
    case.update(model_kind='synthetic', generation={'seed': 42, 'generator_version': 'test', 'config': {}})
    validate_case(case)
    case['generation']['seed'] = True
    with pytest.raises(ValueError, match='generation'):
        validate_case(case)


def test_unknown_units_and_orphans_rejected(case):
    case['frame']['units'] = 'unknown'
    with pytest.raises(ValueError, match='frame'):
        validate_case(case)
    case['frame']['units'] = 'mm'
    case['nodes']['orphan'] = deepcopy(case['nodes']['a'])
    with pytest.raises(ValueError, match='orphan'):
        validate_case(case)


def test_split_lineage_and_duplicate_cases(case):
    other = deepcopy(case)
    with pytest.raises(ValueError, match='duplicate case'):
        validate_collection([case, other])
    other['case_id'] = 'derived'
    assert validate_collection([case, other]) == {'case_count': 2, 'base_model_count': 1}
    other['split'] = 'test'
    with pytest.raises(ValueError, match='different splits'):
        validate_collection([case, other])
    other['base_model_id'] = 'independent'
    with pytest.raises(ValueError, match='shared geometry source'):
        validate_collection([case, other])
    other['sources'][0]['sha256'] = 'b'*64
    assert validate_collection([case, other])['base_model_count'] == 2


def test_source_id_rename_and_hash_case_do_not_bypass_isolation(case):
    other = deepcopy(case)
    other.update(case_id='other', base_model_id='renamed', split='test')
    other['sources'][0].update(id='renamed_source', sha256='A'*64)
    for edge in other['edges']:
        edge['source_ids'] = ['renamed_source']
    before = deepcopy(other)
    with pytest.raises(ValueError, match='shared geometry source'):
        validate_collection([case, other])
    assert other == before
    other['split'] = case['split']
    assert validate_collection([case, other])['case_count'] == 2


def test_unreferenced_metadata_does_not_bind_distinct_geometry(case):
    other = deepcopy(case)
    other.update(case_id='other', base_model_id='other', split='test')
    other['sources'][0]['sha256'] = 'b'*64
    other['sources'].append(dict(id='unused', sha256='a'*64, license_ref='fixture'))
    assert validate_collection([case,other])['case_count'] == 2


def test_collection_cli_loads_verified_snapshots_and_rejects_leakage(case,tmp_path,capsys):
    import json
    from vv_toolbox.case_cli import main
    from vv_toolbox.case_io import save_case
    other = deepcopy(case)
    other.update(case_id='other',base_model_id='renamed',split='test')
    first,second = tmp_path/'first.json',tmp_path/'second.json'
    save_case(first,case)
    save_case(second,other)
    before = [p.read_bytes() for p in (first,second)]
    with pytest.raises(SystemExit) as stopped:
        main(['collection',str(first),str(second)])
    assert stopped.value.code == 2
    capsys.readouterr()
    assert [p.read_bytes() for p in (first,second)] == before
    assert main(['collection',str(first)]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report['case_count']==1 and report['independent_anatomy']=='UNKNOWN'
    assert len(report['revisions'])==1
