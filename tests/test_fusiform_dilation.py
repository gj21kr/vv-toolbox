from copy import deepcopy
import json

import numpy as np
import pytest
import trimesh

from test_lesions import inputs
from vv_toolbox.lesions import fusiform_dilation, concentric_stenosis
from vv_toolbox.case_surface import build_case_surface
from vv_toolbox.case_io import save_case, load_case
from vv_toolbox.case_cli import main


def parameters():
    _, kwargs=inputs()
    kwargs.pop('severity_percent')
    kwargs.pop('measurement_method')
    return dict(kwargs, diameter_ratio=2, sample_spacing_mm=.25)


def test_dilation_preserves_source_and_records_expanded_support():
    case,_=inputs()
    before=deepcopy(case)
    result=fusiform_dilation(case,**parameters())
    assert case==before and result==fusiform_dilation(case,**parameters())
    lesion=result['lesions'][0]
    assert lesion['type']=='fusiform_dilation' and 'requested_percent' not in lesion
    assert lesion['profile_center_diameter_mm']==8
    assert lesion['profile_center_diameter_ratio']==2
    assert max(c['radius_mm'] for c in lesion['support_capsules_mm'])==4
    for p,r in zip(result['edges'][0]['centerline_mm'],result['edges'][0]['radii_mm']):
        if p[0]<=6 or p[0]>=14: assert r==2
    assert result['nodes']==before['nodes'] and result['split']==before['split']


@pytest.mark.parametrize('ratio',[True,1,0,float('nan'),float('inf')])
def test_invalid_ratio_rejected(ratio):
    case,_=inputs()
    with pytest.raises(ValueError):fusiform_dilation(case,**dict(parameters(),diameter_ratio=ratio))


def test_expanded_radius_blocks_other_lesions_on_nearby_parallel_vessel():
    case,_=inputs()
    second=deepcopy(case['edges'][0]);second.update(id='parallel',start='c',end='d')
    second['centerline_mm']=[[0,6,0],[20,6,0]]
    second['anatomy']['branch_id']='parallel'
    case['edges'].append(second)
    for n,p in [('c',[0,6,0]),('d',[20,6,0])]:
        case['nodes'][n]=dict(case['nodes']['a'],position_mm=p)
    derived=fusiform_dilation(case,**parameters())
    _,stenosis=inputs()
    # Baseline radii sum 4 would clear six mm; expanded support reaches six.
    with pytest.raises(ValueError,match='clearance'):
        concentric_stenosis(derived,**dict(stenosis,edge_id='parallel',case_id='second',lesion_id='l2'))


def test_surface_mask_labels_and_cli_roundtrip(tmp_path):
    case,_=inputs()
    source=tmp_path/'source.json';params=tmp_path/'params.json';output=tmp_path/'dilated.json'
    save_case(source,case);params.write_text(json.dumps(parameters()))
    assert main(['dilation',str(source),str(params),str(output)])==0
    derived,_=load_case(output)
    vertices,faces,metadata=build_case_surface(derived,['e'],spacing_mm=.2)
    mesh=trimesh.Trimesh(vertices=vertices,faces=faces,process=False)
    section=mesh.section(plane_origin=[10,0,0],plane_normal=[1,0,0])
    assert mesh.is_volume and len(section.discrete)==1
    assert np.all(np.abs(np.ptp(section.discrete[0][:,1:],axis=0)-8)<.3)
    from vv_toolbox.voxel_output import Grid,Surface,voxelize
    from vv_toolbox.lesion_labels import label_lesion_lumen
    grid=Grid((9,9,5),(1,1,1),(8,-4,-4),'fixture')
    volume=voxelize([Surface(1,0,'estimated',vertices,faces,'fixture','manual dilation')],grid)
    labels,meta=label_lesion_lumen(volume,derived,{'e':[1]})
    assert meta['status']=='PASS'
    assert volume.foreground[4,7,2] and labels[4,7,2]==1  # beyond original radius two
    assert np.all(labels[~volume.foreground]==0)
    assert metadata['provenance']=='estimated'


def test_mixed_lesion_batch_preserves_both_operations(tmp_path):
    from vv_toolbox.batch import generate_lesion_batch
    case, stenosis=inputs()
    case['nodes']['b']['position_mm']=[50,0,0]
    case['edges'][0]['centerline_mm'][-1]=[50,0,0]
    dilation=parameters()
    for p in [dilation,stenosis]:
        p.pop('seed');p.pop('case_id')
    dilation.update(type='fusiform_dilation',center_mm=12,length_mm=6)
    stenosis.update(type='concentric_stenosis',center_mm=36,length_mm=6,lesion_id='narrowing')
    candidates=[[dict(dilation,type='unsupported')],[dilation,stenosis]]
    report=generate_lesion_batch(case,candidates,tmp_path/'mixed',target_count=1,
                                 max_attempts=2,seed=9,spacing_mm=.3)
    assert [a['status'] for a in report['attempts']]==['FAIL','PASS']
    restored,_=load_case(tmp_path/'mixed/case-00000/case.snapshot.json')
    assert [l['type'] for l in restored['lesions']]==['fusiform_dilation','concentric_stenosis']
    assert len(restored['lesions'][1]['spacing_checks'])==1
    assert restored['base_model_id']==case['base_model_id']
