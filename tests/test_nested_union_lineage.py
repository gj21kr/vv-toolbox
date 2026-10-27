from copy import deepcopy

import pytest
import trimesh

from vv_toolbox.solid_union import build_solid_union
from vv_toolbox.union_lineage import compose_face_lineage, verify_face_lineage


def nested_fixture():
    a=trimesh.creation.box(extents=[2,2,2])
    b=a.copy();b.apply_translation([1,0,0])
    c=a.copy();c.apply_translation([0,1,0])
    parent,first=build_solid_union({'a':a,'b':b})
    result,second=build_solid_union({'parent':parent,'c':c})
    return result,{'a':a,'b':b,'c':c},first['face_lineage'],second['face_lineage']


def test_two_union_stages_trace_to_original_triangles():
    mesh,sources,first,second=nested_fixture()
    original=deepcopy(second)
    flat=compose_face_lineage(second,{'parent':first})
    assert verify_face_lineage(mesh,sources,flat)['status']=='PASS'
    assert second==original


def test_invalid_parent_face_rejected():
    _,_,first,second=nested_fixture()
    index=second['face_source_indices'].index(second['source_names'].index('parent'))
    second['source_face_indices'][index]=len(first['source_face_indices'])
    with pytest.raises(ValueError,match='outside'):
        compose_face_lineage(second,{'parent':first})


def test_repeated_original_name_requires_explicit_resolution():
    _,_,first,second=nested_fixture()
    first['source_names'][0]='c'
    with pytest.raises(ValueError,match='repeated'):
        compose_face_lineage(second,{'parent':first})


def test_unknown_nested_input_rejected():
    _,_,first,second=nested_fixture()
    with pytest.raises(ValueError,match='unknown'):
        compose_face_lineage(second,{'other':first})


def test_two_independent_parent_unions_and_new_bridge_preserve_sources():
    originals={}
    for index,name in enumerate(('a','b','bridge','c','d')):
        mesh=trimesh.creation.box(extents=[2,2,2])
        mesh.apply_translation([index,0,0])
        originals[name]=mesh
    left,left_report=build_solid_union({name:originals[name] for name in ('a','b')})
    right,right_report=build_solid_union({name:originals[name] for name in ('c','d')})
    combined,report=build_solid_union({'left':left,'right':right,'bridge':originals['bridge']})
    flat=compose_face_lineage(report['face_lineage'],{
        'left':left_report['face_lineage'],'right':right_report['face_lineage']})
    assert set(flat['source_names'])==set(originals)
    assert verify_face_lineage(combined,originals,flat)['status']=='PASS'
