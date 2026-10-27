from copy import deepcopy

import pytest
import trimesh

from vv_toolbox.solid_union import build_solid_union
from vv_toolbox.union_lineage import verify_face_lineage


def fixture():
    a=trimesh.creation.box(extents=[2,2,2])
    b=a.copy();b.apply_translation([1,0,0])
    sources={'a':a,'b':b}
    mesh,report=build_solid_union(sources)
    return mesh,sources,report['face_lineage']


def test_all_output_triangles_have_verified_source():
    mesh,sources,lineage=fixture()
    result=verify_face_lineage(mesh,sources,lineage)
    assert result['status']=='PASS'
    assert sum(r['faces'] for r in result['rows'])==len(mesh.faces)


def test_wrong_source_face_is_not_accepted():
    mesh,sources,lineage=fixture()
    damaged=deepcopy(lineage)
    damaged['source_face_indices']=[0]*len(mesh.faces)
    assert verify_face_lineage(mesh,sources,damaged)['status']=='FAIL'


def test_out_of_range_source_rejected():
    mesh,sources,lineage=fixture()
    lineage['face_source_indices'][0]=99
    with pytest.raises(ValueError):
        verify_face_lineage(mesh,sources,lineage)
