"""Ordered interval edit sessions with staged, fully revalidated restoration."""
from copy import deepcopy
import hashlib
import json
import threading
from types import SimpleNamespace

import numpy as np

from .atlas_edit_session import canonical_modifications, AtlasEditConflict
from .case_io import _encode, _unique_object
from .interval_snapshot import encode_interval_snapshot, decode_interval_snapshot
from .interval_application import apply_interval, _ready, _publish

SCHEMA = 'vv-toolbox.interval-session/1'


def encode_session(workspace):
    with workspace.lock:
        _ready(workspace, workspace.generation)
        entries = [c for values in getattr(workspace, 'atlas_interval_edits', {}).values()
                   for c in values]
        if not entries:
            raise ValueError('No active interval edits')
        order = lambda c: c.get('operation_index', c['generation'])
        entries.sort(key=order)
        generations = [order(c) for c in entries]
        if any(type(g) is not int for g in generations) or len(set(generations)) != len(entries):
            raise ValueError('Ambiguous interval operation order')
        for pid, values in workspace.atlas_interval_edits.items():
            last = max(values, key=order)
            part = workspace.atlas_modified_parts.get(pid)
            if part is None or any(not np.array_equal(part[k], last[k]) for k in ('vertices', 'faces')):
                raise ValueError('Active surface differs from interval history')
        content = dict(atlas_sha256=workspace.atlas.metadata['sha256'],
                       base_modifications=canonical_modifications(getattr(workspace, 'atlas_modifications', {})),
                       snapshots=[encode_interval_snapshot(c)[0].decode() for c in entries])
        revision = hashlib.sha256(_encode(content)).hexdigest()
        return _encode(dict(schema=SCHEMA, revision=revision, content=content)) + b'\n', revision


def decode_session(text, atlas_sha256):
    value = json.loads(text, object_pairs_hook=_unique_object)
    if not isinstance(value, dict) or set(value) != {'schema', 'revision', 'content'} or value['schema'] != SCHEMA:
        raise ValueError('Invalid interval session')
    content = value['content']
    if not isinstance(content, dict) or set(content) != {'atlas_sha256', 'base_modifications', 'snapshots'}:
        raise ValueError('Invalid interval session content')
    if hashlib.sha256(_encode(content)).hexdigest() != value['revision']:
        raise ValueError('Interval session hash mismatch')
    if content['atlas_sha256'] != atlas_sha256:
        raise ValueError('Atlas source mismatch')
    if canonical_modifications(content['base_modifications']) != content['base_modifications']:
        raise ValueError('Noncanonical base modifications')
    if not isinstance(content['snapshots'], list) or not content['snapshots']:
        raise ValueError('Ordered interval snapshots required')
    for snapshot in content['snapshots']:
        decode_interval_snapshot(snapshot, expected_atlas_sha256=atlas_sha256)
    return content, value['revision']


def restore_session(workspace, text, expected_generation, render):
    """Restore onto the matching base scene, publishing only after all edits pass."""
    with workspace.lock:
        _ready(workspace, expected_generation)
        if getattr(workspace, 'atlas_interval_edits', {}):
            raise AtlasEditConflict('Undo active intervals before restoring a session')
        content, revision = decode_session(text, workspace.atlas.metadata['sha256'])
        if content['base_modifications'] != canonical_modifications(getattr(workspace, 'atlas_modifications', {})):
            raise AtlasEditConflict('Restore the matching base vessel parameters first')
        scratch = SimpleNamespace(
            lock=threading.RLock(), source='atlas', busy=False, generation=workspace.generation,
            atlas=SimpleNamespace(meshes=deepcopy(workspace.atlas.meshes),
                                  metadata=deepcopy(workspace.atlas.metadata)),
            neck_parts=deepcopy(workspace.neck_parts),
            atlas_modified_parts=deepcopy(workspace.atlas_modified_parts),
            atlas_centerlines=deepcopy(workspace.atlas_centerlines))
        workspace.interval_preview_busy = True
    try:
        for snapshot in content['snapshots']:
            apply_interval(scratch, snapshot, scratch.generation, lambda: None)
        with workspace.lock:
            _ready(workspace, expected_generation, own_computation=True)
            history = scratch.atlas_interval_undo
            history[-1]['generation'] = workspace.generation + 1
            _publish(workspace, scratch.atlas_modified_parts, scratch.atlas_interval_edits, history, render)
            return dict(status='RESTORED', generation=workspace.generation,
                        revision=revision, operations=len(content['snapshots']))
    finally:
        with workspace.lock:
            workspace.interval_preview_busy = False
