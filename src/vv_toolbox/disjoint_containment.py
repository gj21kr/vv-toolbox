"""Component-wise containment screening after complete surface separation."""
import hashlib
from copy import deepcopy

import numpy as np
import trimesh

from .mesh_pair_contact import inspect_pair_contact
from .mesh_self_contact import inspect_self_contact
from .surface_indexing import exact_vertex_index_copy


class _SurfaceValidationCache:
    """Request-local reuse; content-addressed, bounded and never persisted."""

    def __init__(self):
        self.entries = {}
        self._checks = {}
        self.hits = 0
        self.misses = 0

    def validate(self, mesh):
        vertices = np.asarray(mesh.vertices, dtype='<f8')
        faces = np.asarray(mesh.faces, dtype='<i8')
        digest = hashlib.sha256()
        for array in (vertices, faces):
            digest.update(str(array.shape).encode('ascii'))
            digest.update(array.tobytes())
        key = digest.digest()
        if key in self.entries:
            self.hits += 1
            # Keep the repeatedly used union hot while rotating small neighbors.
            entry = self.entries.pop(key)
            self.entries[key] = entry
            return entry
        self.misses += 1
        normalized, topology = exact_vertex_index_copy(mesh)
        reason = None
        check = None
        diagnostic = dict(geometry_sha256=digest.hexdigest(), topology=topology,
                          self_contact='NOT RUN')
        if not topology['usable_for_sampled_containment']:
            reason = 'Closed consistent nondegenerate surface required'
        else:
            check = inspect_self_contact(normalized.vertices, normalized.faces)
            diagnostic['self_contact'] = {k: check[k] for k in
                ('status', 'coverage', 'checked_pairs') if k in check}
            diagnostic['self_contact']['contact_pair_count'] = len(check.get('contact_pairs', []))
            diagnostic['self_contact']['example_contact_pairs'] = check.get('contact_pairs', [])[:16]
            if check['status'] != 'NO_CONTACT_DETECTED':
                reason = 'Self-contact clearance incomplete or failed'
        if len(self.entries) >= 32:
            oldest = next(iter(self.entries))
            self.entries.pop(oldest)
            self._checks.pop(oldest, None)
        self.entries[key] = (normalized, reason, diagnostic)
        # Failed inspections can carry millions of pairs; diagnostics above
        # retain only examples. Successful checks have no contact-pair payload.
        self._checks[key] = check if check and check['status']=='NO_CONTACT_DETECTED' else None
        return normalized, reason, diagnostic

    def self_contact_check(self, mesh):
        """Return the computed check, never accept caller-provided clearance."""
        _, reason, diagnostic = self.validate(mesh)
        key = bytes.fromhex(diagnostic['geometry_sha256'])
        check = self._checks.get(key)
        if check is None:
            raise ValueError(reason or 'Self-contact inspection unavailable')
        return deepcopy(check)


def inspect_disjoint_containment(first, second, *, tolerance_mm=1e-6, _validation_cache=None):
    """For closed nonintersecting surfaces, classify one vertex per component.

    Floating-point ray tests assume valid solid surfaces. Face component IDs are
    their minimum original face index; exact-coordinate normalization preserves
    face order. Intersecting surfaces require a different volume-overlap test.
    """
    if not np.isfinite(tolerance_mm) or tolerance_mm <= 0:
        raise ValueError('Positive finite tolerance required')
    result = dict(status='UNKNOWN', complete=False, contained_components=[],
                  tolerance_mm=tolerance_mm,
                  scope='Whole connected boundary components of closed disjoint surfaces')
    surfaces = []
    cache = _validation_cache if _validation_cache is not None else _SurfaceValidationCache()
    for index, mesh in enumerate((first, second)):
        normalized, reason, diagnostic = cache.validate(mesh)
        if reason:
            return dict(result, reason=reason, invalid_surface_index=index,
                        invalid_surface_validation=diagnostic)
        surfaces.append(normalized)
    pair = inspect_pair_contact(surfaces[0].triangles, surfaces[1].triangles,
                                tolerance_mm=tolerance_mm)
    if not pair['complete'] or pair['contact_pairs']:
        return dict(result, reason='Complete disjoint-surface prerequisite not satisfied')
    for direction, (source, target) in enumerate((surfaces, surfaces[::-1])):
        components = trimesh.graph.connected_components(
            source.face_adjacency, nodes=np.arange(len(source.faces)), min_len=1)
        ids = sorted(int(np.min(component)) for component in components)
        points = source.triangles[ids, 0]
        _, distances, _ = trimesh.proximity.closest_point(target, points)
        if not np.isfinite(distances).all() or np.any(distances <= tolerance_mm):
            return dict(result, reason='Component witness too close to boundary')
        inside = target.contains(points)
        for face_id, point, enclosed in zip(ids, points, inside):
            if enclosed:
                result['contained_components'].append(dict(
                    direction=direction, first_face_id=face_id, witness_mm=point.tolist()))
    result.update(status='CONTAINMENT_DETECTED' if result['contained_components']
                  else 'NO_CONTAINMENT_DETECTED', complete=True)
    return result
