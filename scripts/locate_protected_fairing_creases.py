"""Localize angle regressions to exact source faces and fixed/free vertices."""
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh


def main():
    root=Path('docs/evidence')
    edit=json.loads((root/'protected-neck-fairing.json').read_text())
    union=json.loads((root/'femoral-anterior-union.json').read_text())
    source=Path('exports/femoral-anterior-union/candidate.npz'); target=Path(edit['artifact'])
    if (hashlib.sha256(source.read_bytes()).hexdigest()!=edit['source_surface_sha256']
            or union['output_sha256']!=edit['source_surface_sha256']
            or hashlib.sha256(target.read_bytes()).hexdigest()!=edit['artifact_sha256']):
        raise ValueError('Source/candidate identity mismatch')
    with np.load(source,allow_pickle=False) as data:
        before=trimesh.Trimesh(data['vertices'],data['faces'],process=False)
    with np.load(target,allow_pickle=False) as data:
        after=trimesh.Trimesh(data['vertices'],data['faces'],process=False)
        free=data['free_vertex_ids'].copy()
    if not np.array_equal(before.faces,after.faces):
        raise ValueError('Face topology mismatch')
    adjacency=before.face_adjacency
    changed=np.isin(before.faces,free).any(axis=1)
    local=np.flatnonzero(changed[adjacency].any(axis=1))
    original=np.degrees(before.face_adjacency_angles)
    edited=np.degrees(after.face_adjacency_angles)
    increased=edited-original
    chosen=[('maximum_after',int(local[np.argmax(edited[local])])),
            ('maximum_increase',int(local[np.argmax(increased[local])]))]
    rows=[]
    lineage=union['face_lineage']
    for kind,index in chosen:
        faces=adjacency[index];edge=before.face_adjacency_edges[index]
        rows.append(dict(kind=kind,source_face_pair=faces.tolist(),source_edge_vertex_ids=edge.tolist(),
            source_owners=[lineage['source_names'][lineage['face_source_indices'][f]] for f in faces],
            before_angle_deg=float(original[index]),after_angle_deg=float(edited[index]),
            increase_deg=float(increased[index]),edge_vertices_free=np.isin(edge,free).tolist(),
            before_triangle_areas_mm2=before.area_faces[faces].tolist(),
            before_edge_positions_mm=before.vertices[edge].tolist(),
            after_edge_positions_mm=after.vertices[edge].tolist()))
    report=dict(status='MEASURED',source_surface_sha256=edit['source_surface_sha256'],
        candidate_sha256=edit['artifact_sha256'],measured_pairs=len(local),rows=rows,
        smoothness_acceptance='UNKNOWN',candidate_applied=False,
        scope='Extrema of changed-region adjacent-face angles; not clinical curvature criteria')
    (root/'protected-neck-fairing-creases.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))


if __name__=='__main__':
    main()
