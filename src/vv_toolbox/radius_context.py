"""Compare a fixed-topology edit against every supplied context surface."""
import hashlib
import copy
import numpy as np

from .mesh_pair_contact import inspect_pair_contact
from .disjoint_containment import inspect_disjoint_containment, _SurfaceValidationCache


def inspect_radius_context(before, after, neighbors, *, tolerance_mm=1e-6, progress=None, _validation_cache=None):
    if not np.array_equal(before.faces, after.faces) or before.vertices.shape != after.vertices.shape:
        raise ValueError('Matching edit topology required for contact-pair comparison')
    if not neighbors:
        raise ValueError('Explicit nonempty neighbor context required')
    if not np.isfinite(tolerance_mm) or tolerance_mm <= 0:
        raise ValueError('Positive finite tolerance required')
    if progress is not None and not callable(progress):
        raise ValueError('Progress callback must be callable')
    cache = _validation_cache if _validation_cache is not None else _SurfaceValidationCache()

    def inspect(mesh, other):
        if (np.any(mesh.bounds[0] > other.bounds[1]+tolerance_mm)
                or np.any(other.bounds[0] > mesh.bounds[1]+tolerance_mm)):
            return dict(status='SEPARATED', complete=True, contact_pairs=[])
        pair = inspect_pair_contact(mesh.triangles, other.triangles, tolerance_mm=tolerance_mm)
        if not pair['complete']:
            return dict(status='UNKNOWN', complete=False, contact_pairs=pair['contact_pairs'])
        if pair['contact_pairs']:
            return dict(status='SURFACE_CONTACT', complete=True, contact_pairs=pair['contact_pairs'])
        containment = inspect_disjoint_containment(
            mesh, other, tolerance_mm=tolerance_mm, _validation_cache=cache)
        return dict(status=('CONTAINMENT' if containment['status']=='CONTAINMENT_DETECTED'
                            else 'SEPARATED' if containment['status']=='NO_CONTAINMENT_DETECTED'
                            else 'UNKNOWN'), complete=containment['complete'],
                    contact_pairs=[], containment=containment)

    rows = []
    context_hash = hashlib.sha256()
    for name, neighbor in sorted(neighbors.items()):
        encoded = name.encode('utf-8')
        context_hash.update(len(encoded).to_bytes(8, 'little'))
        context_hash.update(encoded)
        for array in (np.asarray(neighbor.vertices,dtype='<f8'), np.asarray(neighbor.faces,dtype='<i8')):
            context_hash.update(str(array.shape).encode('ascii'))
            context_hash.update(array.tobytes())
        old = inspect(before, neighbor)
        new = copy.deepcopy(old) if before is after else inspect(after, neighbor)
        old_pairs = {tuple(pair) for pair in old['contact_pairs']}
        new_pairs = {tuple(pair) for pair in new['contact_pairs']}
        rows.append(dict(neighbor_id=name, before=old, after=new,
                         added_contact_pairs=sorted(new_pairs-old_pairs),
                         removed_contact_pairs=sorted(old_pairs-new_pairs)))
        if progress is not None:
            progress(dict(completed=len(rows),total=len(neighbors),row=copy.deepcopy(rows[-1])))
    changed = [r['neighbor_id'] for r in rows if r['added_contact_pairs']
               or (r['after']['status'] in ('SURFACE_CONTACT','CONTAINMENT')
                   and r['before']['status']=='SEPARATED')]
    unknown = [r['neighbor_id'] for r in rows if not r['before']['complete'] or not r['after']['complete']]
    existing = [r['neighbor_id'] for r in rows if r['after']['status'] in ('SURFACE_CONTACT','CONTAINMENT')]
    return dict(status='FAIL' if changed else 'UNKNOWN' if unknown or existing else 'PASS',
                decision_reason=('NEW_OR_EXTENDED_CONTACT' if changed else 'INCOMPLETE_INSPECTION'
                                 if unknown else 'EXISTING_CONTACT_REQUIRES_JUNCTION_REVIEW' if existing else 'CLEAR'),
                context_sha256=context_hash.hexdigest(),
                rows=rows, new_or_extended_contacts=changed, unknown=unknown,
                remaining_contacts=existing, tolerance_mm=tolerance_mm,
                scope='Fixed-topology edit versus all supplied static neighbors, including disjoint containment',
                same_triangle_contact_location_equivalence='NOT RUN',
                anatomical_validation='NOT RUN')


def inspect_static_context(mesh, neighbors, *, tolerance_mm=1e-6, progress=None):
    """Absolute context inspection for a new union, without topology comparison."""
    result=inspect_radius_context(mesh,mesh,neighbors,tolerance_mm=tolerance_mm,progress=progress)
    return dict(status=result['status'],decision_reason=result['decision_reason'],
                context_sha256=result['context_sha256'],tolerance_mm=tolerance_mm,
                rows=[dict(neighbor_id=row['neighbor_id'],**row['after']) for row in result['rows']],
                remaining_contacts=result['remaining_contacts'],unknown=result['unknown'],
                scope='Single candidate against every supplied context surface, including disjoint containment',
                anatomical_validation='NOT RUN')
