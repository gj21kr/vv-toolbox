from copy import deepcopy

import pytest

from vv_toolbox.atlas_case import build_atlas_case


def inputs():
    preview = {'schema': 'vv-toolbox.atlas-centerlines/1', 'algorithm': 'fixture', 'units': 'mm assumed',
               'parts': [{'id': 'p', 'layer': 'arterial'}, {'id': 'missing', 'layer': 'arterial'}],
               'nodes': [{'id': 'n0', 'part_id': 'p', 'point': [0, 0, 0], 'kind': 'cycle'}],
               'edges': [{'id': 'e', 'part_id': 'p', 'start': 'n0', 'end': 'n0',
                          'provenance': 'source-mesh-voxel-medial', 'pitch': 1,
                          'points': [[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 0, 0]],
                          'radii': [1, 1, 1, 1]}],
               'links': [{'part_a': 'p', 'part_b': 'other', 'status': 'candidate'}]}
    binding = {'artery': 'ACA', 'side': 'L', 'identity_refs': ['fixture identity']}
    options = dict(source={'id': 'atlas', 'sha256': 'a'*64, 'license_ref': 'fixture'},
                   extraction_source={'id': 'preview', 'sha256': 'b'*64, 'license_ref': 'fixture'},
                   frame={'id': 'fixture', 'units': 'mm', 'axes': 'LPS', 'origin': 'fixture', 'confirmed': True},
                   case_id='case', base_model_id='base')
    return preview, {'p': binding, 'missing': deepcopy(binding)}, options


def test_candidates_cycles_missing_parts_and_uncertainty_preserved():
    preview, bindings, options = inputs()
    before = deepcopy(preview)
    case = build_atlas_case(preview, bindings, **options)
    assert len(case['edges']) == 1
    assert case['edges'][0]['start'] == case['edges'][0]['end']
    assert case['edges'][0]['anatomy']['segment'] == 'unresolved'
    assert case['nodes']['n0']['kind'] == 'unresolved'
    assert case['inspection']['missing_path_parts'] == ['missing']
    assert len(case['inspection']['candidate_links']) == 1
    case['inspection']['candidate_links'][0]['status'] = 'changed'
    assert preview == before


def test_unconfirmed_frame_rejected():
    preview, bindings, options = inputs()
    options['frame']['confirmed'] = False
    with pytest.raises(ValueError, match='confirmed'):
        build_atlas_case(preview, bindings, **options)


def test_degenerate_loop_quarantined_without_source_repair():
    preview, bindings, options = inputs()
    bad = deepcopy(preview['edges'][0])
    bad.update(id='bad', points=[[0, 0, 0], [1, 0, 0], [0, 0, 0]], radii=[1, 1, 1])
    preview['edges'].append(bad)
    before = deepcopy(preview)
    result = build_atlas_case(preview, bindings, **options)
    assert len(result['edges']) == 1
    rejection = result['inspection']['rejected_extraction_edges'][0]
    assert rejection['reason'] == 'degenerate_self_loop'
    assert rejection['original_edge'] == bad
    assert preview == before


@pytest.mark.parametrize('defect', ['synthetic', 'cross_part', 'duplicate', 'venous'])
def test_bad_sources_rejected(defect):
    preview, bindings, options = inputs()
    if defect == 'synthetic':
        preview['edges'][0]['provenance'] = 'estimated-connector'
    elif defect == 'cross_part':
        preview['nodes'][0]['part_id'] = 'other'
    elif defect == 'duplicate':
        preview['nodes'].append(deepcopy(preview['nodes'][0]))
    else:
        preview['parts'][0]['layer'] = 'systemic_venous'
    with pytest.raises(ValueError):
        build_atlas_case(preview, bindings, **options)
