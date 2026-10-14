"""Boundary checks for the shared workspace's browser input."""
import copy
import pytest
from vv_toolbox.app import defaults, validate_parameters


def test_local_shapes_and_topology_are_retained():
    raw=defaults()
    raw['vessel_parameters']={'left_aca_a1':{'radius_scale':1.4,'tortuosity':.7}}
    raw['arch_variant']='common_origin'
    raw['absent_communicators']=['acom']
    assert validate_parameters(raw,{'left_aca_a1'})==raw


@pytest.mark.parametrize('field,value', [('radius_scale',float('nan')),('tortuosity',2),('arch_height_ratio',0),('arch_variant','arbitrary'),('absent_communicators',['unknown'])])
def test_rejects_invalid_model_controls(field,value):
    raw=defaults();raw[field]=value
    with pytest.raises(ValueError):validate_parameters(raw,set())


def test_rejects_unknown_vessels_and_extra_parameters():
    raw=defaults();raw['vessel_parameters']={'foreign':{'radius_scale':1,'tortuosity':.3}}
    with pytest.raises(ValueError):validate_parameters(raw,set())
    raw=defaults();raw['path']='anything'
    with pytest.raises(ValueError):validate_parameters(raw,set())


def test_validation_does_not_mutate_input():
    raw=defaults();before=copy.deepcopy(raw)
    validate_parameters(raw,set())
    assert raw==before
