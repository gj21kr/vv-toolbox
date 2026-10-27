import numpy as np
import pytest

from vv_toolbox.bridge_resampling import resample_bridge_interior


def test_endpoint_collars_preserved_and_only_interior_resampled():
    theta=np.linspace(0,2*np.pi,12,endpoint=False)
    rings=np.array([np.column_stack([np.cos(theta),np.sin(theta),np.full(12,z)]) for z in range(7)])
    original=rings.copy()
    mesh,report=resample_bridge_interior(rings,samples=8,preserved_rings=2)
    assert np.array_equal(rings,original)
    ids=report['ring_vertex_ids']
    assert [len(x) for x in ids]==[12,12,8,8,8,12,12]
    for i in [0,1,5,6]:assert np.array_equal(mesh.vertices[ids[i]],rings[i])
    assert mesh.is_winding_consistent and report['endpoint_collars_exact']
    assert not mesh.is_watertight


def test_no_interior_is_rejected():
    with pytest.raises(ValueError):resample_bridge_interior(np.zeros((4,12,3)))
