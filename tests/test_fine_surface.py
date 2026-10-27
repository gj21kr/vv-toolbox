import pytest
import numpy as np
from vv_toolbox.model import Segment,VesselGraph
from vv_toolbox.surface import network_mesh
import trimesh


def graph():
    p=np.array([[0.,0.,0.],[0.,0.,3.]])
    return VesselGraph({'a':p[0],'b':p[1]},[Segment('fixture','a','b',p,.6)],{'radius_scale':1.})


def test_explicit_fine_surface_is_closed():
    v,f=network_mesh(graph(),spacing=.15)
    mesh=trimesh.Trimesh(v,f,process=False)
    assert mesh.is_watertight and mesh.is_winding_consistent
    assert abs(mesh.volume)>0


@pytest.mark.parametrize('spacing',[.05,0.,float('nan'),.5])
def test_fine_spacing_guard(spacing):
    with pytest.raises(ValueError,match='spacing'):network_mesh(graph(),spacing=spacing)
