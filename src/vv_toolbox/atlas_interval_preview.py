"""Read-only interval preview against the current Atlas scene."""
from copy import deepcopy
from types import SimpleNamespace
import hashlib

import numpy as np

from .atlas_edit_checks import AtlasEditCheckFailure
from .interval_candidate import build_interval_candidate
from .mesh_pair_contact import inspect_pair_contact


def snapshot_interval_workspace(workspace, raw):
    """Copy a coherent scene under the caller's lock; compute outside it."""
    required = {'part_id', 'edge_id', 'start_mm', 'end_mm', 'factor',
                'max_displacement_mm', 'absolute_scale_tolerance'}
    if not isinstance(raw, dict) or set(raw) != required:
        raise ValueError('Explicit interval, displacement and target tolerance required')
    if workspace.source != 'atlas' or workspace.atlas_centerlines is None:
        raise ValueError('Atlas centerlines must be available')
    return SimpleNamespace(
        source=workspace.source, generation=workspace.generation,
        atlas=SimpleNamespace(meshes=deepcopy(workspace.atlas.meshes),
                              metadata=deepcopy(getattr(workspace.atlas,'metadata',{}))),
        neck_parts=deepcopy(workspace.neck_parts),
        atlas_modified_parts=deepcopy(workspace.atlas_modified_parts),
        atlas_centerlines=dict(edges=deepcopy([
            e for e in workspace.atlas_centerlines['edges'] if e['part_id'] == raw['part_id']])),
        atlas_edit_recovery_error=getattr(workspace, 'atlas_edit_recovery_error', None))


def preview_interval(workspace, raw):
    required = {'part_id', 'edge_id', 'start_mm', 'end_mm', 'factor',
                'max_displacement_mm', 'absolute_scale_tolerance'}
    if not isinstance(raw, dict) or set(raw) != required:
        raise ValueError('Explicit interval, displacement and target tolerance required')
    if workspace.source != 'atlas' or workspace.atlas_centerlines is None:
        raise ValueError('Atlas centerlines must be available')
    if getattr(workspace, 'atlas_edit_recovery_error', None):
        raise ValueError('Atlas recovery required')
    original = [p for p in [*workspace.atlas.meshes, *workspace.neck_parts]
                if p['layer'] != 'context']
    parts = {p['id']: workspace.atlas_modified_parts.get(p['id'], p) for p in original}
    if len(parts) != len(original):
        raise ValueError('Ambiguous scene part identities')
    if raw['part_id'] not in parts:
        raise ValueError('Unknown vessel')
    part = parts[raw['part_id']]
    edges = [e for e in workspace.atlas_centerlines['edges'] if e['part_id'] == part['id']]
    if len(edges) != 1 or edges[0]['id'] != raw['edge_id']:
        raise ValueError('This preview requires a single centerline edge; multi-branch editing is not supported yet')
    points = edges[0]['points']
    if not 5 <= len(points) <= 5000:
        raise ValueError('Preview requires 5–5000 centerline stations')
    neighbors = [p for ident, p in parts.items() if ident != part['id']]
    vertices, faces = np.asarray(part['vertices']), np.asarray(part['faces'])
    low, high = vertices.min(axis=0), vertices.max(axis=0)
    fixed = set()
    for other in neighbors:
        ov = np.asarray(other['vertices'])
        if np.any(ov.min(axis=0) > high + 1e-8) or np.any(ov.max(axis=0) < low - 1e-8):
            continue
        check = inspect_pair_contact(vertices[faces], ov[np.asarray(other['faces'])])
        if not check['complete']:
            raise AtlasEditCheckFailure('Original contact protection could not be determined')
        if check['contact_pairs']:
            fixed.update(faces[sorted({pair[0] for pair in check['contact_pairs']})].ravel().tolist())
    candidate = build_interval_candidate(
        part, points, start_mm=raw['start_mm'], end_mm=raw['end_mm'], factor=raw['factor'],
        protected_vertex_ids=sorted(fixed), max_displacement_mm=raw['max_displacement_mm'],
        absolute_scale_tolerance=raw['absolute_scale_tolerance'],
        neighbors=neighbors, expected_neighbor_ids=[p['id'] for p in neighbors])
    source_digest=hashlib.sha256()
    for array in (np.asarray(part['vertices'],dtype='<f8'),np.asarray(part['faces'],dtype='<i8')):
        source_digest.update(str(array.shape).encode('ascii'))
        source_digest.update(array.tobytes())
    candidate_digest=hashlib.sha256()
    for array in (np.asarray(candidate['vertices'],dtype='<f8'),np.asarray(candidate['faces'],dtype='<i8')):
        candidate_digest.update(str(array.shape).encode('ascii'))
        candidate_digest.update(array.tobytes())
    candidate['edit_checks']['candidate_geometry_sha256']=candidate_digest.hexdigest()
    return dict(status='CANDIDATE', read_only=True, generation=workspace.generation,
                geometry_sha256=candidate_digest.hexdigest(),
                source=dict(atlas_sha256=getattr(workspace.atlas,'metadata',{}).get('sha256'),
                            part_geometry_sha256=source_digest.hexdigest()),
                frame=dict(id='bodyparts3d_native_LPS',axes='LPS',units='mm'),
                centerline_mm=deepcopy(points),
                part_id=part['id'], edge_id=raw['edge_id'], units='mm', layer=part['layer'],
                vertices=candidate['vertices'].tolist(), faces=candidate['faces'].tolist(),
                reference_vertices=np.asarray(part['vertices']).tolist(),
                checks=candidate['edit_checks'], interval_edit=candidate['interval_edit'],
                original_modified=False, applied=False)
