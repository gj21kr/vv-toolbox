from copy import deepcopy

import numpy as np
import pytest
import trimesh

from test_case_surface import example
from vv_toolbox.case_contract import validate_case
from vv_toolbox.case_source_surfaces import attach_surfaces
from vv_toolbox.case_surface import build_case_surface
from vv_toolbox.case_io import save_case, load_case


def registered():
    case = example()
    mesh = trimesh.creation.box(extents=[20, 4, 2])
    mesh.vertices += [10, 0, 0]
    part = dict(part_id='p', edge_ids=['e'], frame_id='fixture', provenance='source',
                source_ids=['s'], vertices_mm=mesh.vertices.tolist(), faces=mesh.faces.tolist())
    return attach_surfaces(case, [part]), mesh


def test_exact_non_circular_surface_survives_case_save_and_export(tmp_path):
    case, mesh = registered()
    save_case(tmp_path/'case.json', case)
    loaded, _ = load_case(tmp_path/'case.json')
    vertices, faces, metadata = build_case_surface(loaded, ['e'], spacing_mm=.25)
    assert np.array_equal(vertices, mesh.vertices) and np.array_equal(faces, mesh.faces)
    assert metadata['method'] == 'registered-exact-surfaces'
    assert metadata['provenance'] == 'source' and metadata['union_performed'] is False
    assert np.ptp(vertices, axis=0).tolist() == [20., 4., 2.]


@pytest.mark.parametrize('field', ['geometry', 'radius', 'centerline'])
def test_stale_surface_binding_is_rejected(field):
    case, _ = registered()
    if field == 'geometry':
        case['surface_parts'][0]['vertices_mm'][0][0] += .1
    elif field == 'radius':
        case['edges'][0]['radii_mm'][0] += .1
    else:
        case['edges'][0]['centerline_mm'].insert(1, [10., .1, 0.])
        case['edges'][0]['radii_mm'].insert(1, 2.)
    with pytest.raises(ValueError, match='hash mismatch|paths changed'):
        validate_case(case)


def test_multi_edge_source_part_requires_complete_selection():
    case, _ = registered()
    part = case.pop('surface_parts')[0]
    edge = deepcopy(case['edges'][0]); edge['id'] = 'other'
    case['edges'].append(edge)
    part['edge_ids'].append('other')
    case = attach_surfaces(case, [part])
    with pytest.raises(ValueError, match='explicit segment surface boundaries'):
        build_case_surface(case, ['e'], spacing_mm=.25)
    vertices, faces, metadata = build_case_surface(case, ['e', 'other'], spacing_mm=.25)
    assert len(vertices) == 8 and len(faces) == 12
    assert metadata['parts'][0]['edge_ids'] == ['e', 'other']


def test_derived_surface_cannot_claim_source_case():
    case, _ = registered()
    case['surface_parts'][0]['provenance'] = 'estimated'
    with pytest.raises(ValueError, match='synthetic case'):
        validate_case(case)
