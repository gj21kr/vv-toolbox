"""Compare surface contact face pairs across an explicit whole neighbor set."""
import numpy as np
import trimesh

from .mesh_pair_contact import inspect_pair_contact
from .disjoint_containment import inspect_disjoint_containment, _SurfaceValidationCache


def inspect_neighbor_contacts(original, candidate, neighbors, *, expected_ids,
                              max_pairs=2_000_000):
    """Fail closed on missing neighbors; PASS is not a volume-overlap result."""
    if (not isinstance(neighbors, list) or not isinstance(expected_ids, list)
            or any(not isinstance(i, str) or not i for i in expected_ids)
            or len(expected_ids) != len(set(expected_ids))):
        raise ValueError('Explicit unique neighbor IDs required')
    ids = [p.get('id') for p in neighbors]
    report = dict(status='UNKNOWN', complete=False, rows=[],
                  expected_ids=sorted(expected_ids), containment='NOT RUN',
                  scope='Unchanged surface-contact face pairs for all supplied neighbors')
    if (len(ids) != len(set(ids)) or set(ids) != set(expected_ids)
            or original.get('id') in ids):
        return dict(report, reason='Missing, duplicate or self neighbor')
    def triangles(part):
        vertices = np.asarray(part['vertices'], dtype=float)
        faces = np.asarray(part['faces'])
        if (vertices.ndim != 2 or vertices.shape[1] != 3 or not np.isfinite(vertices).all()
                or faces.ndim != 2 or faces.shape[1] != 3 or not len(faces)
                or not np.issubdtype(faces.dtype, np.integer)
                or faces.min() < 0 or faces.max() >= len(vertices)):
            raise ValueError('Finite mesh with valid face indices required')
        return vertices[faces]
    if original.get('id') != candidate.get('id') or not np.array_equal(original['faces'], candidate['faces']):
        return dict(report, reason='Part identity or face correspondence changed')
    before, after = triangles(original), triangles(candidate)
    validation_cache = _SurfaceValidationCache()
    for neighbor in neighbors:
        other = triangles(neighbor)
        def separated(triangles):
            return bool(np.any(triangles.max(axis=(0, 1)) < other.min(axis=(0, 1)) - 1e-6)
                        or np.any(other.max(axis=(0, 1)) < triangles.min(axis=(0, 1)) - 1e-6))
        if separated(before) and separated(after):
            clearance = dict(status='BOUNDS_SEPARATED', complete=True, contact_pairs=[], checked_pairs=0)
            report['rows'].append(dict(neighbor_id=neighbor['id'], status='PASS',
                                       before=clearance.copy(), after=clearance.copy(), gained=[], lost=[],
                                       disjoint_containment=dict(status='PASS', reason='Before and after bounds separated')))
            continue
        old = inspect_pair_contact(before, other, max_pairs=max_pairs)
        new = inspect_pair_contact(after, other, max_pairs=max_pairs)
        previous, current = set(map(tuple, old['contact_pairs'])), set(map(tuple, new['contact_pairs']))
        gained, lost = sorted(current - previous), sorted(previous - current)
        complete = old['complete'] and new['complete']
        status = 'UNKNOWN' if not complete else 'FAIL' if gained or lost else 'PASS'
        containment = dict(status='NOT RUN', reason='Surface contact present or incomplete')
        if complete and not previous and not current and separated(before) and separated(after):
            containment = dict(status='PASS', reason='Both before and after bounding boxes separated')
        elif complete and not previous and not current:
            meshes = [trimesh.Trimesh(p['vertices'], p['faces'], process=False)
                      for p in (original, candidate, neighbor)]
            prior_inside = inspect_disjoint_containment(meshes[0], meshes[2], _validation_cache=validation_cache)
            next_inside = inspect_disjoint_containment(meshes[1], meshes[2], _validation_cache=validation_cache)
            def identities(check):
                return {(r['direction'], r['first_face_id']) for r in check['contained_components']}
            if not prior_inside['complete'] or not next_inside['complete']:
                inside_status = 'UNKNOWN'
            else:
                inside_status = 'PASS' if identities(prior_inside) == identities(next_inside) else 'FAIL'
            containment = dict(status=inside_status, before=prior_inside, after=next_inside)
            if inside_status != 'PASS':
                status = inside_status
        report['rows'].append(dict(neighbor_id=neighbor['id'], status=status,
                                   before=old, after=new, gained=gained, lost=lost,
                                   disjoint_containment=containment))
    states = [row['status'] for row in report['rows']]
    report['complete'] = 'UNKNOWN' not in states
    report['status'] = 'FAIL' if 'FAIL' in states else 'UNKNOWN' if 'UNKNOWN' in states else 'PASS'
    report['surface_validation_reuse'] = dict(hits=validation_cache.hits, misses=validation_cache.misses)
    return report
