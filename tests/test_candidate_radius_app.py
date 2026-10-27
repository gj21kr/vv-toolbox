from types import SimpleNamespace

import numpy as np
import pytest

from test_candidate_radius_session import session
from vv_toolbox.candidate_radius_app import prepare, publish, action, inspect_result, snapshot_context
import trimesh


def workspace():
    candidate = session().current()
    candidate['summary']['selected_source'] = 'middle'
    return SimpleNamespace(source='candidate', candidate=candidate, generation=1,
        metrics=SimpleNamespace(content=''), graph=None, draw_candidate=lambda: None,
        description=lambda graph: 'candidate')


def preview(w):
    raw = dict(source_name='middle', scale=.9, transition_mm=1., max_displacement_mm=.2)
    editor, snapshot, generation = prepare(w, raw)
    result = editor.compute(snapshot, scale=.9, transition_mm=1., max_displacement_mm=.2)
    other = trimesh.creation.box()
    other.apply_translation([100, 0, 0])
    result = inspect_result(snapshot['candidate'], result, {'other':other})
    return editor, generation, result


def test_app_preview_discard_and_apply_undo():
    w = workspace()
    original = w.candidate['vertices_mm'].copy()
    editor, generation, result = preview(w)
    receipt = publish(w, editor, generation, result)
    assert not np.array_equal(w.candidate['vertices_mm'], original)
    assert np.array_equal(editor.current()['vertices_mm'], original)
    action(w, dict(action='discard', token=receipt['token']))
    assert np.array_equal(w.candidate['vertices_mm'], original)
    w.candidate['summary']['selected_source'] = 'middle'
    editor, generation, result = preview(w)
    receipt = publish(w, editor, generation, result)
    action(w, dict(action='apply', token=receipt['token']))
    assert w.candidate_radius_session.status()['undo_available']
    action(w, dict(action='undo', token=None))
    assert np.array_equal(w.candidate['vertices_mm'], original)


def test_scene_change_discards_computed_candidate():
    w = workspace()
    original = w.candidate['vertices_mm'].copy()
    editor, generation, result = preview(w)
    w.generation += 1
    with pytest.raises(ValueError, match='Scene changed'):
        publish(w, editor, generation, result)
    assert np.array_equal(w.candidate['vertices_mm'], original)
    assert not editor.status()['preview_token']


def test_display_failure_does_not_consume_apply_or_undo():
    w = workspace()
    editor, generation, result = preview(w)
    receipt = publish(w, editor, generation, result)
    w.draw_candidate = lambda: (_ for _ in ()).throw(RuntimeError('display failed'))
    with pytest.raises(RuntimeError):
        action(w, dict(action='apply', token=receipt['token']))
    assert editor.status()['preview_token'] == receipt['token']
    assert not editor.status()['undo_available']


def test_boolean_parameter_rejected():
    w = workspace()
    with pytest.raises(ValueError, match='Numeric'):
        prepare(w, dict(source_name='middle', scale=True, transition_mm=1, max_displacement_mm=1))


def test_nonclear_preview_cannot_be_applied():
    w = workspace()
    editor, generation, result = preview(w)
    result['candidate']['summary']['radius_edit']['neighbor_contact'] = 'UNKNOWN'
    receipt = publish(w, editor, generation, result)
    with pytest.raises(ValueError, match='Context clearance'):
        action(w, dict(action='apply', token=receipt['token']))
    assert not editor.status()['undo_available']


def test_context_uses_modified_surfaces_and_independent_copies():
    w = workspace()
    mesh = trimesh.creation.box()
    def part(name, layer):
        return dict(id=name, layer=layer, vertices=mesh.vertices.copy(), faces=mesh.faces.copy())
    w.atlas = SimpleNamespace(meshes=[part('middle','arterial'), part('neighbor','arterial'),
                                      part('organ','context')])
    w.neck_parts = [part('estimate','systemic_venous')]
    modified = part('neighbor','arterial')
    modified['vertices'] += 10
    w.atlas_modified_parts = {'neighbor':modified}
    context = snapshot_context(w,w.candidate)
    assert set(context) == {'neighbor','estimate'}
    assert np.array_equal(context['neighbor'].vertices, modified['vertices'])
    context['neighbor'].vertices[:] = 99
    assert not np.all(modified['vertices'] == 99)
