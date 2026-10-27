from copy import deepcopy
import json

import pytest

from test_atlas_interval_preview import fixture
from vv_toolbox.atlas_interval_preview import preview_interval
from vv_toolbox.interval_snapshot import save_interval_snapshot, load_interval_snapshot, encode_interval_snapshot
from vv_toolbox.interval_snapshot import process_snapshot_request


@pytest.fixture(scope='module')
def candidate():
    workspace, request = fixture()
    workspace.atlas.metadata = dict(sha256='a' * 64)
    return preview_interval(workspace, request)


def test_immutable_save_reload_preserves_geometry_conditions_and_checks(tmp_path, candidate):
    before = deepcopy(candidate)
    path, revision = save_interval_snapshot(tmp_path, candidate)
    loaded, restored_revision = load_interval_snapshot(path, expected_atlas_sha256='a' * 64)
    assert loaded == candidate and restored_revision == revision
    assert save_interval_snapshot(tmp_path, candidate) == (path, revision)
    assert candidate == before
    assert len(list(tmp_path.iterdir())) == 1


def test_distinct_generation_has_distinct_revision(tmp_path, candidate):
    changed = deepcopy(candidate)
    changed['generation'] += 1
    first, _ = save_interval_snapshot(tmp_path, candidate)
    second, _ = save_interval_snapshot(tmp_path, changed)
    assert first != second and first.exists()


def test_hash_and_expected_source_mismatch_rejected(tmp_path, candidate):
    path, _ = save_interval_snapshot(tmp_path, candidate)
    with pytest.raises(ValueError, match='Atlas source'):
        load_interval_snapshot(path, expected_atlas_sha256='b' * 64)
    value = json.loads(path.read_text())
    value['candidate']['vertices'][0][0] += 1
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError, match='fingerprint'):
        load_interval_snapshot(path)
    with pytest.raises(ValueError, match='immutable'):
        save_interval_snapshot(tmp_path, candidate)


@pytest.mark.parametrize('field,value', [
    ('frame', {'units':'mm'}), ('vertices', [[float('nan'),0,0]]),
    ('faces', [[0,1,999999]]), ('applied', True)])
def test_invalid_snapshot_not_written(tmp_path, candidate, field, value):
    changed = deepcopy(candidate)
    changed[field] = value
    with pytest.raises(ValueError):
        save_interval_snapshot(tmp_path, changed)
    assert not list(tmp_path.iterdir())


def test_changed_reference_geometry_rejected(candidate):
    changed = deepcopy(candidate)
    changed['reference_vertices'][0][0] += .1
    with pytest.raises(ValueError, match='fingerprint'):
        encode_interval_snapshot(changed)


def test_duplicate_json_keys_rejected(tmp_path):
    path = tmp_path / 'duplicate.json'
    path.write_text('{"schema":"first","schema":"second"}')
    with pytest.raises(ValueError):
        load_interval_snapshot(path)


def test_download_upload_keeps_original_text_and_marks_no_revalidation(candidate):
    exported = process_snapshot_request({'action':'export', 'candidate':candidate},
                                       expected_atlas_sha256='a' * 64)
    loaded = process_snapshot_request({'action':'import', 'snapshot_text':exported['snapshot_text']},
                                     expected_atlas_sha256='a' * 64)
    assert loaded['candidate'] == candidate
    assert loaded['snapshot_text'] == exported['snapshot_text']
    assert loaded['integrity'] == 'PASS' and loaded['geometry_revalidation'] == 'NOT RUN'
    assert loaded['applied'] is False


def test_export_different_atlas_rejected(candidate):
    with pytest.raises(ValueError, match='Atlas source'):
        process_snapshot_request({'action':'export', 'candidate':candidate},
                                 expected_atlas_sha256='b' * 64)
