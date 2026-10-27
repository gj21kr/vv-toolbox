"""Explicit registered-wall deformation and graph update for inspection cases."""
from copy import deepcopy
import hashlib

import numpy as np
import trimesh

from .case_io import case_digest, _encode
from .case_source_surfaces import attach_surfaces
from .centerline_containment import inspect_centerline_containment
from .union_shape import deform_selected_shape


def _source_chain(edges):
    """Order explicit source edges without inferring proximity connections."""
    if len(edges)==1:
        edge=edges[0]
        return edge['centerline_mm'], {edge['id']:(0,len(edge['centerline_mm']),False)}
    adjacency={}
    for edge in edges:
        if edge['start']==edge['end'] or edge.get('centerline_mm') is None:
            raise ValueError('Source requires an open connected chain')
        for node in (edge['start'],edge['end']):
            adjacency.setdefault(node,[]).append(edge)
    ends=sorted(node for node,items in adjacency.items() if len(items)==1)
    if len(ends)!=2 or any(len(items)>2 for items in adjacency.values()):
        raise ValueError('Branched or cyclic source needs a branch-aware field')
    node=ends[0]; used=set(); points=[]; spans={}
    while True:
        remaining=[edge for edge in adjacency[node] if edge['id'] not in used]
        if not remaining:break
        edge=remaining[0]; reverse=edge['end']==node
        line=edge['centerline_mm'][::-1] if reverse else edge['centerline_mm']
        if points and not np.array_equal(points[-1],line[0]):
            raise ValueError('Source chain endpoints must coincide exactly')
        start=max(0,len(points)-1)
        points.extend(line[1:] if points else line)
        spans[edge['id']]=(start,len(points),reverse)
        used.add(edge['id']); node=edge['start'] if reverse else edge['end']
    if len(used)!=len(edges):
        raise ValueError('Source has disconnected components')
    return points,spans


def source_edit_options(case):
    """Structural eligibility only; geometry checks run on each proposal."""
    options={}; groups={}
    for edge in case['edges']:
        groups.setdefault(edge.get('source_part_id'),[]).append(edge)
    for source,edges in groups.items():
        ids=sorted(edge['id'] for edge in edges)
        reason=None
        try:
            if not source:
                raise ValueError('원본 혈관 대응 정보가 없습니다.')
            if any(edge.get('centerline_mm') is None for edge in edges):
                raise ValueError('공동 편집할 모든 구간의 중심선이 필요합니다.')
            _source_chain(edges)
            parts=[part for part in case.get('surface_parts',[]) if set(ids)&set(part['edge_ids'])]
            if len(parts)!=1 or not parts[0].get('face_lineage') or not set(ids).issubset(parts[0]['edge_ids']):
                raise ValueError('모든 구간이 면 소유권이 있는 동일한 등록 표면에 속해야 합니다.')
            if any(lesion['edge_id'] in parts[0]['edge_ids'] for lesion in case.get('lesions',[])):
                raise ValueError('병변이 있는 표면의 공동 형상 편집은 지원하지 않습니다.')
        except ValueError as exc:
            reason=str(exc)
        for edge in edges:
            options[edge['id']]=dict(eligible=reason is None,reason=reason,affected_edge_ids=ids if reason is None else [])
    return options


def deform_registered_source(case, *, edge_id, **parameters):
    """Return a separate, unapproved case; never infer source ownership.

    Split-source chains share one field; graph nodes remain protected.
    """
    revision = case_digest(case)
    selected = next((e for e in case['edges'] if e['id'] == edge_id), None)
    if selected is None or selected.get('centerline_mm') is None:
        raise ValueError('Known edge with centerline required')
    source = selected.get('source_part_id')
    if not source:
        raise ValueError('Explicit source ownership required')
    source_edges=[e for e in case['edges'] if e.get('source_part_id')==source]
    chain,spans=_source_chain(source_edges)
    if len(spans)>1:
        for edge in source_edges:
            for node,point in ((edge['start'],edge['centerline_mm'][0]),(edge['end'],edge['centerline_mm'][-1])):
                position=case['nodes'][node].get('position_mm')
                if position is None or not np.array_equal(position,point):
                    raise ValueError('Source-chain junctions require exact graph positions')
    parts = [p for p in case.get('surface_parts', []) if edge_id in p['edge_ids']]
    if len(parts) != 1 or not parts[0].get('face_lineage'):
        raise ValueError('One registered surface with face lineage required')
    part = parts[0]
    if not set(spans).issubset(part['edge_ids']):
        raise ValueError('Every source segment must belong to the same registered surface')
    if any(l['edge_id'] in part['edge_ids'] for l in case.get('lesions', [])):
        raise ValueError('Registered shape edit with existing lesions is not supported')
    paths = [e for e in case['edges'] if e['id'] in part['edge_ids']]
    if any(e.get('centerline_mm') is None for e in paths):
        raise ValueError('Every affected surface edge needs a centerline')
    protected = [n['position_mm'] for n in case['nodes'].values() if n['position_mm'] is not None]
    mesh = trimesh.Trimesh(part['vertices_mm'], part['faces'], process=False)
    changed, line, audit = deform_selected_shape(mesh, part['face_lineage'], source,
        chain, protected_points_mm=protected, **parameters)
    result = deepcopy(case)
    result.pop('surface_parts')
    for edge in result['edges']:
        if edge['id'] in spans:
            start,end,reverse=spans[edge['id']]
            segment=line[start:end]
            if reverse:segment=segment[::-1]
            edge.update(centerline_mm=segment.tolist(), geometry_kind='estimated', evidence_status='synthetic_estimate')
    checked = []
    for edge in result['edges']:
        if edge['id'] not in part['edge_ids']:
            continue
        check = (audit['centerline_containment'] if len(spans)==1 and edge['id'] == edge_id else
                 inspect_centerline_containment(changed, edge['centerline_mm']))
        if check['status'] != 'PASS':
            raise ValueError('Affected surface graph containment not cleared: '+edge['id'])
        checked.append(dict(edge_id=edge['id'], containment=check))
    normalized = deepcopy(parameters)
    for key in ('bend_mm','twist_deg','collar_mm','transition_mm','max_displacement_mm'):
        normalized[key] = float(parameters[key])
    operation = dict(parent_case_revision=revision, edge_id=edge_id, source_part_id=source,
                     parameters=normalized)
    if len(spans)>1:
        operation['affected_edge_ids']=sorted(spans)
        audit['affected_edge_ids']=sorted(spans)
        audit['field_scope']='One source-chain chord with fixed graph nodes'
    operation_id = hashlib.sha256(_encode(operation)).hexdigest()[:20]
    result.update(case_id='registered-shape:'+operation_id, model_kind='synthetic',
        generation=dict(seed=0, generator_version='registered-source-shape/1', config=operation))
    previous = result.pop('inspection', {})
    historical = {key:result.pop(key) for key in (
        'candidate_surface_reference', 'quality', 'geometry_quality', 'surface_quality',
        'synthetic_route_inspection', 'centerline_regularization', 'radius_regularization') if key in result}
    result['inspection'] = dict(registered_shape_edit=dict(
        parent_case_revision=revision, source_part_id=source, edge_id=edge_id,
        parent_inspection=previous, parent_geometry_metadata=historical,
        parent_inspection_role='Historical only; edited geometry requires new checks',
        audit=audit, checked_paths=checked, neighboring_vessels='NOT RUN',
        radius_surface_consistency='NOT RUN', anatomical_acceptance='UNKNOWN',
        accepted_for_generation=False))
    revised = deepcopy(case['surface_parts'])
    for item in revised:
        if item['part_id'] == part['part_id']:
            item.update(vertices_mm=changed.vertices.tolist(), faces=changed.faces.tolist(), provenance='estimated',
                        lineage_scope='Inherited ownership; edited vertices are not original source coordinates')
    return attach_surfaces(result, revised)
