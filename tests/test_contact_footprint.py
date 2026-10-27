import numpy as np
import pytest

from vv_toolbox.contact_footprint import compare_contact_footprints


def triangles():
    return np.array([[[0,0,0],[1,0,0],[0,1,0]],
                     [[2,0,0],[4,0,0],[2,2,0]],
                     [[5,0,0],[6,0,0],[5,1,0]]],dtype=float)


def test_reference_face_union_not_pair_multiplicity_controls_area():
    result=compare_contact_footprints(triangles(),[0,0,1],[1,2,2])
    assert result['before']['support_area_mm2']==2.5
    assert result['after']['support_area_mm2']==2.5
    assert result['retained']['face_ids']==[1]
    assert result['lost']['face_ids']==[0] and result['gained']['face_ids']==[2]
    assert result['face_jaccard']==pytest.approx(1/3)
    assert result['before']['support_centroid_mm']==pytest.approx([2.2,.6,0])


def test_empty_and_identical_sets_do_not_fabricate_displacement():
    empty=compare_contact_footprints(triangles(),[],[])
    assert empty['face_jaccard'] is None and empty['support_centroid_shift_mm'] is None
    assert compare_contact_footprints(triangles(),[1],[1])['support_centroid_shift_mm']==0
    assert compare_contact_footprints(triangles(),[1],[])['after']['support_centroid_mm'] is None


@pytest.mark.parametrize('ids',[[True],[-1],[3],[.5]])
def test_invalid_reference_indices_rejected(ids):
    with pytest.raises(ValueError):compare_contact_footprints(triangles(),ids,[])
