import copy

import pytest
import trimesh

from test_candidate_radius_session import session, compute
from test_candidate_radius_app import workspace
from vv_toolbox.candidate_radius_session import CandidateRadiusSession
from vv_toolbox.candidate_radius_app import inspect_result, publish, action
from vv_toolbox.candidate_radius_io import base_identity


def candidate(outside=False):
    result = session().current()
    result['summary'].pop('carotid_union')
    result['summary']['access_union'] = dict(lineage_faces=123, centerline_status='PASS',
        checked_paths=99, checked_segments=99, context_status='PASS', context_completed=99,
        context_neighbors=99, contacts=['old'], unknown=['old'])
    result['summary']['access_graph'] = dict(edges=2, revision='graph')
    result['edges'] = [dict(id='first', centerline_mm=[[0, 0, 0], [0, 0, 2]]),
                       dict(id='second', centerline_mm=[[10 if outside else 0, 0, 2], [0, 0, 4]])]
    return result


def test_all_paths_rechecked_and_previous_surface_audits_invalidated():
    base = candidate()
    result = compute(CandidateRadiusSession(base))
    summary = result['candidate']['summary']
    assert 'carotid_union' not in summary
    audit = summary['access_union']
    assert audit['centerline_status'] == 'PASS' and audit['checked_paths'] == 2
    assert audit['lineage_faces'] == 'NOT RUN'
    assert audit['context_status'] == 'NOT RUN' and audit['context_completed'] == 0
    assert audit['contacts'] == audit['unknown'] == []
    paths = result['audit']['centerline_containment']
    assert paths['geometry_sha256'] == summary['geometry_sha256']
    assert {r['edge_id'] for r in paths['rows']} == {'first', 'second'}
    assert base['summary']['access_union']['checked_paths'] == 99


def test_outside_path_blocks_apply_even_with_clear_neighbors():
    w = workspace()
    w.candidate = candidate(outside=True)
    editor = CandidateRadiusSession(w.candidate)
    w.candidate_radius_session = editor
    result = compute(editor)
    other = trimesh.creation.box()
    other.apply_translation([100, 0, 0])
    inspect_result(editor.current(), result, {'other': other})
    assert result['audit']['neighbor_contact'] == 'PASS'
    assert result['audit']['centerline_containment']['status'] == 'FAIL'
    receipt = publish(w, editor, w.generation, result)
    with pytest.raises(ValueError, match='centerline clearance'):
        action(w, dict(action='apply', token=receipt['token']))
    action(w, dict(action='discard', token=receipt['token']))
    assert not editor.status()['undo_available']


def test_incomplete_graph_cannot_be_edited():
    base = candidate()
    base['edges'].pop()
    with pytest.raises(ValueError, match='Complete access graph'):
        compute(CandidateRadiusSession(base))


def test_recipe_identity_includes_full_access_graph():
    base = candidate()
    changed = copy.deepcopy(base)
    changed['edges'][1]['centerline_mm'][0][0] = 10
    assert base_identity(base) != base_identity(changed)


def test_progress_preserves_stage_counts_and_cannot_mutate_results():
    editor = CandidateRadiusSession(candidate())
    events = []
    def progress(event):
        events.append(dict(event))
        event['completed'] = -1
    result = editor.compute(editor.snapshot('middle'), scale=.9, transition_mm=1.,
                            max_displacement_mm=.2, progress=progress)
    assert events == [dict(phase='geometry', completed=0, total=1),
                      dict(phase='geometry', completed=1, total=1),
                      dict(phase='centerlines', completed=0, total=2),
                      dict(phase='centerlines', completed=1, total=2),
                      dict(phase='centerlines', completed=2, total=2)]
    other = trimesh.creation.box()
    other.apply_translation([100, 0, 0])
    inspect_result(editor.current(), result, {'other': other}, progress=progress)
    assert events[-2:] == [dict(phase='context', completed=0, total=1),
                          dict(phase='context', completed=1, total=1)]
    assert result['audit']['centerline_containment']['status'] == 'PASS'
    assert result['audit']['neighbor_contact'] == 'PASS'
