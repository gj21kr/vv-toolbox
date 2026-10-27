"""Revision-bound, read-only comparison of eight protected cerebral surfaces."""
import hashlib
from io import BytesIO
import itertools
import json
from pathlib import Path

import numpy as np
import trimesh

REFERENCE_ID='cerebral-protected-reference'
CANDIDATE_ID='cerebral-protected-fit'


def load_protected_preview(root, *, reference=False):
    from .atlas import load_atlas
    root=Path(root).resolve()
    raw=(root/'docs/evidence/protected-cerebral-fit.json').read_bytes()
    candidate=json.loads(raw)
    scene_raw=(root/'docs/evidence/protected-cerebral-scene.json').read_bytes()
    scene=json.loads(scene_raw)
    atlas=load_atlas()
    if (scene['input_candidate_report_sha256']!=hashlib.sha256(raw).hexdigest()
            or candidate['atlas_archive_sha256']!=atlas.metadata['sha256']
            or scene['atlas_archive_sha256']!=atlas.metadata['sha256']):
        raise ValueError('Protected preview source/evidence mismatch')
    parts={p['id']:p for p in atlas.meshes if p['layer']=='arterial'}
    rows=candidate['rows'];selected={r['source_part_id'] for r in rows}
    if len(rows)!=8 or len(selected)!=8 or not selected<=parts.keys():
        raise ValueError('Complete eight-part cerebral candidate required')
    expected={pair for pair in itertools.combinations(sorted(parts),2) if any(p in selected for p in pair)}
    pairs=[tuple(p) for p in scene['bounds_separated_pairs']]+[tuple(r['parts']) for r in scene['rows']]
    if len(pairs)!=len(set(pairs)) or set(pairs)!=expected:
        raise ValueError('Incomplete simultaneous scene coverage')
    for pair in scene['rows']:
        if (not all(pair[s]['complete'] for s in ('before','after'))
                or set(map(tuple,pair['before']['contact_pairs']))!=set(map(tuple,pair['after']['contact_pairs']))
                or pair['gained_face_pairs'] or pair['lost_face_pairs']):
            raise ValueError('Contact-pair preservation not established')
    vertices=[];faces=[];offset=0
    for row in rows:
        ident=row['source_part_id'];part=parts[ident]
        path=(root/row['artifact']).resolve()
        if not path.is_relative_to(root/'exports'):
            raise ValueError('Candidate must be a local registered export')
        data=path.read_bytes();digest=hashlib.sha256(data).hexdigest()
        if digest!=row['sha256'] or scene['replacement_sha256'].get(ident)!=digest:
            raise ValueError('Protected artifact identity mismatch')
        if (row['status']!='CANDIDATE'
                or row['self_contact']['status']!='NO_CONTACT_DETECTED'
                or row['self_contact']['coverage']!='all distinct triangle pairs'
                or row['self_contact']['contact_pairs']):
            raise ValueError('Complete self-contact screening required')
        mesh=trimesh.load(BytesIO(data),file_type='ply',process=False)
        fixed=row['protected_vertex_ids']
        if (not np.array_equal(mesh.faces,part['faces'])
                or not np.array_equal(mesh.vertices[fixed],np.asarray(part['vertices'])[fixed])):
            raise ValueError('Protected source topology or positions changed')
        v=np.asarray(part['vertices'] if reference else mesh.vertices)
        f=np.asarray(part['faces'] if reference else mesh.faces)
        vertices.append(v);faces.append(f+offset);offset+=len(v)
    v=np.concatenate(vertices);f=np.concatenate(faces)
    summary=dict(id=REFERENCE_ID if reference else CANDIDATE_ID,
        title='뇌혈관 8개 · 원본 비교' if reference else '뇌혈관 8개 · 끝단 보존 보정 후보',
        revision=hashlib.sha256(scene_raw).hexdigest(),edge_ids=[r['edge_id'] for r in rows],
        vertices=len(v),triangles=len(f),read_only=True,
        scope='동일한 8개 원본 표면' if reference else '원본 끝단과 접촉면을 고정한 8개 합성 표면',
        protected_comparison=dict(reference=reference,parts=8,affected_pairs=len(expected),
            self_contact='NO_CONTACT_DETECTED' if not reference else 'candidate checked separately',
            gained_contact_pairs=0,lost_contact_pairs=0),
        centerlines_available=False,anatomy='UNKNOWN',volume_containment='NOT RUN')
    return dict(summary=summary,vertices_mm=v,faces=f,edges=[])
