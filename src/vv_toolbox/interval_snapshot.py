"""Immutable geometry snapshots of interval candidates, separate from Atlas saves."""
import hashlib
import json
import os
from pathlib import Path
import tempfile

import numpy as np

from .case_io import _encode, _unique_object

SCHEMA = 'vv-toolbox.interval-candidate-snapshot/1'


def _validate(candidate):
    if not isinstance(candidate, dict) or candidate.get('status') != 'CANDIDATE' or candidate.get('applied') is not False:
        raise ValueError('Unapplied candidate required')
    if candidate.get('frame') != dict(id='bodyparts3d_native_LPS', axes='LPS', units='mm') or candidate.get('units') != 'mm':
        raise ValueError('Explicit native LPS millimetre frame required')
    for key in ('part_id', 'edge_id'):
        if not isinstance(candidate.get(key), str) or not candidate[key]:
            raise ValueError('Part and edge identity required')
    for key in ('atlas_sha256', 'part_geometry_sha256'):
        value = candidate.get('source', {}).get(key)
        if not isinstance(value, str) or len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
            raise ValueError('Complete source fingerprints required')
    arrays = {}
    for key in ('vertices', 'reference_vertices', 'centerline_mm'):
        array = np.asarray(candidate.get(key), dtype=float)
        if array.ndim != 2 or array.shape[1] != 3 or len(array) < 3 or not np.isfinite(array).all():
            raise ValueError('Finite surface and centerline coordinates required')
        arrays[key] = array
    faces = np.asarray(candidate.get('faces'))
    if (faces.ndim != 2 or faces.shape[1] != 3 or not len(faces)
            or not np.issubdtype(faces.dtype, np.integer) or faces.min() < 0
            or faces.max() >= len(arrays['vertices'])
            or arrays['vertices'].shape != arrays['reference_vertices'].shape):
        raise ValueError('Corresponding source/candidate topology required')
    digest = hashlib.sha256()
    for array in (np.asarray(arrays['reference_vertices'], dtype='<f8'), np.asarray(faces, dtype='<i8')):
        digest.update(str(array.shape).encode('ascii')); digest.update(array.tobytes())
    if digest.hexdigest() != candidate['source']['part_geometry_sha256']:
        raise ValueError('Reference surface fingerprint mismatch')
    if not isinstance(candidate.get('checks'), dict) or not isinstance(candidate.get('interval_edit'), dict):
        raise ValueError('Recorded edit conditions and checks required')
    digest = hashlib.sha256()
    for array in (np.asarray(arrays['vertices'], dtype='<f8'), np.asarray(faces, dtype='<i8')):
        digest.update(str(array.shape).encode('ascii')); digest.update(array.tobytes())
    if (candidate.get('geometry_sha256') != digest.hexdigest()
            or candidate['checks'].get('candidate_geometry_sha256') != digest.hexdigest()):
        raise ValueError('Candidate geometry and recorded checks fingerprint mismatch')
    # Encoding also rejects nonfinite values hidden in metadata.
    _encode(candidate)


def encode_interval_snapshot(candidate):
    _validate(candidate)
    revision = hashlib.sha256(_encode(candidate)).hexdigest()
    return _encode(dict(schema=SCHEMA, revision=revision, candidate=candidate)) + b'\n', revision


def load_interval_snapshot(path, *, expected_atlas_sha256=None):
    return decode_interval_snapshot(Path(path).read_text(encoding='utf-8'),
                                    expected_atlas_sha256=expected_atlas_sha256)


def decode_interval_snapshot(text, *, expected_atlas_sha256=None):
    value = json.loads(text, object_pairs_hook=_unique_object)
    if not isinstance(value, dict) or set(value) != {'schema', 'revision', 'candidate'} or value['schema'] != SCHEMA:
        raise ValueError('Invalid interval snapshot envelope')
    _, revision = encode_interval_snapshot(value['candidate'])
    if revision != value['revision']:
        raise ValueError('Interval snapshot content hash mismatch')
    if expected_atlas_sha256 is not None and value['candidate']['source']['atlas_sha256'] != expected_atlas_sha256:
        raise ValueError('Atlas source mismatch')
    return value['candidate'], revision


def process_snapshot_request(raw, *, expected_atlas_sha256):
    if not isinstance(expected_atlas_sha256, str) or len(expected_atlas_sha256) != 64:
        raise ValueError('Current Atlas source identity unavailable')
    if not isinstance(raw, dict):
        raise ValueError('Snapshot request required')
    if raw.get('action') == 'export' and set(raw) == {'action', 'candidate'}:
        data, revision = encode_interval_snapshot(raw['candidate'])
        if raw['candidate']['source']['atlas_sha256'] != expected_atlas_sha256:
            raise ValueError('Atlas source mismatch')
        return dict(snapshot_text=data.decode('utf-8'), revision=revision)
    if raw.get('action') == 'import' and set(raw) == {'action', 'snapshot_text'} and isinstance(raw['snapshot_text'], str):
        candidate, revision = decode_interval_snapshot(
            raw['snapshot_text'], expected_atlas_sha256=expected_atlas_sha256)
        return dict(candidate=candidate, revision=revision, snapshot_text=raw['snapshot_text'],
                    integrity='PASS', geometry_revalidation='NOT RUN', applied=False)
    raise ValueError('Invalid snapshot action')


def save_interval_snapshot(directory, candidate):
    """Create immutable content-addressed file; never replace source or old edits."""
    data, revision = encode_interval_snapshot(candidate)
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    destination = folder / (revision + '.json')
    fd, temporary = tempfile.mkstemp(prefix='.interval-', suffix='.tmp', dir=folder)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data); stream.flush(); os.fsync(stream.fileno())
        try:
            os.link(temporary, destination)
        except FileExistsError:
            if destination.read_bytes() != data:
                raise ValueError('Existing immutable snapshot differs')
    finally:
        os.unlink(temporary)
    return destination, revision
