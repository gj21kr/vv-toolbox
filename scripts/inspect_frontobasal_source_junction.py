"""Inspect fixed 3 mm branch ports against the original FJ1690 surface."""
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh

from vv_toolbox.atlas import load_atlas
from vv_toolbox.case_io import load_case
from vv_toolbox.junction_source_patch import clip_source_junction
from vv_toolbox.mesh_self_contact import inspect_self_contact
from vv_toolbox.surface_indexing import exact_vertex_index_copy


def main():
    root = Path(__file__).resolve().parents[1]
    evidence = root/'docs/evidence'
    transition = json.loads((evidence/'frontobasal-junction-transition.json').read_text())
    parent = json.loads((evidence/'frontobasal-centering.json').read_text())
    case, revision = load_case(root/'exports/atlas-case-inspection/all-arterial.snapshot.json')
    if revision != transition['source_case_revision'] or parent['sha256'] != transition['path_sha256']:
        raise ValueError('Graph or corrected path identity mismatch')
    if hashlib.sha256((root/parent['artifact']).read_bytes()).hexdigest() != parent['sha256']:
        raise ValueError('Path changed')
    with np.load(root/parent['artifact'], allow_pickle=False) as data:
        corrected = data['candidate_points_mm']
    atlas = load_atlas()
    if atlas.metadata['sha256'] != parent['atlas_archive_sha256']:
        raise ValueError('Atlas changed')
    part = next(p for p in atlas.meshes if p['id'] == 'FJ1690')
    source, _ = exact_vertex_index_copy(trimesh.Trimesh(part['vertices'], part['faces'], process=False))
    edges = {e['id']: e for e in case['edges']}
    node = 'FJ1690:n3'
    ports = []
    junction = corrected[-1]
    for entry in transition['endpoints'][1]['incident_edges']:
        edge = edges[entry['edge_id']]
        points = corrected if edge['id'] == 'FJ1690:e0' else np.asarray(edge['centerline_mm'], float)
        if edge['end'] == node:
            points = points[::-1]
        elif edge['start'] != node:
            raise ValueError('Incident edge mismatch')
        if not np.allclose(points[0], junction, rtol=0, atol=1e-8):
            raise ValueError('Incident endpoints do not coincide')
        arc = np.r_[0, np.cumsum(np.linalg.norm(np.diff(points, axis=0), axis=1))]
        if arc[-1] <= 3.25:
            raise ValueError('Branch too short for fixed 3 mm port and tangent window')
        sample = lambda s: np.array([np.interp(s, arc, points[:,k]) for k in range(3)])
        normal = sample(3.25)-sample(2.75)
        normal /= np.linalg.norm(normal)
        ports.append(dict(edge_id=edge['id'], distance_from_junction_mm=3.0,
            tangent_window_mm=.5, origin_mm=sample(3).tolist(), outward_normal=normal.tolist()))
    result = dict(schema='vv-toolbox.frontobasal-source-junction/1', source_case_revision=revision,
        atlas_archive_sha256=atlas.metadata['sha256'], path_sha256=parent['sha256'],
        junction_id=node, junction_mm=junction.tolist(), ports=ports,
        port_rule='Fixed 3 mm arc distance with 0.5 mm chord tangent; engineering probe, not an anatomical boundary.',
        accepted_for_generation=False, arm_attachment='NOT RUN', surrounding_clearance='NOT RUN')
    try:
        patch, lineage, meta = clip_source_junction(source,
            [p['origin_mm'] for p in ports], [p['outward_normal'] for p in ports], junction)
        contact = inspect_self_contact(patch.vertices, patch.faces)
        result.update(status='CANDIDATE', patch=meta, self_contact=contact,
            vertices=len(patch.vertices), faces=len(patch.faces))
        output = root/'exports/frontobasal-source-junction.npz'
        with output.open('xb') as stream:
            np.savez_compressed(stream, vertices_mm=patch.vertices, faces=patch.faces,
                source_face_ids=lineage, metadata=np.array(json.dumps(meta)))
        result.update(artifact=str(output.relative_to(root)), sha256=hashlib.sha256(output.read_bytes()).hexdigest())
    except ValueError as error:
        result.update(status='FAIL', reason=str(error))
    (evidence/'frontobasal-source-junction.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps({k:result[k] for k in ('status','reason','vertices','faces') if k in result}), flush=True)


if __name__ == '__main__':
    main()
