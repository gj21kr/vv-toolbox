import numpy as np
import pytest
import trimesh

from vv_toolbox.solid_union import build_solid_union


def test_union_connects_overlapping_solids_preserving_sources():
    a=trimesh.creation.box(extents=[2,2,2])
    b=a.copy();b.apply_translation([1,0,0])
    original=[(m.vertices.copy(),m.faces.copy()) for m in (a,b)]
    mesh,report=build_solid_union({'a':a,'b':b})
    assert mesh.volume==pytest.approx(12.)
    assert mesh.is_volume and report['boundary_components']==1
    lineage=report['face_lineage']
    assert lineage['source_names']==['a','b']
    source=[a,b]
    for triangle,owner,face in zip(mesh.triangles,lineage['face_source_indices'],lineage['source_face_indices']):
        source_triangle=source[owner].triangles[face]
        distances=trimesh.triangles.closest_point(
            np.repeat(source_triangle[None],3,axis=0),triangle)
        assert np.max(np.linalg.norm(distances-triangle,axis=1))<1e-6
    for m,(v,f) in zip((a,b),original):
        assert np.array_equal(m.vertices,v) and np.array_equal(m.faces,f)


def test_disconnected_union_is_rejected():
    a=trimesh.creation.box();b=a.copy();b.apply_translation([5,0,0])
    with pytest.raises(ValueError,match='disconnected'):
        build_solid_union({'a':a,'b':b})


def test_diagnostic_callback_receives_independent_geometry():
    a=trimesh.creation.box(extents=[2,2,2])
    b=a.copy();b.apply_translation([1,0,0])
    captured=[]
    def inspect(mesh,report):
        captured.append(report)
        mesh.vertices[:]=0
    merged,_=build_solid_union({'a':a,'b':b},diagnostic_callback=inspect)
    assert merged.volume==pytest.approx(12.)
    assert captured[0]['is_volume'] and captured[0]['zero_area_faces']==0
