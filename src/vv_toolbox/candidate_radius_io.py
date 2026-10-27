"""Hash-bound radius recipes replayed on an independently loaded base candidate."""
import hashlib
import json

import numpy as np

from .case_io import _unique_object


SCHEMA = 'vv-toolbox.candidate-radius-session/1'
ALGORITHM = 'fixed-interface-polyline-radius/1'


def _encode(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def base_identity(candidate):
    digest = hashlib.sha256()
    for name, dtype in [('vertices_mm', '<f8'), ('faces', '<i8')]:
        array = np.asarray(candidate[name], dtype=dtype)
        digest.update(_encode([name, list(array.shape)]))
        digest.update(array.tobytes())
    paths = {name:dict(points_mm=np.asarray(path['points_mm']).tolist(),
                      case_revision=path['case_revision'], edge_id=path.get('edge_id'),
                      provenance=path.get('provenance'))
             for name, path in candidate['source_centerlines'].items()}
    digest.update(_encode(dict(paths=paths, lineage=candidate['face_lineage'])))
    if 'access_union' in candidate['summary']:
        digest.update(_encode(dict(access_edges=candidate.get('edges', []),
                                   access_graph=candidate['summary'].get('access_graph'))))
    return dict(candidate_id=candidate['summary'].get('id'),
                case_revision=candidate['summary']['revision'], content_sha256=digest.hexdigest())


def encode_session(base, operations):
    payload = dict(schema=SCHEMA, algorithm=ALGORITHM, base=base_identity(base), operations=operations)
    return _encode(dict(payload=payload, sha256=hashlib.sha256(_encode(payload)).hexdigest())).decode()+'\n'


def restore_session(base, text, *, inspect_operation=None):
    """Recompute every operation; no geometry or PASS claims are trusted from disk."""
    from .candidate_radius_session import CandidateRadiusSession
    if not isinstance(text, str) or len(text.encode('utf-8')) > 1024*1024:
        raise ValueError('Radius session must be JSON text of at most 1 MiB')
    document = json.loads(text, object_pairs_hook=_unique_object)
    if not isinstance(document, dict) or set(document) != {'payload', 'sha256'}:
        raise ValueError('Invalid radius session envelope')
    payload = document['payload']
    if not isinstance(payload, dict) or set(payload) != {'schema', 'algorithm', 'base', 'operations'}:
        raise ValueError('Invalid radius session payload')
    if document['sha256'] != hashlib.sha256(_encode(payload)).hexdigest():
        raise ValueError('Radius session checksum mismatch')
    if payload['schema'] != SCHEMA or payload['algorithm'] != ALGORITHM:
        raise ValueError('Unsupported radius session or algorithm')
    if payload['base'] != base_identity(base):
        raise ValueError('Radius session base geometry, path or revision mismatch')
    if not isinstance(payload['operations'], list):
        raise ValueError('Radius operations must be a list')
    editor = CandidateRadiusSession(base)
    for operation in payload['operations']:
        if not isinstance(operation, dict) or set(operation) != {
                'source_name', 'scale', 'transition_mm', 'max_displacement_mm', 'output_geometry_sha256'}:
            raise ValueError('Invalid radius operation')
        if not isinstance(operation['source_name'], str) or any(
                type(operation[key]) not in (float, int)
                for key in ('scale', 'transition_mm', 'max_displacement_mm')):
            raise ValueError('Invalid radius parameter type')
        snapshot = editor.snapshot(operation['source_name'])
        result = editor.compute(snapshot, **{
            key:operation[key] for key in ('scale', 'transition_mm', 'max_displacement_mm')})
        if result['candidate']['summary']['geometry_sha256'] != operation['output_geometry_sha256']:
            raise ValueError('Replayed radius geometry differs from saved output')
        if inspect_operation is not None:
            inspect_operation(snapshot['candidate'], result)
        editor.apply(editor.publish(result)['token'])
    return editor
