import copy
import json
from types import SimpleNamespace

import numpy as np
import pytest

from test_venous_backend import workspace
from vv_toolbox.model import Segment, VesselGraph


def test_reference_is_separate_readonly_source_and_preserves_authored_model(workspace):
    work,_=workspace
    original=copy.deepcopy(work.parameters)
    graph=work.graph
    p=np.array([[0.,0.,0.],[0.,0.,10.]])
    reference=VesselGraph({'r0':p[0],'r1':p[1]},[Segment('reference_path','r0','r1',p,1)],{})
    work.reference=SimpleNamespace(graph=reference,mesh=(np.array([[0.,0.,0.],[1.,0.,0.],[0.,1.,0.]]),np.array([[0,1,2]])))
    work.reference_info=dict(available=True,title='Synthetic reference fixture',sha256='fixture')
    work.server.get_clients=lambda:{}
    work.set_source('reference')
    state=work.snapshot()
    assert state['source']=='reference'
    assert len(state['layers']['arterial']['edges'])==1
    assert not state['layers']['systemic_venous']['edges']
    assert not state['layers']['hepatic_portal']['edges']
    bundle=json.loads(work.export_bundle())
    assert bundle['schema']=='vv-toolbox.reference-workspace/1'
    assert 'venous' not in bundle
    assert work.parameters==original and work.graph is graph
    work.set_source('schematic')
    assert work.snapshot()['layers']['hepatic_portal']['edges']
    assert work.parameters==original and work.graph is graph


def test_missing_reference_does_not_silently_substitute_schematic(workspace):
    work,_=workspace
    with pytest.raises(ValueError):
        work.set_source('reference')
    assert work.source=='schematic'
