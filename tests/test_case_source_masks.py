from copy import deepcopy

import numpy as np
import pytest

from test_case_source_surfaces import registered
from vv_toolbox.case_source_surfaces import attach_surfaces
from vv_toolbox.case_surface import build_case_surface
from vv_toolbox.case_masks import build_case_masks

GRID = dict(shape_zyx=(9, 17, 49), spacing_xyz_mm=(.5, .5, .5),
            origin_xyz_mm=(-2., -4., -2.), frame_id='fixture')


def masks(case, **options):
    ids = [e['id'] for e in case['edges']]
    v, f, _ = build_case_surface(case, ids, spacing_mm=.5)
    return build_case_masks(case, ids, v, f, spacing_mm=.5, grid_config=GRID, **options)


def test_source_mask_follows_box_surface_not_circular_radius():
    case, _ = registered()
    volume, lesions, meta, quality = masks(case)
    assert volume.foreground[4, 8, 24]
    assert not volume.foreground[7, 8, 24]  # z=1.5, outside source but inside radius=2 tube
    assert volume.provenance[4, 8, 24] == 1
    assert not lesions.any() and meta['sampling_status'] == 'NOT APPLICABLE'
    assert quality['part_instances'] == {'p': 1}
    assert not volume.anatomical.any()  # Name alone does not authorize A2 labels.


def test_registered_roi_matches_whole_crop_with_explicit_partial_scope():
    case, _ = registered()
    whole, _, _, _ = masks(case)
    v, f, _ = build_case_surface(case, ['e'], spacing_mm=.5)
    grid = dict(shape_zyx=(5, 9, 17), spacing_xyz_mm=(.5, .5, .5),
                origin_xyz_mm=(2., -2., -1.), frame_id='fixture')
    roi, lesions, _, quality = build_case_masks(case, ['e'], v, f, spacing_mm=.5,
                                               grid_config=grid, coverage='roi')
    for name in ('foreground', 'anatomical', 'instance', 'provenance', 'overlap_count'):
        assert np.array_equal(getattr(roi, name), getattr(whole, name)[2:7, 4:13, 8:25])
    assert np.array_equal(roi.membership, whole.membership[:, 2:7, 4:13, 8:25])
    assert roi.grid.origin_xyz_mm == (2., -2., -1.)
    assert quality['coverage'] == 'roi' and quality['surface_bounds_covered'] == 'NOT APPLICABLE'
    assert quality['source_bounds_mm'] != quality['sampled_bounds_mm']
    assert not lesions.any()
    with pytest.raises(ValueError, match='whole output grid'):
        build_case_masks(case, ['e'], v, f, spacing_mm=.5, grid_config=grid)


def test_mixed_sources_keep_overlap_membership_and_provenance():
    case, _ = registered()
    parts = case.pop('surface_parts')
    case['model_kind'] = 'synthetic'
    case['generation'] = dict(seed=0, generator_version='test', config={})
    other = deepcopy(case['edges'][0]); other['id'] = 'other'
    case['edges'].append(other)
    part = deepcopy(parts[0]); part.update(part_id='q', edge_ids=['other'], provenance='estimated')
    parts.append(part)
    case = attach_surfaces(case, parts)
    volume, _, _, quality = masks(case)
    assert volume.provenance[4, 8, 24] == 3
    assert volume.overlap_count[4, 8, 24] == 2
    assert volume.membership[:, 4, 8, 24].all()
    assert quality['part_instances'] == {'p': 1, 'q': 2}


def test_multi_edge_part_is_one_instance_without_invented_partition():
    case, _ = registered()
    parts = case.pop('surface_parts')
    other = deepcopy(case['edges'][0]); other['id'] = 'other'
    case['edges'].append(other); parts[0]['edge_ids'].append('other')
    case = attach_surfaces(case, parts)
    volume, _, _, quality = masks(case)
    assert volume.membership.shape[0] == 1
    assert quality['edge_instances'] == {'e': [1], 'other': [1]}


def test_unregistered_geometry_cannot_be_masked_as_registered_surface():
    case, _ = registered()
    v, f, _ = build_case_surface(case, ['e'], spacing_mm=.5)
    v[0, 0] += .1
    with pytest.raises(ValueError, match='differs'):
        build_case_masks(case, ['e'], v, f, spacing_mm=.5, grid_config=GRID)


def test_distinct_supported_labels_require_actual_surface_partition():
    from vv_toolbox.anatomical_labels import assign_access_labels
    from vv_toolbox.case_io import case_digest
    case, _ = registered()
    parts = case.pop('surface_parts')
    other = deepcopy(case['edges'][0]); other['id'] = 'other'
    case['edges'].append(other); parts[0]['edge_ids'].append('other')
    case = attach_surfaces(case, parts)
    case = assign_access_labels(case, [
        dict(edge_id='e', label_id=13, evidence_refs=['synthetic fixture extent']),
        dict(edge_id='other', label_id=14, evidence_refs=['synthetic fixture extent'])],
        expected_revision=case_digest(case))
    with pytest.raises(ValueError, match='explicit surface partition'):
        masks(case)


def test_memory_budget_includes_lesion_label_array():
    case, _ = registered()
    with pytest.raises(ValueError, match='memory budget'):
        masks(case, max_bytes=1)
