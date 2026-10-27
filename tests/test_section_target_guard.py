from copy import deepcopy

import numpy as np
import pytest
import trimesh

from vv_toolbox.atlas_edit_checks import AtlasEditCheckFailure, require_section_target_match
from vv_toolbox.profile_scale import scale_section
from vv_toolbox.source_sections import extract_source_sections


def fixture():
    mesh = trimesh.creation.box(extents=[2, 4, 8])
    points = [[0, 0, -1], [0, 0, 0], [0, 0, 1]]
    source = extract_source_sections(mesh, points)['profiles']
    requested = [scale_section(source[0], .5)]
    return mesh, points, source, requested


def run(candidate, points, source, requested):
    return require_section_target_match(candidate, source, requested, points,
                                        absolute_scale_tolerance=1e-8,
                                        tangent_half_window_mm=None)


def test_real_candidate_area_is_measured_not_trusted_from_metadata():
    mesh, points, source, requested = fixture()
    candidate = dict(vertices=mesh.vertices.copy(), faces=mesh.faces.copy(),
                     edit_checks={'section_targets': {'status': 'PASS'}})
    with pytest.raises(AtlasEditCheckFailure, match='FAIL'):
        run(candidate, points, source, requested)
    assert candidate['edit_checks']['section_targets']['status'] == 'FAIL'


def test_correct_shape_passes_and_inputs_are_preserved():
    mesh, points, source, requested = fixture()
    original = mesh.vertices.copy()
    saved = deepcopy(source)
    changed = mesh.vertices.copy()
    changed[:, :2] *= .5
    candidate = dict(vertices=changed, faces=mesh.faces.copy())
    result = run(candidate, points, source, requested)
    assert result['status'] == 'PASS'
    assert source == saved and np.array_equal(mesh.vertices, original)
    assert np.array_equal(candidate['vertices'], changed)


def test_unmeasurable_candidate_fails_closed():
    mesh, points, source, requested = fixture()
    candidate = dict(vertices=mesh.vertices + [100, 0, 0], faces=mesh.faces.copy())
    with pytest.raises(AtlasEditCheckFailure, match='UNKNOWN'):
        run(candidate, points, source, requested)
