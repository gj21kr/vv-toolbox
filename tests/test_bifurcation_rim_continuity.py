from copy import deepcopy
import pytest
from test_bifurcation_surface import design
from vv_toolbox.bifurcation_rim import project_bifurcation_rim
from vv_toolbox.bifurcation_rim_continuity import inspect_projected_rim


def inputs():
    case,spec=design()
    projection=project_bifurcation_rim(case,spec,lower_mm=-1,upper_mm=1,step_mm=.05)
    return case,spec,projection


def test_every_chord_including_closure_has_residual_bound():
    case,spec,projection=inputs()
    report=inspect_projected_rim(case,spec,projection,tolerance_mm=.02)
    assert report['status']=='PASS' and report['closed_chord_count']==64
    assert report['chords'][-1]['chord_index']==63
    assert report['maximum_continuous_absolute_field_bound_mm']<=.02
    assert report['field_lipschitz_bound']==1
    assert not report['accepted_for_generation']


def test_tight_tolerance_detects_actual_chord_sagitta():
    case,spec,projection=inputs()
    report=inspect_projected_rim(case,spec,projection,tolerance_mm=.0001)
    assert report['status']=='FAIL'
    assert max(r['maximum_sampled_absolute_field_mm'] for r in report['chords'])>.0001


def test_tampering_and_budget_overrun_are_rejected():
    case,spec,projection=inputs();altered=deepcopy(projection)
    altered['curve_mm'][0][0]+=1
    with pytest.raises(ValueError,match='differs'):
        inspect_projected_rim(case,spec,altered,tolerance_mm=.02)
    with pytest.raises(ValueError,match='budget'):
        inspect_projected_rim(case,spec,projection,tolerance_mm=.02,max_samples=2)
