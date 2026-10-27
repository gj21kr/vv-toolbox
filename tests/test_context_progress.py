import trimesh

from vv_toolbox.radius_context import inspect_static_context


def test_progress_reports_all_neighbors_without_changing_results():
    mesh=trimesh.creation.box();a=mesh.copy();a.apply_translation([5,0,0])
    b=mesh.copy();b.apply_translation([10,0,0]);neighbors={'b':b,'a':a}
    expected=inspect_static_context(mesh,neighbors);events=[]
    def progress(event):
        events.append((event['completed'],event['total'],event['row']['neighbor_id']))
        event['row']['after']['status']='corrupted callback copy'
    actual=inspect_static_context(mesh,neighbors,progress=progress)
    assert actual==expected
    assert events==[(1,2,'a'),(2,2,'b')]
