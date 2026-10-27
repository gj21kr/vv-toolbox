from copy import deepcopy

import pytest

from vv_toolbox.atlas_annotations import new_annotation_document
from vv_toolbox.case_contract import validate_case
from vv_toolbox.segment_materialization import materialize_segments


def fixture():
    case = {'schema': 'vv-toolbox.case/1', 'case_id': 'fixture', 'base_model_id': 'fixture',
        'model_kind': 'source', 'split': 'unassigned', 'generation': None,
        'frame': {'id': 'fixture', 'origin': 'fixture', 'units': 'mm', 'axes': 'LPS'},
        'sources': [{'id': 'source', 'sha256': 'a'*64, 'license_ref': 'fixture'}],
        'nodes': {n: {'kind': 'unresolved', 'position_mm': p, 'evidence_status': 'unresolved'}
                  for n, p in [('a', [0, 0, 0]), ('b', [4, 0, 0])]},
        'edges': [{'id': 'e', 'start': 'a', 'end': 'b', 'source_ids': ['source'],
            'geometry_kind': 'source', 'evidence_status': 'unresolved',
            'anatomy': {'artery': 'ACA', 'side': 'L', 'segment': 'unresolved', 'branch_id': 'branch'},
            'centerline_mm': [[0, 0, 0], [2, 0, 0], [4, 0, 0]], 'radii_mm': [1, 2, 3]}]}
    doc = new_annotation_document('source', 'a'*64, coordinate_frame_id='fixture',
                                  units='mm', frame_confirmed=True, units_confirmed=True)
    ids = ['B.L.ACA.A1_A2', 'B.L.ACA.A2_A3']
    for b in doc['boundaries']:
        if b['boundary_id'] in ids:
            b.update(position=[1 if b['boundary_id'] == ids[0] else 3, 0, 0],
                     branch_id='branch', evidence_status='landmark_reviewed', source_refs=['fixture review'])
    assignments = [{'edge_id': 'e', 'labels': ['A1', 'A2', 'A3'],
                    'extent_review_refs': ['fixture full extent review'],
                    'cuts': [{'boundary_id': ident, 'interval_index': i, 'fraction': .5}
                             for i, ident in enumerate(ids)]}]
    return case, doc, assignments


def test_splits_preserve_geometry_radius_incidence_and_unknown_connectivity():
    case, doc, assignments = fixture()
    before = deepcopy((case, doc, assignments))
    result = materialize_segments(case, doc, assignments, tolerance_mm=0)
    assert (case, doc, assignments) == before
    assert [e['anatomy']['segment'] for e in result['edges']] == ['A1', 'A2', 'A3']
    assert result['edges'][1]['centerline_mm'] == [[1, 0, 0], [2, 0, 0], [3, 0, 0]]
    assert result['edges'][1]['radii_mm'] == [1.5, 2, 2.5]
    assert all(e['evidence_status'] == 'unresolved' for e in result['edges'])
    incidence = validate_case(result)
    assert len(incidence[result['edges'][0]['end']]) == 2


@pytest.mark.parametrize('defect', ['region', 'branch', 'fingerprint', 'frame', 'position', 'labels', 'order', 'extent'])
def test_incompatible_annotation_is_atomic(defect):
    case, doc, assignments = fixture()
    b = next(b for b in doc['boundaries'] if b['boundary_id'] == 'B.L.ACA.A1_A2')
    if defect == 'region': b['localization_scope'] = 'region_only'
    if defect == 'branch': b['branch_id'] = 'other'
    if defect == 'fingerprint': doc['source']['sha256'] = 'b'*64
    if defect == 'frame': doc['coordinate_frame']['units_confirmed'] = False
    if defect == 'position': b['position'][1] = 10
    if defect == 'labels': assignments[0]['labels'][0] = 'M1'
    if defect == 'order': assignments[0]['cuts'].reverse()
    if defect == 'extent': assignments[0].pop('extent_review_refs')
    before = deepcopy(case)
    with pytest.raises(ValueError):
        materialize_segments(case, doc, assignments, tolerance_mm=.01)
    assert case == before


def test_cut_on_existing_sample_has_no_duplicate_vertex():
    case, doc, assignments = fixture()
    b = next(b for b in doc['boundaries'] if b['boundary_id'] == 'B.L.ACA.A1_A2')
    b['position'] = [2, 0, 0]
    assignments[0]['cuts'][0].update(interval_index=1, fraction=0)
    result = materialize_segments(case, doc, assignments, tolerance_mm=0)
    assert result['edges'][0]['centerline_mm'] == [[0, 0, 0], [2, 0, 0]]
    assert result['edges'][1]['centerline_mm'] == [[2, 0, 0], [3, 0, 0]]
