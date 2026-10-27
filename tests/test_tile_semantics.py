from copy import deepcopy
import numpy as np
import pytest
from vv_toolbox.tile_semantics import validate_tile_semantics


def fixture():
    arrays=dict(membership=np.array([[1,1,0,0],[0,1,1,0]],bool),foreground=np.array([1,1,1,0],bool),
        overlap_count=np.array([1,2,1,0],np.uint32),instance=np.array([9,2,2,0],np.uint32),
        anatomical=np.array([3,0,4,0],np.uint32),provenance=np.array([1,3,2,0],np.uint8))
    meta=dict(instances=[dict(instance_id=9,anatomical_label=3,provenance='source'),
                         dict(instance_id=2,anatomical_label=4,provenance='estimated')])
    return arrays,meta


def test_conflicting_labels_mixed_provenance_and_unsorted_instance_rows():
    arrays,meta=fixture();result=validate_tile_semantics(arrays,meta)
    assert result['foreground_voxels']==3 and result['overlapping_voxels']==1
    assert result['instance_voxels']=={'9':2,'2':2}


@pytest.mark.parametrize('key',['foreground','overlap_count','instance','anatomical','provenance'])
def test_semantic_corruption_is_rejected(key):
    arrays,meta=fixture();arrays[key][0]=0
    with pytest.raises(ValueError,match='conflicts'):validate_tile_semantics(arrays,meta)


def test_unknown_label_does_not_disappear_when_overlapping_known_label():
    arrays,meta=fixture();meta['instances'][0]['anatomical_label']=0;arrays['anatomical'][0]=0
    assert validate_tile_semantics(arrays,meta)['status']=='PASS'
