"""Transactional interval surface application; callers supply a scene renderer."""
from copy import deepcopy

import numpy as np

from .atlas_edit_session import AtlasEditConflict
from .atlas_interval_preview import snapshot_interval_workspace
from .interval_revalidation import prepare_revalidation, revalidate_interval_snapshot


def apply_interval(workspace, text, expected_generation, render):
    """Revalidate outside the lock, then publish or roll back under the lock.

    ``render`` must synchronously rebuild the view from workspace state. Interval
    records are separate from legacy parameter edits. This function never saves.
    """
    with workspace.lock:
        _ready(workspace, expected_generation)
        _, _, request = prepare_revalidation(
            text, atlas_sha256=workspace.atlas.metadata.get('sha256'))
        snapshot = snapshot_interval_workspace(workspace, request)
        workspace.interval_preview_busy = True
    try:
        candidate = revalidate_interval_snapshot(snapshot, text)
        with workspace.lock:
            _ready(workspace, expected_generation, own_computation=True)
            pid = candidate['part_id']
            source = next(p for p in [*workspace.atlas.meshes, *workspace.neck_parts]
                          if p['id'] == pid)
            part = deepcopy(workspace.atlas_modified_parts.get(pid, source))
            part['vertices'] = np.asarray(candidate['vertices'], dtype=float)
            part['faces'] = np.asarray(candidate['faces'], dtype=np.int64)
            part['edit_checks'] = deepcopy(candidate['checks'])
            replacements = dict(workspace.atlas_modified_parts)
            replacements[pid] = part
            records = deepcopy(getattr(workspace, 'atlas_interval_edits', {}))
            candidate['operation_index'] = 1 + max(
                (c.get('operation_index', c['generation']) for values in records.values() for c in values),
                default=0)
            records.setdefault(pid, []).append(deepcopy(candidate))
            history = deepcopy(getattr(workspace, 'atlas_interval_undo', []))
            # An intervening operation makes older full-scene snapshots unsafe.
            if history and history[-1]['generation'] != workspace.generation:
                history = []
            history.append(dict(
                part_id=pid, generation=workspace.generation + 1,
                parts=deepcopy(workspace.atlas_modified_parts),
                records=deepcopy(getattr(workspace, 'atlas_interval_edits', {}))))
            _publish(workspace, replacements, records, history, render)
            return dict(status='APPLIED', part_id=pid, generation=workspace.generation)
    finally:
        with workspace.lock:
            workspace.interval_preview_busy = False


def _ready(workspace, generation, own_computation=False):
    if (type(generation) is not int or generation != workspace.generation
            or workspace.source != 'atlas' or workspace.busy
            or (getattr(workspace, 'interval_preview_busy', False) and not own_computation)
            or getattr(workspace, 'atlas_edit_recovery_error', None)):
        raise AtlasEditConflict('Atlas scene changed, busy or requires recovery')


def undo_interval(workspace, expected_generation, render):
    """Undo the latest interval operation only while its scene is still current."""
    with workspace.lock:
        _ready(workspace, expected_generation)
        history = deepcopy(getattr(workspace, 'atlas_interval_undo', []))
        if not history or history[-1]['generation'] != workspace.generation:
            raise AtlasEditConflict('No interval undo for the current scene')
        entry = history.pop()
        if history:
            history[-1]['generation'] = workspace.generation + 1
        _publish(workspace, entry['parts'], entry['records'], history, render)
        return dict(status='UNDONE', part_id=entry['part_id'], generation=workspace.generation)


def _publish(workspace, replacements, records, history, render):
    prior = (workspace.atlas_modified_parts,
             getattr(workspace, 'atlas_interval_edits', {}),
             getattr(workspace, 'atlas_interval_undo', []), workspace.generation)
    workspace.atlas_modified_parts = replacements
    workspace.atlas_interval_edits = records
    workspace.atlas_interval_undo = history
    workspace.generation += 1
    try:
        render()
    except Exception:
        (workspace.atlas_modified_parts, workspace.atlas_interval_edits, workspace.atlas_interval_undo,
         workspace.generation) = prior
        try:
            render()
        except Exception as error:
            workspace.atlas_edit_recovery_error = 'Interval scene rollback failed; recovery required'
            raise RuntimeError(workspace.atlas_edit_recovery_error) from error
        raise
