from copy import deepcopy
import threading

import numpy as np
import pytest

from test_atlas_interval_preview import fixture
from vv_toolbox.atlas_interval_preview import preview_interval
from vv_toolbox.interval_snapshot import encode_interval_snapshot
from vv_toolbox.interval_application import apply_interval, undo_interval
from vv_toolbox.atlas_edit_session import AtlasEditConflict
import vv_toolbox.interval_application as application


def prepared():
    ws, request = fixture()
    ws.atlas.metadata = {'sha256': 'a'*64}
    ws.lock = threading.RLock()
    ws.busy = False
    candidate = preview_interval(ws, request)
    return ws, encode_interval_snapshot(candidate)[0].decode(), candidate


def test_actual_regeneration_applies_separate_surface_and_preserves_source():
    ws, text, candidate = prepared()
    original = deepcopy(ws.atlas.meshes[0])
    rendered = []
    result = apply_interval(ws, text, 7, lambda: rendered.append(ws.generation))
    assert result['status'] == 'APPLIED' and rendered == [8]
    assert np.array_equal(ws.atlas_modified_parts['vessel']['vertices'], candidate['vertices'])
    assert np.array_equal(ws.atlas.meshes[0]['vertices'], original['vertices'])
    assert ws.atlas_interval_edits['vessel'][0]['revalidation']['status'] == 'PASS'
    assert ws.interval_preview_busy is False


def test_render_failure_restores_state_and_rebuilds_prior_view():
    ws, text, _ = prepared()
    prior = ws.atlas_modified_parts
    calls = []
    def render():
        calls.append(ws.generation)
        if len(calls) == 1:
            raise RuntimeError('renderer failure')
    with pytest.raises(RuntimeError, match='renderer failure'):
        apply_interval(ws, text, 7, render)
    assert calls == [8, 7]
    assert ws.atlas_modified_parts is prior and ws.atlas_interval_edits == {}
    assert ws.generation == 7 and ws.interval_preview_busy is False


def test_stale_generation_never_calls_renderer():
    ws, text, _ = prepared()
    with pytest.raises(AtlasEditConflict):
        apply_interval(ws, text, 6, lambda: pytest.fail('must not render'))
    assert ws.atlas_modified_parts == {}


def test_failed_rollback_marks_recovery_required():
    ws, text, _ = prepared()
    def render():
        raise RuntimeError('broken renderer')
    with pytest.raises(RuntimeError, match='recovery required'):
        apply_interval(ws, text, 7, render)
    assert ws.atlas_edit_recovery_error
    assert ws.generation == 7 and ws.interval_preview_busy is False


def test_scene_change_during_revalidation_discards_candidate(monkeypatch):
    ws, text, _ = prepared()
    real = application.revalidate_interval_snapshot
    def changed(snapshot, text):
        result = real(snapshot, text)
        with ws.lock:
            ws.generation += 1
        return result
    monkeypatch.setattr(application, 'revalidate_interval_snapshot', changed)
    with pytest.raises(AtlasEditConflict):
        apply_interval(ws, text, 7, lambda: pytest.fail('must not render'))
    assert ws.generation == 8 and ws.atlas_modified_parts == {}
    assert ws.interval_preview_busy is False


def test_two_actual_edits_undo_in_reverse_order():
    ws, text, _ = prepared()
    apply_interval(ws, text, 7, lambda: None)
    first = deepcopy(ws.atlas_modified_parts['vessel'])
    _, request = fixture()
    second = preview_interval(ws, request)
    second_text = encode_interval_snapshot(second)[0].decode()
    apply_interval(ws, second_text, 8, lambda: None)
    assert len(ws.atlas_interval_edits['vessel']) == 2
    assert undo_interval(ws, 9, lambda: None)['status'] == 'UNDONE'
    assert np.array_equal(ws.atlas_modified_parts['vessel']['vertices'], first['vertices'])
    assert len(ws.atlas_interval_edits['vessel']) == 1
    undo_interval(ws, 10, lambda: None)
    assert ws.atlas_modified_parts == {} and ws.atlas_interval_edits == {}
    assert ws.generation == 11 and ws.atlas_interval_undo == []


def test_undo_cannot_overwrite_intervening_scene_change():
    ws, text, _ = prepared()
    apply_interval(ws, text, 7, lambda: None)
    ws.generation += 1
    with pytest.raises(AtlasEditConflict, match='current scene'):
        undo_interval(ws, 9, lambda: pytest.fail('must not render'))
    assert ws.generation == 9 and len(ws.atlas_interval_undo) == 1


def test_undo_render_failure_keeps_edit_and_retryable_history():
    ws, text, _ = prepared()
    apply_interval(ws, text, 7, lambda: None)
    first = deepcopy(ws.atlas_modified_parts['vessel'])
    calls = []
    def render():
        calls.append(ws.generation)
        if len(calls) == 1:
            raise RuntimeError('undo render failure')
    with pytest.raises(RuntimeError, match='undo render failure'):
        undo_interval(ws, 8, render)
    assert calls == [9, 8] and ws.generation == 8
    assert np.array_equal(ws.atlas_modified_parts['vessel']['vertices'], first['vertices'])
    assert len(ws.atlas_interval_undo) == 1
    undo_interval(ws, 8, lambda: None)
    assert ws.atlas_modified_parts == {}
