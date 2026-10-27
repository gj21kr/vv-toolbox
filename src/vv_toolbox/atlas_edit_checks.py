"""Basic edit invariants; these checks do not certify anatomical geometry."""
import numpy as np


class AtlasEditCheckFailure(ValueError):
    """A computed edit failed a required geometry check before publication."""


def require_section_target_match(edited, original_profiles, requested_profiles,
                                 centerline_mm, *, absolute_scale_tolerance,
                                 tangent_half_window_mm):
    """Measure the candidate itself before allowing a target-scale check to pass.

    Call on a staged candidate, before replacing the active surface. The caller
    must also perform collision and junction checks; this is not full approval.
    """
    import trimesh
    from .source_sections import extract_source_sections
    from .section_target_check import check_section_targets
    try:
        mesh = trimesh.Trimesh(edited['vertices'], edited['faces'], process=False)
        measured = extract_source_sections(
            mesh, centerline_mm, tangent_half_window_mm=tangent_half_window_mm)
        result = check_section_targets(
            original_profiles, requested_profiles, measured['profiles'],
            absolute_scale_tolerance=absolute_scale_tolerance)
    except (KeyError, TypeError, ValueError) as error:
        result = dict(status='UNKNOWN', complete=False, reason=str(error))
    edited.setdefault('edit_checks', {})['section_targets'] = result
    if result['status'] != 'PASS':
        raise AtlasEditCheckFailure(f"Atlas section target check {result['status']}")
    return result


def require_self_contact_clearance(edited):
    """Screen an edited surface; reject both detected contacts and incomplete checks.

    This is not surrounding-vessel clearance or anatomical acceptance.
    """
    from .mesh_self_contact import inspect_self_contact
    result = inspect_self_contact(edited['vertices'], edited['faces'])
    status = {'NO_CONTACT_DETECTED': 'PASS', 'CONTACT_DETECTED': 'FAIL'}.get(result['status'], 'UNKNOWN')
    edited.setdefault('edit_checks', {})['self_intersection'] = status
    edited['edit_checks']['self_contact_screen'] = result
    if status != 'PASS':
        raise AtlasEditCheckFailure(
            f"Atlas self-contact check {status}: {len(result['contact_pairs'])} contact pairs; {result['coverage']}")
    return result


def inspect_edit(original, edited, source_edges, edited_edges):
    vertices=np.asarray(original['vertices'],dtype=float)
    moved=np.asarray(edited['vertices'],dtype=float)
    faces=np.asarray(original['faces'])
    changed_faces=np.asarray(edited['faces'])
    if (vertices.shape!=moved.shape or vertices.ndim!=2 or vertices.shape[1]!=3 or
            not np.isfinite(vertices).all() or not np.isfinite(moved).all() or
            faces.ndim!=2 or faces.shape[1]!=3 or not len(faces) or
            not np.issubdtype(faces.dtype,np.integer) or faces.min()<0 or faces.max()>=len(vertices)):
        raise ValueError('Invalid edit inspection geometry')
    topology=np.array_equal(faces,changed_faces)
    if not topology:
        raise ValueError('Edit inspection requires unchanged triangle connectivity')
    def areas(points):
        triangle=points[faces]
        return np.linalg.norm(np.cross(triangle[:,1]-triangle[:,0],
                                       triangle[:,2]-triangle[:,0]),axis=1)/2
    before,after=areas(vertices),areas(moved)
    tolerance=1e-12
    prior_degenerate=before<=tolerance
    collapsed=after<=tolerance
    new_collapsed=np.flatnonzero(collapsed & ~prior_degenerate)
    by_id={edge['id']:edge for edge in edited_edges}
    if len(by_id)!=len(edited_edges) or set(by_id)!={edge['id'] for edge in source_edges}:
        raise ValueError('Edit inspection edge identities differ')
    anchors=True
    positive=True
    for edge in source_edges:
        changed=by_id[edge['id']]
        points=np.asarray(changed['points'],dtype=float)
        radii=np.asarray(changed['radii'],dtype=float)
        if (points.shape!=np.asarray(edge['points']).shape or radii.shape!=(len(points),) or
                not np.isfinite(points).all() or not np.isfinite(radii).all()):
            raise ValueError('Invalid edited centerline')
        positive=positive and bool(np.all(radii>0))
        anchors=anchors and all(changed[k]==edge[k] for k in ('start','end'))
        anchors=anchors and np.array_equal(points[[0,-1]],np.asarray(edge['points'])[[0,-1]])
        anchors=anchors and np.array_equal(radii[[0,-1]],np.asarray(edge['radii'])[[0,-1]])
    checks=dict(connectivity='PASS',endpoint_positions_and_radii='PASS' if anchors else 'FAIL',
                positive_radii='PASS' if positive else 'FAIL',
                no_new_degenerate_triangles='PASS' if not len(new_collapsed) else 'FAIL')
    return dict(schema='vv-toolbox.atlas-edit-checks/1',
                basic_invariants='PASS' if all(v=='PASS' for v in checks.values()) else 'FAIL',
                checks=checks,area_tolerance_mm2=tolerance,
                source_degenerate_triangles=int(prior_degenerate.sum()),
                edited_degenerate_triangles=int(collapsed.sum()),
                newly_degenerate_face_ids=new_collapsed.tolist(),
                maximum_vertex_displacement_mm=float(np.linalg.norm(moved-vertices,axis=1).max()),
                self_intersection='NOT RUN',surrounding_collision='NOT RUN',
                junction_smoothness='NOT RUN',anatomical_validity='UNKNOWN',
                scope='Same-connectivity mesh and centerline endpoint invariants only; inherited defects are counted separately.')
