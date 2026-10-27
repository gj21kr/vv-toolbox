"""Relax only an edge-connected neighborhood of the outer transition joins."""
import hashlib
import heapq
import io
import json
from pathlib import Path

import numpy as np
import trimesh

from vv_toolbox.constrained_fairing import fair_surface

ROOT = Path(__file__).resolve().parents[1]


def main():
    path = ROOT/'exports/mca-tangent-transition-constant/surface.npz'
    raw = path.read_bytes()
    source = json.loads((ROOT/'docs/evidence/mca-tangent-transition-constant.json').read_text())
    if hashlib.sha256(raw).hexdigest() != source['artifact_sha256']:
        raise ValueError('candidate hash mismatch')
    with np.load(io.BytesIO(raw), allow_pickle=False) as data:
        v, f = data['vertices_mm'], data['faces']
        meta = json.loads(str(data['metadata'].item()))
    band = json.loads((ROOT/'docs/evidence/mca-transition-annulus.json').read_text())
    if band['case_revision'] != meta['case_revision']:
        raise ValueError('case mismatch')
    mesh = trimesh.Trimesh(vertices=v, faces=f, process=False)
    outer = np.concatenate([row['outer_boundary_vertex_indices'] for row in band['sides']])
    adjacency = [[] for _ in v]
    for a, b in mesh.edges_unique:
        length = float(np.linalg.norm(v[a]-v[b]))
        adjacency[a].append((int(b), length))
        adjacency[b].append((int(a), length))
    distance = np.full(len(v), np.inf)
    queue = []
    for i in outer:
        distance[i] = 0
        heapq.heappush(queue, (0., int(i)))
    extent = .6
    while queue:
        d, i = heapq.heappop(queue)
        if d != distance[i] or d > extent:
            continue
        for j, length in adjacency[i]:
            candidate = d+length
            if candidate <= extent and candidate < distance[j]:
                distance[j] = candidate
                heapq.heappush(queue, (candidate, j))
    # Protect the neck and first five complete rings on both sides. Their
    # indexed layout is explicitly bound to this generator's eight intervals.
    neck_ids = np.asarray(meta['design_vertex_ids'])
    n = len(neck_ids)
    first_ring = int(neck_ids.max())+1
    if meta['sampling_intervals'] != 8 or len(v) != first_ring+14*n:
        raise ValueError('unexpected transition ring layout')
    protected = np.r_[neck_ids, np.arange(first_ring, first_ring+5*n),
                      np.arange(first_ring+7*n, first_ring+12*n)]
    free = np.setdiff1d(np.flatnonzero(distance <= extent), protected)
    # Original vertices removed from the source patch remain preserved in the
    # artifact. Compact only for the solver, then restore the original IDs.
    used = np.unique(f)
    inverse = np.full(len(v), -1, dtype=int)
    inverse[used] = np.arange(len(used))
    free = np.intersect1d(free, used)
    report = dict(source_sha256=source['artifact_sha256'], case_revision=meta['case_revision'],
                  config=dict(edge_path_extent_mm=extent, strength=10.,
                              max_displacement_mm=.3, max_volume_change_fraction=.02),
                  protected_vertex_count=len(protected), free_vertex_count=len(free),
                  app_applied=False)
    try:
        compact, metrics = fair_surface(v[used], inverse[f], inverse[free], strength=10.,
                                        max_displacement_mm=.3, max_volume_change_fraction=.02)
        moved = v.copy()
        moved[used] = compact
        if not np.array_equal(moved[protected], v[protected]):
            raise ValueError('protected transition changed')
        result = trimesh.Trimesh(vertices=moved, faces=f, process=False)
        changed_face = np.isin(f, free).any(axis=1)
        impacted = changed_face[result.face_adjacency].any(axis=1)
        patch = np.asarray(meta['face_origin_labels']) == 4
        all_transition = patch[result.face_adjacency].any(axis=1) | impacted
        measures = {}
        for name, selected in [('all_transition_and_changed', all_transition),
                               ('changed_neighborhood', impacted)]:
            angles = np.degrees(result.face_adjacency_angles[selected])
            measures[name] = dict(edge_count=len(angles), maximum_deg=float(angles.max()),
                                  p95_deg=float(np.percentile(angles, 95)),
                                  above_90_deg=int(np.count_nonzero(angles > 90)))
        out = ROOT/'exports/mca-outer-fairing'
        out.mkdir(exist_ok=True)
        candidate_meta = dict(meta, outer_fairing=metrics, status='CANDIDATE',
                              self_intersection='NOT RUN', context_collision='NOT RUN')
        np.savez_compressed(out/'surface.npz', vertices_mm=moved, faces=f,
                            metadata=np.array(json.dumps(candidate_meta)))
        report.update(status='CANDIDATE', metrics=metrics, angles=measures,
                      protected_vertices_exact=True,
                      crease_screen='FAIL' if measures['all_transition_and_changed']['above_90_deg'] else 'PASS',
                      smooth_junction='UNKNOWN', self_intersection='NOT RUN',
                      context_collision='NOT RUN',
                      artifact_sha256=hashlib.sha256((out/'surface.npz').read_bytes()).hexdigest())
    except ValueError as error:
        report.update(status='REJECTED', reason=str(error))
    report['input_unchanged'] = raw == path.read_bytes()
    (ROOT/'docs/evidence/mca-outer-fairing.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
