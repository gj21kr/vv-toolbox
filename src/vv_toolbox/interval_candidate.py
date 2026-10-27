"""Build a separate, checked noncircular interval candidate without publishing it."""
from copy import deepcopy

import numpy as np
import trimesh

from .atlas_edit_checks import AtlasEditCheckFailure, require_section_target_match
from .mesh_self_contact import inspect_self_contact
from .profile_loft import loft_source_profiles
from .profile_scale import scale_profile_interval
from .protected_surface_fit import fit_protected_surface
from .source_sections import extract_source_sections
from .surface_indexing import exact_vertex_index_copy


def build_interval_candidate(part, centerline_mm, *, start_mm, end_mm, factor,
                             protected_vertex_ids, max_displacement_mm,
                             absolute_scale_tolerance, tangent_half_window_mm=2.,
                             transition_rings=3, neighbors=None, expected_neighbor_ids=None):
    """Return only after topology, self-contact and measured target checks pass.

    Distances begin at the first extracted interior section. Caller supplies
    contact/junction protection. Surrounding-vessel checks remain required
    before any application to an active scene.
    """
    source = trimesh.Trimesh(part['vertices'], part['faces'], process=False)
    _, source_topology = exact_vertex_index_copy(source)
    if not source_topology['usable_for_sampled_containment']:
        raise AtlasEditCheckFailure('Closed consistent source surface required')
    sections = extract_source_sections(
        source, centerline_mm, tangent_half_window_mm=tangent_half_window_mm)
    profiles = sections['profiles']
    edited = scale_profile_interval(profiles, start_mm=start_mm, end_mm=end_mm,
                                    factor=factor,
                                    protected_indices=[profiles[0]['index'], profiles[-1]['index']])
    target, _ = loft_source_profiles(edited['profiles'], samples=64)
    points = np.asarray([p['origin_mm'] for p in profiles])
    delta = np.diff(points, axis=0)
    length = np.linalg.norm(delta, axis=1)
    arc = np.r_[0., np.cumsum(length)]
    # Bound memory while fixing all vertices outside the requested interval.
    fixed = set(protected_vertex_ids)
    for offset in range(0, len(source.vertices), 512):
        relative = source.vertices[offset:offset + 512, None] - points[:-1]
        fraction = np.clip(np.einsum('vsi,si->vs', relative, delta) / length**2, 0, 1)
        residual = relative - fraction[:, :, None] * delta
        nearest = np.argmin(np.einsum('vsi,vsi->vs', residual, residual), axis=1)
        location = arc[nearest] + fraction[np.arange(len(nearest)), nearest] * length[nearest]
        fixed.update((offset + np.flatnonzero((location <= start_mm) | (location >= end_mm))).tolist())
    try:
        mesh, fit = fit_protected_surface(
            source, target, sorted(fixed), max_displacement_mm=max_displacement_mm,
            transition_rings=transition_rings)
    except ValueError as error:
        raise AtlasEditCheckFailure(str(error)) from error
    normalized, topology = exact_vertex_index_copy(mesh)
    if not topology['usable_for_sampled_containment']:
        raise AtlasEditCheckFailure('Candidate lost closed consistent topology')
    contact = inspect_self_contact(normalized.vertices, normalized.faces)
    if contact['status'] != 'NO_CONTACT_DETECTED':
        raise AtlasEditCheckFailure('Candidate self-contact check did not pass')
    candidate = deepcopy(part)
    candidate.update(vertices=np.asarray(mesh.vertices).copy(), faces=np.asarray(mesh.faces).copy(),
                     edit_checks=dict(topology=topology, self_contact_screen=contact,
                                      surrounding_collision='NOT RUN',
                                      anatomical_validity='UNKNOWN'))
    require_section_target_match(
        candidate, profiles, edited['profiles'], centerline_mm,
        absolute_scale_tolerance=absolute_scale_tolerance,
        tangent_half_window_mm=tangent_half_window_mm)
    if neighbors is not None or expected_neighbor_ids is not None:
        from .neighbor_contacts import inspect_neighbor_contacts
        surrounding = inspect_neighbor_contacts(
            part, candidate, neighbors, expected_ids=expected_neighbor_ids)
        candidate['edit_checks']['neighbor_surface_contacts'] = surrounding
        if surrounding['status'] != 'PASS':
            raise AtlasEditCheckFailure('Neighbor surface contact preservation did not pass')
    candidate['interval_edit'] = dict(
        start_mm=start_mm, end_mm=end_mm, factor=factor,
        arclength_origin=edited['arclength_origin'], fit=fit,
        absolute_scale_tolerance=absolute_scale_tolerance,
        protected_vertex_ids=sorted(fixed), status='CANDIDATE')
    return candidate
