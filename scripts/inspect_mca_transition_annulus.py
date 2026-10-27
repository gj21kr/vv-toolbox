"""Inspect connected surface-distance bands before tangent patch replacement."""
import hashlib
import heapq
import io
import json
from pathlib import Path

import numpy as np
import trimesh

from vv_toolbox.patch_boundary import patch_boundary_loops

ROOT = Path(__file__).resolve().parents[1]


def main():
    evidence = json.loads((ROOT/'docs/evidence/mca-surface-origin.json').read_text())
    path = ROOT/'exports/mca-surface-origin/surface.npz'
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != evidence['artifact_sha256']:
        raise ValueError('source hash mismatch')
    with np.load(io.BytesIO(raw), allow_pickle=False) as data:
        vertices, faces = data['vertices_mm'], data['faces']
        metadata = json.loads(str(data['metadata'].item()))
    if metadata['case_revision'] != evidence['case_revision']:
        raise ValueError('case revision mismatch')
    labels = np.asarray(metadata['surface_origin']['face_labels'])
    mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
    centers = vertices[faces].mean(axis=1)
    adjacency = [[] for _ in faces]
    for a, b in mesh.face_adjacency:
        weight = float(np.linalg.norm(centers[a]-centers[b]))
        adjacency[a].append((int(b), weight))
        adjacency[b].append((int(a), weight))
    rows = []
    # Fixed before measurement: dual-graph distance from faces touching the
    # mixed-source band. This is a discrete path distance, not exact geodesic.
    band_width_mm = 1.0
    for label, name in [(0, 'parent'), (1, 'sac')]:
        seeds = [i for i in np.flatnonzero(labels == label)
                 if any(labels[j] == 2 for j, _ in adjacency[i])]
        distances = np.full(len(faces), np.inf)
        queue = []
        for i in seeds:
            distances[i] = 0.
            heapq.heappush(queue, (0., int(i)))
        while queue:
            distance, i = heapq.heappop(queue)
            if distance != distances[i]:
                continue
            for j, weight in adjacency[i]:
                candidate = distance+weight
                if labels[j] == label and candidate < distances[j]:
                    distances[j] = candidate
                    heapq.heappush(queue, (candidate, j))
        selected = np.flatnonzero((labels == label) & (distances <= band_width_mm))
        retained = np.flatnonzero((labels == label) & (distances > band_width_mm))
        row = dict(side=name, seed_face_count=len(seeds),
                   removed_face_indices=selected.tolist(),
                   removed_face_count=len(selected), retained_face_count=len(retained),
                   status='UNKNOWN', outer_boundary_vertex_indices=[])
        try:
            band_loops = patch_boundary_loops(faces, selected)
            retained_loops = patch_boundary_loops(faces, retained)
            patch_faces = faces[selected]
            patch_edges = np.unique(np.sort(np.concatenate(
                [patch_faces[:, [0, 1]], patch_faces[:, [1, 2]],
                 patch_faces[:, [2, 0]]]), axis=1), axis=0)
            euler = len(np.unique(patch_faces))-len(patch_edges)+len(patch_faces)
            unseen = set(selected.tolist())
            components = 0
            while unseen:
                components += 1
                stack = [unseen.pop()]
                while stack:
                    for j, _ in adjacency[stack.pop()]:
                        if j in unseen:
                            unseen.remove(j)
                            stack.append(j)
            old_loops = patch_boundary_loops(faces, np.flatnonzero(labels == label))
            old_edges = {tuple(sorted((a, b))) for loop in old_loops
                         for a, b in zip(loop, loop[1:]+loop[:1])}
            band_edges = {tuple(sorted((a, b))) for loop in band_loops
                          for a, b in zip(loop, loop[1:]+loop[:1])}
            row.update(band_loop_count=len(band_loops),
                       retained_loop_count=len(retained_loops),
                       band_euler_characteristic=euler,
                       band_face_components=components,
                       original_boundary_preserved=old_edges <= band_edges)
            if (len(band_loops) == 2 and len(retained_loops) == 1
                    and old_edges <= band_edges and euler == 0 and components == 1):
                row['status'] = 'BOUNDARIES_PASS'
                row['outer_boundary_vertex_indices'] = retained_loops[0]
            else:
                row['reason'] = 'expected annular band and one retained boundary'
        except ValueError as error:
            row['reason'] = str(error)
        rows.append(row)
    result = dict(case_revision=evidence['case_revision'],
                  artifact_sha256=evidence['artifact_sha256'],
                  band_width_mm=band_width_mm, sides=rows,
                  input_unchanged=raw == path.read_bytes(), app_applied=False,
                  limitation='Centroid dual-graph distance, not exact geodesic. Combinatorial checks do not certify tangent compatibility or geometric nonintersection.')
    (ROOT/'docs/evidence/mca-transition-annulus.json').write_text(
        json.dumps(result, indent=2)+'\n')
    print(json.dumps([{k: v for k, v in row.items()
                       if not k.endswith('_indices')} for row in rows]))


if __name__ == '__main__':
    main()
