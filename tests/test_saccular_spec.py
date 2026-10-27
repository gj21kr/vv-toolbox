from copy import deepcopy
import json

import numpy as np
import pytest

from test_lesions import inputs
from vv_toolbox.saccular import saccular_spec, validate_saccular_spec
from vv_toolbox.case_surface import build_case_surface
from vv_toolbox.lesion_labels import label_lesion_lumen
from vv_toolbox.case_io import save_case
from vv_toolbox.case_cli import main


def parameters():
    return dict(lesion_id='sac', edge_id='e', region='aca', station_mm=10,
                neck_center_mm=[10,2,0], outward_normal=[0,1,0],
                width_direction=[1,0,0], neck_width_mm=2, neck_depth_mm=1,
                height_perpendicular_mm=5, dome_width_mm=4, dome_depth_mm=3,
                blending_extent_mm=.5)


def test_explicit_neck_frame_dimensions_source_binding_and_determinism():
    case, _ = inputs()
    original = deepcopy(case)
    spec = saccular_spec(case, **parameters())
    assert spec == saccular_spec(case, **parameters()) and case == original
    assert validate_saccular_spec(spec, case) == spec
    neck = spec['neck']
    curve = np.asarray(neck['curve_mm'])
    delta = curve - neck['center_mm']
    assert curve.shape == (64, 3)
    np.testing.assert_allclose(delta @ neck['normal'], 0)
    assert np.ptp(curve[:, 0]) == pytest.approx(2)
    assert np.ptp(curve[:, 2]) == pytest.approx(1)
    assert neck['average_diameter_mm'] == 1.5
    assert spec['requested_aspect_ratio_height_over_neck'] == pytest.approx(5/1.5)
    assert spec['parent_anchor']['position_mm'] == [10,0,0]
    assert spec['geometry_status'] == 'NOT GENERATED'
    assert spec['checks']['parent_attachment'] == 'UNKNOWN'
    assert 'lesions' not in case


@pytest.mark.parametrize('change', [
    {'height_perpendicular_mm':True}, {'neck_width_mm':float('nan')},
    {'dome_depth_mm':float('inf')}, {'blending_extent_mm':0},
    {'station_mm':0}, {'station_mm':20}, {'outward_normal':[0,2,0]},
    {'width_direction':[0,1,0]}, {'width_direction':[0,0,0]},
    {'neck_center_mm':[10,True,0]}, {'dome_width_mm':1},
    {'edge_id':'absent'}, {'region':'unknown'}, {'lesion_id':''},
])
def test_invalid_design_inputs_rejected(change):
    case, _ = inputs()
    with pytest.raises(ValueError):
        saccular_spec(case, **dict(parameters(), **change))


def test_stale_parent_and_falsified_generated_status_rejected():
    case, _ = inputs()
    spec = saccular_spec(case, **parameters())
    changed = deepcopy(case)
    changed['edges'][0]['radii_mm'] = [3,3]
    with pytest.raises(ValueError, match='stale'):
        validate_saccular_spec(spec, changed)
    bad = deepcopy(spec)
    bad['geometry_status'] = 'PASS'
    with pytest.raises(ValueError, match='inconsistent'):
        validate_saccular_spec(bad, case)


def test_cli_emits_design_only_and_preserves_snapshot(tmp_path, capsys):
    case, _ = inputs()
    source = tmp_path/'source.json'
    params = tmp_path/'params.json'
    save_case(source, case)
    params.write_text(json.dumps(parameters()))
    before = source.read_bytes()
    assert main(['saccular-spec', str(source), str(params)]) == 0
    spec = json.loads(capsys.readouterr().out)
    validate_saccular_spec(spec, case)
    assert source.read_bytes() == before and spec['geometry_status'] == 'NOT GENERATED'
    bad = deepcopy(spec)
    bad['neck']['curve_mm'][0][0] += .1
    with pytest.raises(ValueError, match='inconsistent'):
        validate_saccular_spec(bad, case)


@pytest.mark.parametrize('kind', ['saccular', 'unimplemented', None])
def test_surface_and_labels_do_not_silently_omit_unsupported_lesions(kind):
    case, _ = inputs()
    case.update(model_kind='synthetic', generation=dict(seed=0,generator_version='test',config={}))
    case['lesions'] = [dict(lesion_id='sac',type=kind,edge_id='e')]
    with pytest.raises(ValueError, match='unsupported lesion geometry'):
        build_case_surface(case, ['e'], spacing_mm=.3)
    with pytest.raises(ValueError, match='unsupported lesion geometry'):
        label_lesion_lumen(None, case, {'e':[1]})
