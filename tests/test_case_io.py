import json

import pytest

from vv_toolbox.case_io import load_case, save_case
from vv_toolbox.case_cli import main


@pytest.fixture
def case():
    return {'schema': 'vv-toolbox.case/1', 'case_id': 'test', 'base_model_id': 'test',
        'model_kind': 'source', 'split': 'unassigned', 'generation': None,
        'frame': {'id': 'f', 'units': 'mm', 'axes': 'LPS', 'origin': 'fixture'},
        'sources': [{'id': 's', 'sha256': 'a'*64, 'license_ref': 'fixture'}],
        'nodes': {n: {'kind': 'unresolved', 'evidence_status': 'unresolved', 'position_mm': p}
                  for n, p in [('a', [0, 0, 0]), ('b', [1, 0, 0])]},
        'edges': [{'id': 'e', 'start': 'a', 'end': 'b', 'source_ids': ['s'],
                   'anatomy': {'artery': 'ACA', 'side': 'L', 'segment': 'unresolved', 'branch_id': 'e'},
                   'geometry_kind': 'source', 'evidence_status': 'unresolved',
                   'centerline_mm': [[0, 0, 0], [1, 0, 0]], 'radii_mm': [1, 1]}]}


def test_roundtrip_and_revision_conflict(tmp_path, case):
    path = tmp_path / 'case.json'
    revision = save_case(path, case)
    assert load_case(path, expected_sources={'s': 'a'*64}) == (case, revision)
    before = path.read_bytes()
    case['case_id'] = 'edited'
    with pytest.raises(ValueError, match='conflict'):
        save_case(path, case)
    assert path.read_bytes() == before
    changed = save_case(path, case, expected_revision=revision)
    assert changed != revision
    assert load_case(path)[0] == case


def test_corruption_and_bad_case_never_overwrite(tmp_path, case):
    path = tmp_path / 'case.json'
    revision = save_case(path, case)
    data = json.loads(path.read_text())
    data['case']['case_id'] = 'corrupt'
    path.write_text(json.dumps(data))
    before = path.read_bytes()
    with pytest.raises(ValueError, match='hash mismatch'):
        save_case(path, case, expected_revision=revision)
    assert path.read_bytes() == before
    assert not list(tmp_path.glob('*.lock'))
    case['edges'][0]['radii_mm'] = [-1, 1]
    with pytest.raises(ValueError):
        save_case(path, case)
    assert path.read_bytes() == before


def test_lock_and_source_mismatch(tmp_path, case):
    path = tmp_path / 'case.json'
    save_case(path, case)
    with pytest.raises(ValueError, match='identity'):
        load_case(path, expected_sources={'s': 'b'*64})
    lock = tmp_path / 'case.json.lock'
    lock.touch()
    with pytest.raises(ValueError, match='lock'):
        save_case(path, case)
    assert lock.exists()


def test_failed_replace_preserves_existing(tmp_path, case, monkeypatch):
    path = tmp_path / 'case.json'
    revision = save_case(path, case)
    before = path.read_bytes()
    def fail(*args):
        raise OSError('simulated storage error')
    monkeypatch.setattr('vv_toolbox.case_io.os.replace', fail)
    case['case_id'] = 'edited'
    with pytest.raises(OSError):
        save_case(path, case, expected_revision=revision)
    assert path.read_bytes() == before
    assert sorted(p.name for p in tmp_path.iterdir()) == ['case.json']


def test_cli_real_file_roundtrip(tmp_path, case, capsys):
    raw, saved = tmp_path / 'raw.json', tmp_path / 'saved.json'
    raw.write_text(json.dumps(case))
    assert main(['save', str(raw), str(saved)]) == 0
    assert main(['inspect', str(saved)]) == 0
    outputs = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert outputs[0]['revision'] == outputs[1]['revision']
    assert outputs[1]['unresolved_edges'] == 1


def test_cli_route_unknown_has_nonzero_result(tmp_path, case, capsys):
    path = tmp_path / 'case.json'
    save_case(path, case)
    assert main(['route', str(path), '--start', 'a', '--end', 'b', '--via', 'e']) == 3
    report = json.loads(capsys.readouterr().out)
    assert report['status'] == 'UNKNOWN'
    assert report['unresolved_edges'] == ['e']


def test_cli_split_save_reload(tmp_path, case, capsys):
    from vv_toolbox.atlas_annotations import new_annotation_document
    input_path, output = tmp_path / 'case.json', tmp_path / 'split.json'
    annotations, assignments = tmp_path / 'annotations.json', tmp_path / 'assignments.json'
    save_case(input_path, case)
    before = input_path.read_bytes()
    doc = new_annotation_document('s', 'a'*64, coordinate_frame_id='f', units='mm',
                                  frame_confirmed=True, units_confirmed=True)
    boundary = next(b for b in doc['boundaries'] if b['boundary_id'] == 'B.L.ACA.A1_A2')
    boundary.update(position=[.5, 0, 0], branch_id='e', evidence_status='landmark_reviewed',
                    source_refs=['fixture'])
    annotations.write_text(json.dumps(doc))
    assignments.write_text(json.dumps([{'edge_id': 'e', 'labels': ['A1', 'A2'],
        'extent_review_refs': ['fixture'], 'cuts': [{'boundary_id': boundary['boundary_id'],
        'interval_index': 0, 'fraction': .5}]}]))
    assert main(['split', str(input_path), str(annotations), str(assignments), str(output),
                 '--tolerance-mm', '0']) == 0
    assert [e['anatomy']['segment'] for e in load_case(output)[0]['edges']] == ['A1', 'A2']
    assert input_path.read_bytes() == before
