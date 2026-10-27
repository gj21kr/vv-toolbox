import numpy as np
import pytest

from vv_toolbox.union_selection import select_union_source


def fixture():
    return (np.array([[0.,0,0],[1,0,0],[1,1,0],[0,1,0],[9,9,9]]),
            np.array([[0,1,2],[0,2,3]]),
            dict(source_names=['a','b'],face_source_indices=[0,1],source_face_indices=[4,8]))


def test_selection_separates_shared_interface_without_mutation():
    v,f,lineage=fixture()
    result=select_union_source(v,f,lineage,'a')
    assert result['face_ids']==[0] and result['source_face_ids']==[4]
    assert result['shared_interface_vertex_ids']==[0,2]
    assert result['exclusive_vertex_ids']==[1]
    assert result['vertex_ids']==[0,1,2]
    assert np.array_equal(f,fixture()[1])


def test_source_partitions_cover_faces_once():
    v,f,lineage=fixture()
    a=select_union_source(v,f,lineage,'a');b=select_union_source(v,f,lineage,'b')
    assert sorted(a['face_ids']+b['face_ids'])==list(range(len(f)))
    assert set(a['exclusive_vertex_ids']).isdisjoint(b['vertex_ids'])


@pytest.mark.parametrize('damage',['name','owner','length'])
def test_incomplete_selection_rejected(damage):
    v,f,lineage=fixture();name='a'
    if damage=='name':name='unknown'
    elif damage=='owner':lineage['face_source_indices'][0]=99
    else:lineage['source_face_indices']=[]
    with pytest.raises(ValueError):select_union_source(v,f,lineage,name)
