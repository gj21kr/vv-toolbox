"""Validated, atomic case snapshots with optimistic revision checks."""
import hashlib
import json
import os
from pathlib import Path
import tempfile

from .case_contract import validate_case


def _encode(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode('utf-8')


def case_digest(case):
    validate_case(case)
    return hashlib.sha256(_encode(case)).hexdigest()


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON key: ' + key)
        result[key] = value
    return result


def load_case(path, *, expected_sources=None):
    """Return case and revision; never replace corrupt files with defaults.

    expected_sources maps exact source IDs to expected hashes. A digest detects
    corruption, not malicious rewriting; it is not an authenticity signature.
    """
    envelope = json.loads(Path(path).read_text(encoding='utf-8'), object_pairs_hook=_unique_object)
    if not isinstance(envelope, dict) or envelope.get('schema') != 'vv-toolbox.case-snapshot/1':
        raise ValueError('unsupported snapshot schema')
    case = envelope.get('case')
    revision = case_digest(case)
    if envelope.get('revision') != revision:
        raise ValueError('snapshot content hash mismatch')
    if expected_sources is not None:
        actual = {s['id']: s['sha256'].lower() for s in case['sources']}
        if actual != {key: value.lower() for key, value in expected_sources.items()}:
            raise ValueError('snapshot source identity mismatch')
    return case, revision


def save_case(path, case, *, expected_revision=None):
    """Create only by default; overwrite requires the current revision.

    Exclusive sibling lock serializes cooperating writers. An abandoned lock is
    reported and never automatically removed based on its age.
    """
    revision = case_digest(case)
    data = _encode({'schema': 'vv-toolbox.case-snapshot/1', 'revision': revision, 'case': case}) + b'\n'
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    lock = target.with_name(target.name + '.lock')
    try:
        lock_fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise ValueError('snapshot writer lock exists') from exc
    temporary = None
    try:
        os.close(lock_fd)
        if target.exists():
            _, current = load_case(target)
            if expected_revision != current:
                raise ValueError('snapshot revision conflict')
        elif expected_revision is not None:
            raise ValueError('expected snapshot is missing')
        fd, temporary = tempfile.mkstemp(prefix=target.name + '.', suffix='.tmp', dir=target.parent)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
        temporary = None
        return revision
    finally:
        if temporary is not None:
            Path(temporary).unlink(missing_ok=True)
        lock.unlink(missing_ok=True)
