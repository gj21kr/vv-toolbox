from copy import deepcopy

import pytest

from vv_toolbox.junction_continuity import inspect_bridge_continuity
from vv_toolbox.synthetic_routes import build_synthetic_routes
from test_synthetic_routes import fixture


def generated():
    case, spec = fixture()
    return build_synthetic_routes(case, spec, case_id='joined')


def test_both_attachments_report_real_measures_without_anatomical_claim():
    case = generated()
    before = deepcopy(case)
    report = inspect_bridge_continuity(case, max_angle_deg=1, max_radius_jump_mm=0)
    assert report['status']=='PASS' and len(report['attachments'])==2
    assert all(a['position_gap_mm']==0 and a['radius_jump_mm']==0 for a in report['attachments'])
    assert report['surface_smoothness']=='NOT RUN'
    assert report['anatomical_connection']=='UNKNOWN'
    assert case==before


@pytest.mark.parametrize('fault', ['angle_start','angle_end','radius_start','radius_end'])
def test_break_at_either_attachment_fails(fault):
    case = generated()
    bridge = case['edges'][-1]
    end = fault.endswith('end')
    if fault.startswith('angle'):
        bridge['centerline_mm'][-2 if end else 1][1] += 2
    else:
        bridge['radii_mm'][-1 if end else 0] += .5
    report = inspect_bridge_continuity(case, max_angle_deg=5, max_radius_jump_mm=.01)
    assert report['status']=='FAIL'
    assert report['attachments'][1 if end else 0]['status']=='FAIL'


@pytest.mark.parametrize('angle,radius', [(float('nan'),0), (181,0), (5,-1), (True,0)])
def test_invalid_thresholds_rejected(angle,radius):
    with pytest.raises(ValueError): inspect_bridge_continuity(generated(), max_angle_deg=angle,max_radius_jump_mm=radius)


def test_cli_inspects_saved_geometry_and_fails_broken_attachment(tmp_path, capsys):
    import json
    from vv_toolbox.case_cli import main
    from vv_toolbox.case_io import save_case
    case = generated()
    case['edges'][-1]['radii_mm'][-1] += 1
    path = tmp_path/'case.json'
    revision = save_case(path, case)
    assert main(['bridge-continuity',str(path),'--max-angle-deg','5',
                 '--max-radius-jump-mm','0.01']) == 1
    report = json.loads(capsys.readouterr().out)
    assert report['case_revision'] == revision
    assert report['attachments'][1]['radius_jump_mm'] == 1
