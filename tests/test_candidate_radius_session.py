import numpy as np
import pytest

from test_union_radius import fixture
from vv_toolbox.candidate_radius_session import CandidateRadiusSession


def session():
    mesh, lineage = fixture()
    return CandidateRadiusSession(dict(
        vertices_mm=mesh.vertices.copy(), faces=mesh.faces.copy(), face_lineage=lineage,
        source_centerlines=dict(middle=dict(points_mm=[[0, 0, 0], [0, 0, 4]], case_revision='rev')),
        summary=dict(revision='rev', surface_sha256='source', carotid_union=dict(lineage_faces=123))))


def compute(editor):
    return editor.compute(editor.snapshot('middle'), scale=.9,
                          transition_mm=1., max_displacement_mm=.2)


def test_preview_apply_undo_preserve_original_and_invalidate_old_inspection():
    editor = session()
    original = editor.current()
    result = compute(editor)
    token = editor.publish(result)['token']
    assert np.array_equal(editor.current()['vertices_mm'], original['vertices_mm'])
    assert not np.array_equal(editor.preview()['vertices_mm'], original['vertices_mm'])
    changed = editor.apply(token)
    assert changed['summary']['carotid_union']['lineage_faces'] == 'NOT RUN'
    assert 'surface_sha256' not in changed['summary']
    assert changed['summary']['radius_edit']['neighbor_contact'] == 'NOT RUN'
    restored = editor.undo()
    assert np.array_equal(restored['vertices_mm'], original['vertices_mm'])
    assert restored['summary'] == original['summary']


def test_old_computation_cannot_publish_after_apply_or_undo():
    editor = session()
    result = compute(editor)
    token = editor.publish(result)['token']
    editor.apply(token)
    with pytest.raises(ValueError, match='changed'):
        editor.publish(result)
    editor.undo()
    with pytest.raises(ValueError, match='changed'):
        editor.publish(result)


def test_token_replacement_and_detached_result():
    editor = session()
    result = compute(editor)
    first = editor.publish(result)['token']
    second = editor.publish(result)['token']
    with pytest.raises(ValueError, match='token'):
        editor.apply(first)
    result['candidate']['vertices_mm'][:] = 999
    assert not np.all(editor.preview()['vertices_mm'] == 999)
    editor.apply(second)
    with pytest.raises(ValueError, match='token'):
        editor.apply(second)


def test_missing_path_and_discard():
    editor = session()
    with pytest.raises(ValueError, match='unavailable'):
        editor.snapshot('unknown')
    editor.publish(compute(editor))
    editor.discard()
    with pytest.raises(ValueError, match='No radius preview'):
        editor.preview()


def test_successive_edits_keep_parent_geometry_and_reverse_in_order():
    editor = session()
    first = editor.apply(editor.publish(compute(editor))['token'])
    second = editor.apply(editor.publish(compute(editor))['token'])
    assert second['summary']['parent_surface_sha256'] == first['summary']['geometry_sha256']
    assert np.array_equal(editor.undo()['vertices_mm'], first['vertices_mm'])
    assert editor.undo()['summary']['surface_sha256'] == 'source'
