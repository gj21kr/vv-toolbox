"""Exact registered case surfaces; no implicit circular reconstruction."""
from copy import deepcopy
import hashlib

import numpy as np

from .case_io import _encode


def _hash(value):
    return hashlib.sha256(_encode(value)).hexdigest()


def _paths(case, ids):
    by_id = {e['id']: e for e in case['edges']}
    return [dict(id=i, centerline_mm=by_id[i]['centerline_mm'], radii_mm=by_id[i]['radii_mm'])
            for i in sorted(ids)]


def attach_surfaces(case, parts):
    """Register explicitly bound source/derived surfaces on an independent case."""
    from .case_contract import validate_case
    validate_case(case)
    result = deepcopy(case)
    result['surface_parts'] = []
    for part in parts:
        item = deepcopy(part)
        item['geometry_sha256'] = _hash(dict(vertices_mm=item['vertices_mm'], faces=item['faces']))
        item['paths_sha256'] = _hash(_paths(case, item['edge_ids']))
        result['surface_parts'].append(item)
    validate_case(result)
    return result


def validate_surface_parts(case):
    parts = case.get('surface_parts')
    if parts is None:
        return
    if not isinstance(parts, list) or not parts:
        raise ValueError('Nonempty surface registry required')
    edge_ids = {e['id'] for e in case['edges']}
    sources = {s['id'] for s in case['sources']}
    seen_parts, seen_edges = set(), set()
    for p in parts:
        if (not isinstance(p, dict) or not isinstance(p.get('part_id'), str)
                or not p['part_id'] or p['part_id'] in seen_parts):
            raise ValueError('Unique surface part identity required')
        ids = p.get('edge_ids')
        if (not isinstance(ids, list) or not ids or any(not isinstance(i, str) for i in ids)
                or len(set(ids)) != len(ids) or not set(ids) <= edge_ids or set(ids) & seen_edges):
            raise ValueError('Unique explicit surface edge bindings required')
        if (p.get('frame_id') != case['frame']['id'] or p.get('provenance') not in ('source', 'estimated')
                or not p.get('source_ids') or not set(p['source_ids']) <= sources):
            raise ValueError('Surface frame and source provenance required')
        if case['model_kind'] == 'source' and p['provenance'] != 'source':
            raise ValueError('Derived surface requires synthetic case provenance')
        v, f = np.asarray(p.get('vertices_mm'), dtype=float), np.asarray(p.get('faces'))
        if (v.ndim != 2 or v.shape[1] != 3 or len(v) < 3 or not np.isfinite(v).all()
                or f.ndim != 2 or f.shape[1] != 3 or not len(f)
                or not np.issubdtype(f.dtype, np.integer) or f.min() < 0 or f.max() >= len(v)):
            raise ValueError('Invalid registered surface geometry')
        if p.get('geometry_sha256') != _hash(dict(vertices_mm=p['vertices_mm'], faces=p['faces'])):
            raise ValueError('Registered surface geometry hash mismatch')
        if p.get('paths_sha256') != _hash(_paths(case, ids)):
            raise ValueError('Registered surface paths changed; regenerate surface explicitly')
        seen_parts.add(p['part_id']); seen_edges.update(ids)


def selected_surface(case, edge_ids):
    """Return unchanged triangles; a multi-edge part cannot be implicitly cut."""
    validate_surface_parts(case)
    if not isinstance(edge_ids, list) or not edge_ids or len(set(edge_ids)) != len(edge_ids):
        raise ValueError('Explicit unique surface edges required')
    selected, covered = [], set()
    for part in case['surface_parts']:
        ids = set(part['edge_ids'])
        if ids & set(edge_ids):
            if not ids <= set(edge_ids):
                raise ValueError('Partial source part requires explicit segment surface boundaries')
            selected.append(part); covered.update(ids)
    if covered != set(edge_ids):
        raise ValueError('Selected edges lack registered surfaces')
    vertices, faces, spans, offset, face_offset = [], [], [], 0, 0
    for p in selected:
        v, f = np.asarray(p['vertices_mm'], float), np.asarray(p['faces'], np.int64)
        vertices.append(v); faces.append(f + offset)
        spans.append(dict(part_id=p['part_id'], edge_ids=p['edge_ids'],
                          vertex_start=offset, vertex_count=len(v),
                          face_start=face_offset, face_count=len(f),
                          geometry_sha256=p['geometry_sha256'], provenance=p['provenance']))
        offset += len(v); face_offset += len(f)
    from .case_io import case_digest
    metadata = dict(schema='vv-toolbox.case-surface/1', case_id=case['case_id'],
                    case_revision=case_digest(case), frame=deepcopy(case['frame']),
                    edge_ids=edge_ids, method='registered-exact-surfaces',
                    provenance='source' if all(p['provenance']=='source' for p in selected) else 'estimated',
                    parts=spans, union_performed=False,
                    anatomical_validation='NOT RUN', surface_collision_validation='NOT RUN')
    return np.concatenate(vertices), np.concatenate(faces), metadata
