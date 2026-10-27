import hashlib
import json

import numpy as np
import pytest

from test_candidate_radius_session import session, compute
from vv_toolbox.candidate_radius_io import restore_session, _encode


def resign(document):
    document['sha256'] = hashlib.sha256(_encode(document['payload'])).hexdigest()
    return json.dumps(document)


def test_two_edits_roundtrip_with_undo_history():
    editor = session()
    base = editor.current()
    editor.apply(editor.publish(compute(editor))['token'])
    first = editor.current()
    editor.apply(editor.publish(compute(editor))['token'])
    restored = restore_session(base, editor.export_text())
    assert np.array_equal(restored.current()['vertices_mm'], editor.current()['vertices_mm'])
    assert restored.export_text() == editor.export_text()
    assert np.array_equal(restored.undo()['vertices_mm'], first['vertices_mm'])
    assert np.array_equal(restored.undo()['vertices_mm'], base['vertices_mm'])


@pytest.mark.parametrize('change', ['geometry', 'path', 'revision', 'lineage'])
def test_changed_base_rejected(change):
    editor = session()
    text = editor.export_text()
    base = editor.current()
    if change == 'geometry':base['vertices_mm'][0, 0] += .01
    elif change == 'path':base['source_centerlines']['middle']['points_mm'][0][0] += .01
    elif change == 'revision':base['summary']['revision'] = 'other'
    else:base['face_lineage']['source_face_indices'][0] += 1
    with pytest.raises(ValueError, match='base'):
        restore_session(base, text)


def test_corrupt_and_forged_output_rejected():
    editor = session()
    base = editor.current()
    editor.apply(editor.publish(compute(editor))['token'])
    document = json.loads(editor.export_text())
    document['payload']['operations'][0]['output_geometry_sha256'] = 'wrong'
    with pytest.raises(ValueError, match='checksum'):
        restore_session(base, json.dumps(document))
    with pytest.raises(ValueError, match='differs'):
        restore_session(base, resign(document))


def test_preview_not_saved_and_undo_removes_recipe():
    editor = session()
    original = editor.export_text()
    receipt = editor.publish(compute(editor))
    with pytest.raises(ValueError, match='preview'):
        editor.export_text()
    editor.apply(receipt['token'])
    editor.undo()
    assert editor.export_text() == original


def test_duplicate_keys_rejected():
    with pytest.raises(ValueError, match='duplicate'):
        restore_session(session().current(), '{"payload":{},"payload":{},"sha256":"x"}')


def test_restore_checks_intermediate_edits_and_preserves_inspected_undo():
    editor = session()
    base = editor.current()
    for _ in range(2):
        editor.apply(editor.publish(compute(editor))['token'])
    checked = []
    def inspect(before, result):
        checked.append(result['candidate']['summary']['geometry_sha256'])
        result['candidate']['summary']['radius_edit']['neighbor_contact'] = 'PASS'
    restored = restore_session(base, editor.export_text(), inspect_operation=inspect)
    assert len(checked) == 2
    assert restored.undo()['summary']['radius_edit']['neighbor_contact'] == 'PASS'
    def reject_first(before, result):
        raise ValueError('Intermediate contact')
    with pytest.raises(ValueError, match='Intermediate'):
        restore_session(base, editor.export_text(), inspect_operation=reject_first)
    assert np.array_equal(base['vertices_mm'], session().current()['vertices_mm'])
