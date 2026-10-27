import pytest
from vv_toolbox.patch_contact_regions import classify_patch_contacts


def test_boundary_and_interior_faces_are_not_confused():
    # A triangle annulus and one central triangular face.
    faces=[[0,1,3],[1,4,3],[1,2,4],[2,5,4],[2,0,5],[0,3,5],[3,4,5]]
    result=classify_patch_contacts(faces,[[0,9],[6,10],[6,11]])
    assert result['boundary_vertex_count']==3
    assert result['boundary_incident_face_ids']==[0]
    assert result['interior_face_ids']==[6] and result['interior_pair_count']==2
    assert result['status']=='INTERIOR_CONTACT'


def test_no_contact_and_invalid_indices():
    assert classify_patch_contacts([[0,1,2]],[])['status']=='NO_RECORDED_CONTACT'
    with pytest.raises(ValueError):classify_patch_contacts([[0,1,2]],[[1,0]])
