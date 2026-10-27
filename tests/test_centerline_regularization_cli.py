import json

import pytest

from vv_toolbox.case_cli import main
from vv_toolbox.case_io import load_case, save_case
from test_radius_regularization import base


def test_centerline_cli_separate_case_and_source_guard(tmp_path,capsys):
    case = base()
    for i, point in enumerate(case['edges'][-1]['centerline_mm'][2:-2],start=2):
        point[1] = .05 if i%2 else -.05
    source,parameters,output = [tmp_path/name for name in ('input.json','parameters.json','output.json')]
    revision = save_case(source,case)
    original = source.read_bytes()
    parameters.write_text(json.dumps(dict(edge_ids=['bridge'],sigma_mm=.5,sample_spacing_mm=.1,
                                        max_displacement_mm=.2,case_id='smooth')))
    assert main(['smooth-centerlines',str(source),str(parameters),str(output)]) == 0
    result,_ = load_case(output)
    assert result['edges'][-1]['centerline_mm'] != case['edges'][-1]['centerline_mm']
    assert result['edges'][-1]['centerline_mm'][:2] == case['edges'][-1]['centerline_mm'][:2]
    assert result['edges'][-1]['centerline_mm'][-2:] == case['edges'][-1]['centerline_mm'][-2:]
    assert result['edges'][-1]['radii_mm'] == case['edges'][-1]['radii_mm']
    with pytest.raises(SystemExit):
        main(['smooth-centerlines',str(source),str(parameters),str(source),'--expected-revision',revision])
    assert source.read_bytes() == original
