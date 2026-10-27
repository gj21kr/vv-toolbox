"""Read-only replacement preview with ancestry and complete path coverage checks."""
import hashlib
import json
from pathlib import Path

import numpy as np

from .access_union_preview import load_access_union_preview

CANDIDATE_ID='resampled-access-protected'


def load_resampled_access_preview(root):
    root=Path(root);evidence=root/'docs/evidence'
    read=lambda name:json.loads((evidence/name).read_text())
    base=load_access_union_preview(root)
    parent=read('resampled-access-union.json');record=read('resampled-access-protected.json')
    path=(root/record['artifact']).resolve()
    if not path.is_relative_to(root.resolve()):raise ValueError('Preview artifact escapes workspace')
    if (hashlib.sha256(path.read_bytes()).hexdigest()!=record['output_sha256']
            or record['status']!='CANDIDATE' or record['self_contact']['status']!='NO_CONTACT_DETECTED'
            or record['parent_sha256']!=parent['output_sha256']
            or parent['parent_sha256']!=base['summary']['surface_sha256']
            or parent['lineage_check']['status']!='PASS' or parent['union']['boundary_components']!=1
            or not record['closed_positive_volume'] or not record['faces_unchanged']
            or record['restoration']['status']!='PASS' or not record['restoration']['protected_positions_exact']):
        raise ValueError('Replacement evidence mismatch')
    with np.load(path,allow_pickle=False) as data:
        vertices,faces=data['vertices'].copy(),data['faces'].copy()
    lineage=parent['face_lineage'];owners=np.asarray(lineage['face_source_indices'])
    if (vertices.ndim!=2 or vertices.shape[1]!=3 or not np.isfinite(vertices).all()
            or faces.ndim!=2 or faces.shape[1]!=3 or not len(faces)
            or not np.issubdtype(faces.dtype,np.integer) or faces.min()<0 or faces.max()>=len(vertices)
            or owners.shape!=(len(faces),) or not np.issubdtype(owners.dtype,np.integer)
            or owners.min()<0 or owners.max()>=len(lineage['source_names'])
            or parent['lineage_check']['faces']!=len(faces)):
        raise ValueError('Replacement ownership/geometry mismatch')
    paths=read('resampled-access-paths.json');ids={e['id'] for e in base['edges']}
    if (not ids or paths['surface_sha256']!=record['output_sha256']
            or paths['graph_revision']!=base['summary']['access_graph']['revision']
            or paths['status']!='PASS' or paths['expected_edges']!=len(ids)
            or len(paths['rows'])!=len(ids) or {r['edge_id'] for r in paths['rows']}!=ids
            or any(r['status']!='PASS' for r in paths['rows'])):
        raise ValueError('Complete replacement path evidence required')
    audit=base['summary']['access_union']
    audit.update(lineage_faces=len(faces),centerline_status='PASS',checked_paths=len(ids),
        checked_segments=sum(r['segment_count'] for r in paths['rows']),
        context_status='NOT RUN',context_neighbors=0,context_completed=0,contacts=[],unknown=[])
    context_path=evidence/'resampled-access-context.json'
    if context_path.exists():
        context=json.loads(context_path.read_text())
        state=context['status'];rows=context['rows'];total=context['neighbor_count']
        if (context['candidate_sha256']!=record['output_sha256']
                or context['source_case_revision']!=record['source_case_revision']
                or state not in ('RUNNING','UNKNOWN','PASS','FAIL')
                or len(rows)>total or context['completed']!=len(rows)
                or len({r['neighbor_id'] for r in rows})!=len(rows)
                or (state!='RUNNING' and len(rows)!=total)
                or set(context['excluded_union_sources'])!=set(lineage['source_names'])):
            raise ValueError('Replacement context scope mismatch')
        contacts=[r['neighbor_id'] for r in rows if r['status'] in ('SURFACE_CONTACT','CONTAINMENT')]
        unknown=[r['neighbor_id'] for r in rows if not r['complete']]
        if state=='PASS' and (contacts or unknown):raise ValueError('Invalid context PASS')
        audit.update(context_status=state,context_neighbors=total,context_completed=len(rows),contacts=contacts,unknown=unknown)
    base.update(vertices_mm=vertices,faces=faces,face_lineage=lineage)
    case_record = evidence/'atlas-neck-volume-case.json'
    if case_record.exists():
        from .case_io import load_case
        from .candidate_centerlines import bind_source_centerlines
        case_path = (root/json.loads(case_record.read_text())['derived_case_file']).resolve()
        if not case_path.is_relative_to(root.resolve()):
            raise ValueError('Candidate case must stay within workspace')
        case, revision = load_case(case_path)
        editable, unavailable = bind_source_centerlines(
            case, revision, record['source_case_revision'], lineage['source_names'])
        base['source_centerlines'] = editable
        base['summary'].update(radius_path_sources=list(editable), radius_path_unavailable=unavailable)
    base['summary'].update(id=CANDIDATE_ID,title='대퇴–전방순환 · 목 메시 개선 후보',
        surface_sha256=record['output_sha256'],vertices=len(vertices),triangles=len(faces),
        scope='원본 분지 보호 · 추정 우측 목 내부 메시 재구성 · 해부학적 수용 및 주변 검사 별도',
        smoothness='UNKNOWN')
    return base
