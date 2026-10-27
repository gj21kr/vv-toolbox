import numpy as np
import pytest
from vv_toolbox.surface_origin import label_union_faces


def test_source_ownership_and_mixed_region_are_retained():
    parent=np.zeros((5,5,5),bool);parent[:3]=True
    sac=np.zeros_like(parent);sac[2:]=True
    vertices=np.array([[0,1,1],[0,2,1],[0,1,2],
                       [4,1,1],[4,2,1],[4,1,2],
                       [2,1,1],[2,2,1],[2,1,2]],float)
    result=label_union_faces(vertices,[[0,1,2],[3,4,5],[6,7,8]],parent,sac,1)
    assert result['face_labels']==[0,1,2]
    assert sum(result['counts'].values())==3
    assert result['anatomical_neck_boundary']=='UNKNOWN'


def test_out_of_grid_cannot_inherit_border_label():
    mask=np.ones((3,3,3),bool)
    with pytest.raises(ValueError,match='outside'):
        label_union_faces([[-1,0,0],[0,1,0],[0,0,1]],[[0,1,2]],mask,mask,1)
