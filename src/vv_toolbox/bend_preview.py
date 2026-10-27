"""Read-only real-access bend preview with graph and context evidence binding."""
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh

from .case_io import load_case
from .resampled_access_preview import load_resampled_access_preview
from .union_selection import select_union_source

CANDIDATE_ID = 'access-femoral-bend-inspection'


def load_bend_preview(root):
    root = Path(root)
    evidence = root/'docs/evidence'
    read = lambda name: json.loads((evidence/name).read_text())
    base = load_resampled_access_preview(root)
    edit = read('access-shape-edit-bend.json')
    paths = read('access-bend-graph.json')
    graph, revision = load_case(root/'exports/access-shape-edit-bend/graph.snapshot.json')
    artifact = root/'exports/access-shape-edit-bend/candidate.npz'
    raw_hash = hashlib.sha256(artifact.read_bytes()).hexdigest()
    with np.load(artifact, allow_pickle=False) as data:
        vertices, faces = data['vertices'], data['faces']
    digest = hashlib.sha256(vertices.astype('<f8').tobytes()+faces.astype('<i8').tobytes()).hexdigest()
    if (edit['status'] != 'CANDIDATE' or edit['parent_surface_sha256'] != base['summary']['surface_sha256']
            or paths['status'] != 'PASS' or paths['graph_revision'] != revision
            or paths['parent_graph_revision'] != base['summary']['access_graph']['revision']
            or paths['geometry_sha256'] != digest or not np.array_equal(faces, base['faces'])
            or vertices.shape != base['vertices_mm'].shape or not np.isfinite(vertices).all()
            or len(paths['rows']) != len(graph['edges'])
            or {r['edge_id'] for r in paths['rows']} != {e['id'] for e in graph['edges']}
            or any(r['status'] != 'PASS' for r in paths['rows'])):
        raise ValueError('Bend geometry/graph evidence mismatch')
    selection = select_union_source(base['vertices_mm'], faces, base['face_lineage'], edit['source'])
    fixed = np.setdiff1d(np.arange(len(vertices)), selection['exclusive_vertex_ids'])
    if not np.array_equal(vertices[fixed], base['vertices_mm'][fixed]):
        raise ValueError('Bend moved other sources or shared interfaces')
    if not trimesh.Trimesh(vertices, faces, process=False).is_volume:
        raise ValueError('Closed positive bend surface required')
    if edit['audit']['self_contact']['status'] != 'NO_CONTACT_DETECTED':
        raise ValueError('Bend self-contact evidence not clear')
    context = read('access-bend-context.json')
    baseline = read('resampled-access-context.json')
    rows = context['rows']
    baseline_ids = {r['neighbor_id'] for r in baseline['rows']}
    row_ids = {r['neighbor_id'] for r in rows}
    if (context['before_sha256'] != edit['parent_surface_sha256'] or context['after_sha256'] != raw_hash
            or context['context_sha256'] != baseline['context_sha256']
            or context['neighbor_count'] != baseline['neighbor_count']
            or len(baseline_ids) != baseline['neighbor_count']
            or len(baseline['rows']) != baseline['neighbor_count']
            or not row_ids.issubset(baseline_ids)
            or context['completed'] != len(rows) or len({r['neighbor_id'] for r in rows}) != len(rows)
            or len(rows) > context['neighbor_count']
            or context['status'] not in ('RUNNING', 'PASS', 'FAIL', 'UNKNOWN')
            or (context['status'] != 'RUNNING' and len(rows) != context['neighbor_count'])):
        raise ValueError('Bend context evidence mismatch')
    contacts = [r['neighbor_id'] for r in rows if r['after']['status'] in ('SURFACE_CONTACT', 'CONTAINMENT')]
    unknown = [r['neighbor_id'] for r in rows if not r['after']['complete'] or not r['before']['complete']]
    if context['status'] == 'PASS' and (contacts or unknown):
        raise ValueError('Invalid bend context PASS')
    base.update(vertices_mm=vertices, faces=faces, edges=graph['edges'], geometry_context=context)
    base.pop('source_centerlines', None)
    summary = base['summary']
    summary.update(id=CANDIDATE_ID, title='대퇴 굴곡 0.25 mm · 검사 후보',
        surface_sha256=raw_hash, geometry_sha256=digest, read_only=True,
        radius_path_sources=[], radius_path_unavailable={}, shape_edit=edit['audit'],
        scope='굴곡 검사 후보 · 적용 불가 · 반경 보존과 해부학적 수용 미확인', smoothness='UNKNOWN')
    summary['access_graph']['revision'] = revision
    summary['access_union'].update(lineage_faces='NOT RUN', centerline_status='PASS',
        checked_paths=len(paths['rows']), context_status=context['status'],
        context_neighbors=context['neighbor_count'], context_completed=len(rows), contacts=contacts, unknown=unknown)
    return base
