import numpy as np
import pytest
import trimesh

from vv_toolbox.atlas_edit_checks import AtlasEditCheckFailure
from vv_toolbox.interval_candidate import build_interval_candidate


def fixture():
    line = [[0, -5], *[[1, z] for z in range(-5, 6)], [0, 5]]
    mesh = trimesh.creation.revolve(line, sections=16)
    return dict(id='synthetic', vertices=mesh.vertices.copy(), faces=mesh.faces.copy())


def build(part, **overrides):
    settings = dict(start_mm=1., end_mm=5., factor=.9,
                    protected_vertex_ids=[], max_displacement_mm=.3,
                    absolute_scale_tolerance=.08, tangent_half_window_mm=2.,
                    transition_rings=1)
    settings.update(overrides)
    return build_interval_candidate(part, [[0, 0, z] for z in range(-4, 5)], **settings)


def test_pipeline_builds_separate_closed_candidate_and_reports_unchecked_surroundings():
    part = fixture()
    vertices, faces = part['vertices'].copy(), part['faces'].copy()
    candidate = build(part)
    assert candidate['edit_checks']['section_targets']['status'] == 'PASS'
    assert candidate['edit_checks']['surrounding_collision'] == 'NOT RUN'
    assert np.array_equal(part['vertices'], vertices)
    assert np.array_equal(part['faces'], faces)
    assert not np.array_equal(candidate['vertices'], vertices)
    assert np.array_equal(candidate['faces'], faces)


def test_failure_retains_source_even_after_candidate_geometry_was_built():
    part = fixture()
    vertices = part['vertices'].copy()
    with pytest.raises(AtlasEditCheckFailure):
        build(part, absolute_scale_tolerance=0.)
    assert np.array_equal(part['vertices'], vertices)
    assert 'edit_checks' not in part


def test_excess_displacement_never_returns_candidate():
    part = fixture()
    with pytest.raises(AtlasEditCheckFailure, match='bound'):
        build(part, max_displacement_mm=.001)


def test_missing_neighbor_prevents_return_and_preserves_source():
    part = fixture()
    original = part['vertices'].copy()
    with pytest.raises(AtlasEditCheckFailure, match='Neighbor'):
        build(part, neighbors=[], expected_neighbor_ids=['missing'])
    assert np.array_equal(original, part['vertices'])
