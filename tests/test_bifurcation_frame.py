from copy import deepcopy
import numpy as np
import pytest
from test_bifurcation_surface import design
from vv_toolbox.bifurcation_frame import propose_bifurcation_frame


def test_known_spherical_junction_exit_and_input_preservation():
    case,spec=design();before=deepcopy((case,spec))
    result=propose_bifurcation_frame(case,spec,search_mm=5,step_mm=.1,gradient_step_mm=.001)
    assert result['exit_distance_mm']==pytest.approx(2)
    assert abs(result['field_residual_mm'])<1e-9
    for key in ('neck_center_mm','outward_normal','width_direction'):
        assert np.allclose(result['parameters'][key],spec['parameters'][key],atol=1e-6)
    assert (case,spec)==before and not result['accepted_for_generation']


def test_insufficient_search_refuses_to_invent_exit():
    case,spec=design()
    with pytest.raises(ValueError,match='No sampled'):
        propose_bifurcation_frame(case,spec,search_mm=1,step_mm=.1,gradient_step_mm=.001)


@pytest.mark.parametrize('field,value',[('search_mm',0),('step_mm',float('nan')),('gradient_step_mm',True),('step_mm',1e-7)])
def test_invalid_or_excessive_search_rejected(field,value):
    case,spec=design();options=dict(search_mm=5,step_mm=.1,gradient_step_mm=.001);options[field]=value
    with pytest.raises(ValueError):propose_bifurcation_frame(case,spec,**options)
