from copy import deepcopy
import numpy as np
import pytest
from test_bifurcation_surface import design
from vv_toolbox.bifurcation_rim import project_bifurcation_rim


def test_spherical_cap_samples_preserve_projection_and_original_spec():
    case,spec=design();before=deepcopy((case,spec))
    result=project_bifurcation_rim(case,spec,lower_mm=-1,upper_mm=1,step_mm=.05)
    assert result['resolved_sample_count']==64
    curve=np.asarray(result['curve_mm']);original=np.asarray(spec['neck']['curve_mm'])
    normal=np.asarray(spec['neck']['normal'])
    np.testing.assert_allclose(np.linalg.norm(curve,axis=1),2,atol=1e-8)
    delta=curve-original
    np.testing.assert_allclose(delta, (delta@normal)[:,None]*normal,atol=1e-8)
    assert not np.allclose(curve,original)
    assert (case,spec)==before and not result['accepted_for_generation']


def test_missing_crossings_do_not_produce_a_contour():
    case,spec=design()
    result=project_bifurcation_rim(case,spec,lower_mm=1,upper_mm=2,step_mm=.1)
    assert result['status']=='UNKNOWN' and result['curve_mm'] is None
    assert result['resolved_sample_count']==0


@pytest.mark.parametrize('options',[dict(lower_mm=1,upper_mm=0,step_mm=.1),
    dict(lower_mm=0,upper_mm=1,step_mm=0),dict(lower_mm=0,upper_mm=1,step_mm=1e-8)])
def test_invalid_projection_inputs_rejected(options):
    case,spec=design()
    with pytest.raises(ValueError):project_bifurcation_rim(case,spec,**options)
