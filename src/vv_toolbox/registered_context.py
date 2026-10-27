"""Fresh fixed-context inspection for registered-wall edit cases."""
from copy import deepcopy
import hashlib

import numpy as np
import trimesh

from .case_io import case_digest
from .radius_context import inspect_radius_context


def run_access_context(case,progress,root):
    """Inspect against the registered access parent's frozen native context."""
    import json
    from pathlib import Path
    from .case_io import load_case
    from .atlas import load_atlas
    from .atlas_neck import build_neck_repairs
    root=Path(root)
    parent,parent_revision=load_case(root/'exports/candidate-case-download/case.snapshot.json')
    if (case.get('generation') or {}).get('config',{}).get('parent_case_revision')!=parent_revision:
        raise ValueError('This context supports direct edits of the registered access parent only')
    baseline=json.loads((root/'docs/evidence/resampled-access-context.json').read_text())
    artifact=root/'exports/resampled-access-union/protected-candidate.npz'
    if hashlib.sha256(artifact.read_bytes()).hexdigest()!=baseline['candidate_sha256']:
        raise ValueError('Frozen parent surface changed')
    if len(parent.get('surface_parts',[]))!=1:
        raise ValueError('One registered access parent surface required')
    part=parent['surface_parts'][0]
    with np.load(artifact,allow_pickle=False) as data:
        if not np.array_equal(part['vertices_mm'],data['vertices']) or not np.array_equal(part['faces'],data['faces']):
            raise ValueError('Registered parent differs from frozen context parent')
    if set(part['face_lineage']['source_names'])!=set(baseline['excluded_union_sources']):
        raise ValueError('Frozen source exclusions changed')
    atlas=load_atlas();neck,_=build_neck_repairs(atlas)
    neighbors={p['id']:trimesh.Trimesh(p['vertices'],p['faces'],process=False)
        for p in [*atlas.meshes,*neck] if p['id'] not in baseline['excluded_union_sources']
        and p['layer'] in ('arterial','systemic_venous','hepatic_portal')}
    return inspect_registered_context(case,parent,neighbors,
        expected_context_sha256=baseline['context_sha256'],
        expected_neighbor_ids=[r['neighbor_id'] for r in baseline['rows']],progress=progress)


def context_fingerprint(neighbors):
    digest=hashlib.sha256()
    for name,mesh in sorted(neighbors.items()):
        encoded=name.encode('utf-8');digest.update(len(encoded).to_bytes(8,'little'));digest.update(encoded)
        for array in (np.asarray(mesh.vertices,dtype='<f8'),np.asarray(mesh.faces,dtype='<i8')):
            digest.update(str(array.shape).encode('ascii'));digest.update(array.tobytes())
    return digest.hexdigest()


def inspect_registered_context(case,parent,neighbors,*,expected_context_sha256,expected_neighbor_ids,progress=None):
    revision=case_digest(case); parent_revision=case_digest(parent)
    if (case.get('generation',{}).get('generator_version')!='registered-source-shape/1'
            or case['generation']['config']['parent_case_revision']!=parent_revision):
        raise ValueError('Exact registered shape parent required')
    if case['frame']!=parent['frame']:
        raise ValueError('Shared parent/candidate coordinate frame required')
    before=parent.get('surface_parts',[]);after=case.get('surface_parts',[])
    if len(before)!=1 or len(after)!=1 or before[0]['part_id']!=after[0]['part_id']:
        raise ValueError('One explicit registered union surface required')
    old,new=before[0],after[0]
    if (old['edge_ids']!=new['edge_ids'] or old['faces']!=new['faces']
            or len(old['vertices_mm'])!=len(new['vertices_mm'])):
        raise ValueError('Matching fixed surface topology required')
    ids=list(expected_neighbor_ids)
    if (not ids or len(set(ids))!=len(ids) or set(neighbors)!=set(ids)
            or context_fingerprint(neighbors)!=expected_context_sha256):
        raise ValueError('Complete frozen context required')
    result=inspect_radius_context(
        trimesh.Trimesh(old['vertices_mm'],old['faces'],process=False),
        trimesh.Trimesh(new['vertices_mm'],new['faces'],process=False),neighbors,progress=progress)
    if result['context_sha256']!=expected_context_sha256 or len(result['rows'])!=len(ids):
        raise ValueError('Context changed during inspection')
    result.update(case_revision=revision,parent_case_revision=parent_revision,
        before_geometry_sha256=old['geometry_sha256'],after_geometry_sha256=new['geometry_sha256'],
        neighbor_count=len(ids),completed=len(ids),accepted_for_generation=False,
        execution='Fresh before/after contact and containment inspection')
    return result


def case_with_context(case,report):
    if report['case_revision']!=case_digest(case) or report['status'] not in ('PASS','FAIL','UNKNOWN'):
        raise ValueError('Completed inspection of this exact case required')
    if (report['completed']!=report['neighbor_count'] or len(report['rows'])!=report['neighbor_count']
            or not report['neighbor_count']
            or len({r['neighbor_id'] for r in report['rows']})!=report['neighbor_count']
            or report['parent_case_revision']!=case['generation']['config']['parent_case_revision']
            or report['after_geometry_sha256']!=case['surface_parts'][0]['geometry_sha256']):
        raise ValueError('Incomplete context inspection')
    if report['status']=='PASS' and (report['new_or_extended_contacts'] or report['unknown']
            or report['remaining_contacts'] or any(not r['before']['complete'] or not r['after']['complete']
                or r['after']['status']!='SEPARATED' for r in report['rows'])):
        raise ValueError('Invalid context PASS')
    result=deepcopy(case)
    audit=result['inspection']['registered_shape_edit']
    previous={key:audit.pop(key) for key in ('context','context_binding') if key in audit}
    if previous:
        audit.setdefault('context_history',[]).append(previous)
    audit.update(neighboring_vessels=report['status'],context=deepcopy(report),accepted_for_generation=False)
    case_digest(result)
    return result
