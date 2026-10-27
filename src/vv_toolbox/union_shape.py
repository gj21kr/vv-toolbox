"""Explicit bend/twist candidates with fixed source interfaces; no anatomy claims."""
import numpy as np
from scipy.spatial import cKDTree
import trimesh

from .union_selection import select_union_source
from .mesh_self_contact import inspect_self_contact
from .centerline_containment import inspect_centerline_containment


class ShapeEditFailure(ValueError):
    """Rejected proposal with measurements; no candidate geometry is returned."""
    def __init__(self, message, measurements):
        super().__init__(message)
        self.measurements = measurements


def deform_selected_shape(mesh, lineage, source_name, centerline, *, bend_mm,
                          bend_direction, twist_deg, collar_mm, transition_mm,
                          max_displacement_mm, protected_points_mm=()):
    """One spatial field for selected surface vertices and its supplied path.

    Bend is a displacement, not a measured tortuosity target. Twist rotates about
    the endpoint chord with a spatial taper, not a differential torsion target.
    Other graph paths and neighboring vessels require separate validation.
    """
    parameters = [bend_mm, twist_deg, collar_mm, transition_mm, max_displacement_mm]
    if any(isinstance(v, (bool, str)) or not np.isscalar(v) for v in parameters):
        raise ValueError('Finite numeric shape parameters required')
    if (not np.isfinite(parameters).all() or collar_mm < 0 or transition_mm <= 0
            or max_displacement_mm <= 0):
        raise ValueError('Invalid shape parameters')
    points = np.asarray(centerline, float)
    protected = np.asarray(protected_points_mm, float)
    if protected.shape == (0,):
        protected = np.empty((0, 3))
    if protected.ndim != 2 or protected.shape[1] != 3 or not np.isfinite(protected).all():
        raise ValueError('Finite Nx3 protected graph points required')
    direction = np.asarray(bend_direction, float)
    if (points.ndim != 2 or points.shape[1] != 3 or len(points) < 2
            or not np.isfinite(points).all() or direction.shape != (3,)
            or not np.isfinite(direction).all()):
        raise ValueError('Explicit finite path and bend direction required')
    chord = points[-1]-points[0]
    if np.linalg.norm(chord) <= 1e-9 or np.any(np.linalg.norm(np.diff(points, axis=0), axis=1) <= 1e-9):
        raise ValueError('Distinct path stations and endpoint chord required')
    axis = chord/np.linalg.norm(chord)
    direction = direction-axis*np.dot(direction, axis)
    if np.linalg.norm(direction) <= 1e-9:
        raise ValueError('Bend direction must have a component perpendicular to chord')
    direction /= np.linalg.norm(direction)
    vertices = np.asarray(mesh.vertices)
    selection = select_union_source(vertices, mesh.faces, lineage, source_name)
    active = np.asarray(selection['exclusive_vertex_ids'], int)
    shared = np.asarray(selection['shared_interface_vertex_ids'], int)
    if not len(active) or not len(shared) or not mesh.is_volume:
        raise ValueError('Closed positive union with interior and shared interface required')
    fixed = np.setdiff1d(np.arange(len(vertices)), active)
    # The same physical collars affect the surface and path; no vertex-only taper.
    anchors = cKDTree(np.vstack((vertices[fixed], points[[0, -1]], protected)))

    def transform(query):
        t = np.clip((anchors.query(query)[0]-collar_mm)/transition_mm, 0, 1)
        weight = t**3*(10-15*t+6*t*t)
        relative = query-points[0]
        parallel = np.outer(relative@axis, axis)
        radial = relative-parallel
        angle = np.deg2rad(twist_deg)*weight
        rotated = radial*np.cos(angle)[:, None]+np.cross(axis, radial)*np.sin(angle)[:, None]
        return query+(rotated-radial)+bend_mm*weight[:, None]*direction

    output = vertices.copy()
    output[active] = transform(vertices[active])
    path = transform(points)
    path[[0, -1]] = points[[0, -1]]
    surface_move = np.linalg.norm(output-vertices, axis=1)
    path_move = np.linalg.norm(path-points, axis=1)
    surface_peak, path_peak = int(np.argmax(surface_move)), int(np.argmax(path_move))
    displacement = max(float(surface_move[surface_peak]), float(path_move[path_peak]))
    relative = vertices[surface_peak]-points[0]
    measurements = dict(maximum_displacement_mm=displacement,
        displacement_bound_mm=float(max_displacement_mm),
        surface_maximum_mm=float(surface_move[surface_peak]),
        surface_peak_vertex=surface_peak, surface_peak_position_mm=vertices[surface_peak].tolist(),
        surface_peak_chord_distance_mm=float(np.linalg.norm(relative-axis*np.dot(relative, axis))),
        path_maximum_mm=float(path_move[path_peak]), path_peak_station=path_peak,
        path_peak_position_mm=points[path_peak].tolist(),
        chord_length_mm=float(np.linalg.norm(chord)),
        surface_displacement_percentiles_mm=np.percentile(surface_move[active], [0, 50, 95, 100]).tolist())
    if displacement > max_displacement_mm:
        raise ShapeEditFailure('Shape change exceeds displacement bound', measurements)
    old, new = vertices[mesh.faces], output[mesh.faces]
    old_normal = np.cross(old[:, 1]-old[:, 0], old[:, 2]-old[:, 0])
    new_normal = np.cross(new[:, 1]-new[:, 0], new[:, 2]-new[:, 0])
    if np.any(np.linalg.norm(new_normal, axis=1) <= 1e-12) or np.any(np.sum(old_normal*new_normal, axis=1) <= 0):
        raise ValueError('Shape change degenerates or reverses triangles')
    result = trimesh.Trimesh(output, mesh.faces.copy(), process=False)
    if not result.is_volume:
        raise ValueError('Shape change loses closed positive volume')
    contact = inspect_self_contact(result.vertices, result.faces)
    if contact['status'] != 'NO_CONTACT_DETECTED':
        raise ValueError('Shape self-contact not cleared')
    containment = inspect_centerline_containment(result, path)
    if containment['status'] != 'PASS':
        raise ValueError('Deformed centerline containment not cleared')
    return result, path, dict(status='CANDIDATE', source_name=source_name,
        bend_mm=float(bend_mm), twist_deg=float(twist_deg), collar_mm=float(collar_mm),
        transition_mm=float(transition_mm), maximum_displacement_mm=displacement,
        displacement_measurements=measurements,
        fixed_vertices_unchanged=bool(np.array_equal(output[fixed], vertices[fixed])),
        protected_graph_points=len(protected),
        protected_graph_points_fixed=bool(np.array_equal(transform(protected), protected)) if len(protected) else True,
        path_endpoints_fixed=bool(np.array_equal(path[[0, -1]], points[[0, -1]])),
        self_contact=contact, centerline_containment=containment, neighboring_vessels='NOT RUN',
        radius_surface_consistency='NOT RUN', anatomical_validation='NOT RUN')
