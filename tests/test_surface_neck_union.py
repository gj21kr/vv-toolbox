from copy import deepcopy
import pytest
import trimesh
from test_lesions import inputs
from test_saccular_spec import parameters
from vv_toolbox.saccular import saccular_spec
from vv_toolbox.surface_neck_union import build_surface_neck_union


def test_closed_union_and_source_preservation():
    case,_=inputs()
    spec=saccular_spec(case,**parameters())
    before=deepcopy((case,spec))
    v,f,meta=build_surface_neck_union(case,spec,spacing_mm=.25,
                                     ray_half_span_mm=1.,ray_step_mm=.05)
    mesh=trimesh.Trimesh(vertices=v,faces=f,process=False)
    assert mesh.is_volume and len(mesh.split())==1
    section=mesh.section(plane_origin=[10,0,0],plane_normal=[1,0,0])
    assert section is not None and len(section.discrete)==1
    assert meta['checks']['context_collision']=='NOT RUN'
    assert len(meta['surface_origin']['face_labels'])==len(f)
    assert meta['surface_origin']['counts']['parent_dominant']>0
    assert meta['surface_origin']['counts']['sac_dominant']>0
    assert meta['surface_origin']['counts']['mixed_or_tied']>0
    assert meta['surface_origin']['counts']['unsupported']==0
    assert (case,spec)==before


def test_coarse_grid_rejected():
    case,_=inputs()
    with pytest.raises(ValueError,match='four samples'):
        build_surface_neck_union(case,saccular_spec(case,**parameters()),
                                 spacing_mm=.5,ray_half_span_mm=1.,ray_step_mm=.05)
