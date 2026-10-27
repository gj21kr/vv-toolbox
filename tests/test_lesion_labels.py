from copy import deepcopy

import numpy as np
import pytest

from vv_toolbox.lesion_labels import label_lesion_lumen
from vv_toolbox.voxel_output import Grid,MaskVolume,crop


def fixture():
    case={'schema':'vv-toolbox.case/1','case_id':'fixture','base_model_id':'fixture',
      'model_kind':'synthetic','generation':{'seed':0,'generator_version':'fixture','config':{}},'split':'unassigned',
      'frame':{'id':'fixture','origin':'fixture','axes':'LPS','units':'mm'},
      'sources':[{'id':'s','sha256':'a'*64,'license_ref':'fixture'}],
      'nodes':{n:{'kind':'unresolved','position_mm':p,'evidence_status':'unresolved'}
                for n,p in [('a',[0,0,0]),('b',[10,0,0])]},
      'edges':[{'id':'e','start':'a','end':'b','source_ids':['s'],'geometry_kind':'estimated',
        'evidence_status':'synthetic_estimate','anatomy':{'artery':'ACA','side':'L','segment':'A2','branch_id':'e'},
        'centerline_mm':[[0,0,0],[10,0,0]],'radii_mm':[1,1]}],
      'lesions':[{'lesion_id':'l','type':'concentric_stenosis','edge_id':'e','support_interval_mm':[3,7]}]}
    shape=(1,2,11)
    membership=np.zeros((2,*shape),dtype=bool)
    membership[0,0,0,:]=True
    membership[1,0,1,:]=True
    volume=MaskVolume(Grid(shape,(1.,1.,1.),(0.,0.,0.),'fixture'),
      np.ones(shape,dtype=bool),np.full(shape,42,dtype=np.uint32),
      np.where(membership[0],1,2).astype(np.uint32),np.full(shape,2,dtype=np.uint8),
      np.ones(shape,dtype=np.uint32),membership,[{'instance_id':1},{'instance_id':2}])
    return case,volume


def test_labels_only_mapped_lumen_anatomy_untouched():
    case,volume=fixture()
    before=volume.anatomical.copy()
    labels,metadata=label_lesion_lumen(volume,case,{'e':[1]})
    assert np.flatnonzero(labels[0,0]).tolist()==[4,5,6]
    assert not labels[0,1].any()
    assert np.array_equal(volume.anatomical,before)
    assert metadata['registry'][0]['sampled_voxels']==3


def test_crop_labels_equal_whole_slice():
    case,volume=fixture()
    whole,_=label_lesion_lumen(volume,case,{'e':[1]})
    part=crop(volume,[0,0,4],[1,2,8])
    labels,_=label_lesion_lumen(part,case,{'e':[1]})
    assert np.array_equal(labels,whole[:,:,4:8])


def test_empty_sampling_unknown():
    case,volume=fixture()
    case['lesions'][0]['support_interval_mm']=[3.1,3.2]
    labels,meta=label_lesion_lumen(volume,case,{'e':[1]})
    assert not labels.any()
    assert meta['status']=='UNKNOWN'


def test_overlap_or_missing_mapping_rejected():
    case,volume=fixture()
    with pytest.raises(ValueError,match='mapping'):
        label_lesion_lumen(volume,case,{})
    another=deepcopy(case['lesions'][0]);another['lesion_id']='other'
    case['lesions'].append(another)
    with pytest.raises(ValueError,match='overlap'):
        label_lesion_lumen(volume,case,{'e':[1]})


def test_archive_preserves_independent_lesion_and_anatomy_arrays(tmp_path):
    import json
    from vv_toolbox.volume_cli import save_volume
    case,volume=fixture()
    labels,meta=label_lesion_lumen(volume,case,{'e':[1]})
    save_volume(tmp_path/'mask.npz',volume,lesion_labels=labels,lesion_metadata=meta)
    with np.load(tmp_path/'mask.npz',allow_pickle=False) as data:
        assert np.array_equal(data['lesion_instance'],labels)
        assert np.all(data['anatomical']==42)
        assert json.loads(str(data['lesion_metadata']))['registry'][0]['lesion_id']=='l'


@pytest.mark.parametrize('explicit_empty',[False,True])
def test_no_declared_lesions_yields_zero_mask_not_a_sampling_claim(explicit_empty):
    case,volume=fixture()
    if explicit_empty:
        case['lesions']=[]
    else:
        case.pop('lesions')
    labels,meta=label_lesion_lumen(volume,case,{'e':[1]})
    assert labels.shape==volume.foreground.shape
    assert labels.dtype==np.uint32 and not labels.any()
    assert meta['registry']==[] and meta['required_lesion_ids']==[]
    assert meta['status']=='PASS'
    assert meta['sampling_status']=='NOT APPLICABLE'
    assert meta['lesion_presence']=='none_declared'
    assert meta['clinical_validity']=='NOT RUN'
    with pytest.raises(ValueError,match='required lesion'):
        label_lesion_lumen(volume,case,{'e':[1]},required_lesion_ids=['missing'])
    with pytest.raises(ValueError,match='budget'):
        label_lesion_lumen(volume,case,{'e':[1]},max_bytes=1)
    with pytest.raises(ValueError,match='mapped edge'):
        label_lesion_lumen(volume,case,{'missing':[1]})


def test_present_lesions_cannot_be_suppressed_with_empty_required_set():
    case,volume=fixture()
    with pytest.raises(ValueError,match='required lesion'):
        label_lesion_lumen(volume,case,{'e':[1]},required_lesion_ids=[])
