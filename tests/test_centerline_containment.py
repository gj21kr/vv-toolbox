import numpy as np
import pytest
import trimesh

from vv_toolbox.centerline_containment import inspect_centerline_containment


def test_inside_intervals_are_covered_without_mutating_source():
    mesh=trimesh.creation.box()
    before=mesh.vertices.copy()
    result=inspect_centerline_containment(mesh,[[-.4,-.4,0],[.4,.4,0]])
    assert result['status']=='PASS'
    assert result['maximum_depth_used']>0
    assert result['covered_cells']>1
    assert np.array_equal(mesh.vertices,before)


def test_interior_stations_and_midpoint_do_not_hide_exit_between_them():
    boxes=[]
    for x in (-1,0,1):
        box=trimesh.creation.box(extents=[.4,.4,.4])
        box.apply_translation([x,0,0]);boxes.append(box)
    mesh=trimesh.util.concatenate(boxes)
    assert mesh.contains([[-1,0,0],[0,0,0],[1,0,0]]).all()
    result=inspect_centerline_containment(mesh,[[-1,0,0],[1,0,0]])
    assert result['status']=='FAIL'
    assert result['outside_witnesses']
    assert result['maximum_depth_used']>=1


def test_boundary_contact_and_exhausted_budget_remain_unknown():
    mesh=trimesh.creation.box()
    contact=inspect_centerline_containment(mesh,[[0,0,0],[.5,0,0]],max_depth=8)
    assert contact['status']=='UNKNOWN'
    exhausted=inspect_centerline_containment(mesh,[[-.4,-.4,0],[.4,.4,0]],max_cells=1)
    assert exhausted['status']=='UNKNOWN' and exhausted['processed_cells']==1


def test_open_surface_not_accepted():
    mesh=trimesh.creation.box();mesh.update_faces(np.arange(len(mesh.faces)-1))
    assert inspect_centerline_containment(mesh,[[0,0,0],[.1,0,0]])['status']=='UNKNOWN'


@pytest.mark.parametrize('settings',[dict(tolerance_mm=0),dict(max_depth=True),dict(max_cells=0)])
def test_invalid_limits_rejected(settings):
    with pytest.raises(ValueError):
        inspect_centerline_containment(trimesh.creation.box(),[[0,0,0],[.1,0,0]],**settings)


@pytest.mark.parametrize("leaves_volume", [False, True])
def test_smaller_query_batches_keep_all_interval_results(monkeypatch, leaves_volume):
    import vv_toolbox.centerline_containment as module
    mesh = trimesh.creation.box()
    points = np.column_stack((np.linspace(-.4, .4, 601), np.zeros((601, 2))))
    if leaves_volume:
        points[300, 1] = .8
    monkeypatch.setattr(module, "_QUERY_BATCH_SIZE", 2048)
    previous = inspect_centerline_containment(mesh, points)
    monkeypatch.setattr(module, "_QUERY_BATCH_SIZE", 128)
    bounded = inspect_centerline_containment(mesh, points)
    assert bounded["segment_count"] == previous["segment_count"] == 600
    assert bounded["status"] == previous["status"] == ("FAIL" if leaves_volume else "PASS")
    for key in ("processed_cells", "covered_cells", "unresolved_segments",
                "outside_witnesses", "maximum_depth_used"):
        assert bounded[key] == previous[key]
