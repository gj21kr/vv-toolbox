from copy import deepcopy
import pytest
from test_bifurcation_surface import design
from vv_toolbox.bifurcation_placement import scan_bifurcation_placement
from vv_toolbox.bifurcation_saccular import bifurcation_saccular_spec
from vv_toolbox.bifurcation_attachment import inspect_bifurcation_attachment


def test_scan_matches_independent_attachment_checks_and_preserves_inputs():
    case,spec=design();before=deepcopy((case,spec))
    report=scan_bifurcation_placement(case,spec,offsets_mm=[-.5,0,.5,1],burial_margin_mm=.15)
    assert 0 in report['passing_offsets_mm'] and -.5 not in report['passing_offsets_mm']
    for sample in report['samples']:
        p=dict(spec['parameters'],neck_center_mm=sample['neck_center_mm'])
        checked=inspect_bifurcation_attachment(case,bifurcation_saccular_spec(case,**p),burial_margin_mm=.15)
        assert sample['interior_rim_samples']==len(checked['rim']['interior_indices'])
        assert sample['insufficient_burial_samples']==len(checked['buried_rim']['insufficient_burial_indices'])
    assert (case,spec)==before and not report['accepted_for_generation']


@pytest.mark.parametrize('offsets',[[],[1,0],[0,0],[float('nan')],[True],list(range(1002))])
def test_invalid_search_inputs_rejected(offsets):
    case,spec=design()
    with pytest.raises(ValueError):scan_bifurcation_placement(case,spec,offsets_mm=offsets,burial_margin_mm=.15)
