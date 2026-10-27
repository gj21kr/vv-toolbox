"""Read-only preview of hash-bound carotid solid union candidates."""
from io import BytesIO
import hashlib
import json
from pathlib import Path

import numpy as np


IDS={'left-carotid-solid-union':'estimated_left_carotid_neck',
     'right-carotid-solid-union':'estimated_right_carotid_neck'}


def load_carotid_preview(root,candidate_id):
    if candidate_id not in IDS:raise ValueError('Unknown carotid preview')
    root=Path(root);pid=IDS[candidate_id]
    def read(name):
        return json.loads((root/'docs/evidence'/name).read_text())
    union=read('carotid-solid-union-diagnostic-float64-lineage.json')
    lineage=read('carotid-union-lineage.json')
    paths=read('carotid-union-paths.json')
    neighbors=read('carotid-union-neighbors.json')
    if not (union['source_case_revision']==lineage['source_case_revision']==paths['source_case_revision']):
        raise ValueError('Carotid evidence revisions differ')
    def row(report):
        rows=[r for r in report['rows'] if r['part_id']==pid]
        if len(rows)!=1:raise ValueError('Unique carotid evidence row required')
        return rows[0]
    u,l,p=row(union),row(lineage),row(paths)
    raw=(root/'exports/carotid-solid-union-diagnostic-float64-lineage'/(pid+'.npz')).read_bytes()
    digest=hashlib.sha256(raw).hexdigest()
    neighbor_hash={r['part_id']:r['sha256'] for r in neighbors['union_files']}
    if not digest==l['union_sha256']==p['union_file_sha256']==neighbor_hash[pid]:
        raise ValueError('Carotid geometry does not match evidence')
    if (u['status']!='CANDIDATE' or u['self_contact']['status']!='NO_CONTACT_DETECTED'
            or u['boundary_components']!=1 or l['status']!='PASS' or p['status']!='PASS'
            or neighbors['new_contacting_neighbors'] or neighbors['unknown']):
        raise ValueError('Carotid candidate inspection incomplete')
    with np.load(BytesIO(raw),allow_pickle=False) as data:
        vertices=np.asarray(data['vertices']);faces=np.asarray(data['faces'])
    if (vertices.ndim!=2 or vertices.shape[1]!=3 or not np.isfinite(vertices).all()
            or faces.ndim!=2 or faces.shape[1]!=3 or not np.issubdtype(faces.dtype,np.integer)
            or not len(faces) or faces.min()<0 or faces.max()>=len(vertices)
            or len(faces)!=l['faces']):
        raise ValueError('Invalid carotid preview geometry')
    title=('좌측' if candidate_id.startswith('left') else '우측')+' 경동맥 · 내강 결합 후보'
    names=u['face_lineage']['source_names']
    labels={'FJ1682':'우측 내경동맥','FJ1682M':'좌측 내경동맥',
            'FJ3564':'우측 총경동맥','FJ3483':'좌측 총경동맥'}
    source_paths={};unavailable={}
    record_path=root/'docs/evidence/atlas-neck-volume-case.json'
    if record_path.exists():
        from .case_io import load_case
        from .candidate_centerlines import bind_source_centerlines
        record=json.loads(record_path.read_text())
        case_path=(root/record['derived_case_file']).resolve()
        if not case_path.is_relative_to(root.resolve()):
            raise ValueError('Candidate case must stay within workspace')
        case,revision=load_case(case_path)
        source_paths,unavailable=bind_source_centerlines(
            case,revision,union['source_case_revision'],names)
    return dict(vertices_mm=vertices.copy(),faces=faces.copy(),edges=[],face_lineage=u['face_lineage'],
        source_centerlines=source_paths,
        summary=dict(id=candidate_id,title=title,revision=union['source_case_revision'],
            surface_sha256=digest,vertices=len(vertices),triangles=len(faces),read_only=True,
            edge_ids=u['face_lineage']['source_names'],centerlines_available=False,
            selectable_sources=[dict(id=name,label=labels.get(name,'추정 목 연결부')+' · '+name) for name in names],
            selected_source=None,
            radius_path_sources=list(source_paths),radius_path_unavailable=unavailable,
            scope='원본 경동맥 두 부분과 추정 목 연결부를 결합한 합성 표면',
            carotid_union=dict(self_contact='NO_CONTACT_DETECTED',path_segments=p['segment_count'],
                lineage_faces=l['faces'],new_contacting_neighbors=0),
            anatomy='UNKNOWN',smoothness='NOT RUN'))
