"""Compare fixed-design candidates without equating angle screening to convergence."""
import hashlib
import argparse
import io
import json
from pathlib import Path
import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parents[1]


def distances(points, target):
    values = []
    for start in range(0, len(points), 16):
        _, distance, _ = trimesh.proximity.closest_point_naive(target, points[start:start+16])
        values.extend(distance.tolist())
    return np.asarray(values)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--axis', choices=['circumferential', 'radial'], default='circumferential')
    axis = parser.parse_args().axis
    meshes, rows, inputs = {}, [], []
    base = 'mca-tangent-transition-constant-earcut-flips-uniform'
    revisions = set()
    counts = (32, 64, 128) if axis == 'circumferential' else (8, 16, 32)
    for count in counts:
        name = (base if count == 64 else f'{base}-{count}') if axis == 'circumferential' else (
            base if count == 8 else f'{base}-radial{count}')
        evidence = json.loads((ROOT/'docs/evidence'/f'{name}.json').read_text())
        path = ROOT/'exports'/name/'surface.npz'
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != evidence['artifact_sha256']:
            raise ValueError('candidate hash mismatch')
        with np.load(io.BytesIO(raw), allow_pickle=False) as data:
            v, f = data['vertices_mm'], data['faces']
            meta = json.loads(str(data['metadata'].item()))
        revisions.add(meta['case_revision'])
        field = 'interior_ring_samples' if axis == 'circumferential' else 'sampling_intervals'
        fixed_field, fixed_value = ('sampling_intervals', 8) if axis == 'circumferential' else ('interior_ring_samples', 64)
        if meta[field] != count or meta[fixed_field] != fixed_value:
            raise ValueError('resolution mismatch')
        full = trimesh.Trimesh(vertices=v, faces=f, process=False)
        patch = np.asarray(meta['face_origin_labels']) == 4
        mesh = trimesh.Trimesh(vertices=v, faces=f[patch], process=False)
        mesh.remove_unreferenced_vertices()
        meshes[count] = mesh
        adjacent_patch = patch[full.face_adjacency].all(axis=1)
        edge = full.face_adjacency_edges[adjacent_patch]
        lengths = np.linalg.norm(v[edge[:, 1]]-v[edge[:, 0]], axis=1)
        bending = np.sum(lengths*full.face_adjacency_angles[adjacent_patch])
        rows.append(dict(samples=count, artifact_sha256=evidence['artifact_sha256'],
                         total_volume_mm3=float(full.volume), transition_area_mm2=float(mesh.area),
                         absolute_angle_length_per_area_per_mm=float(bending/mesh.area),
                         crease_screen=evidence['crease_screen'], angles=evidence['angles']))
        inputs.append((path, raw))
    if len(revisions) != 1:
        raise ValueError('case mismatch')
    comparisons = []
    for a, b in zip(counts[:-1], counts[1:]):
        measures = []
        for first, second in ((a, b), (b, a)):
            m = meshes[first]
            points = np.vstack([m.vertices, m.triangles_center])
            d = distances(points, meshes[second])
            measures.append(dict(from_samples=first, to_samples=second,
                                 sample_count=len(points), maximum_mm=float(d.max()),
                                 p95_mm=float(np.percentile(d, 95)), mean_mm=float(d.mean())))
        comparisons.append(dict(resolutions=[a, b], directed_distances=measures,
                                symmetric_sampled_maximum_mm=max(x['maximum_mm'] for x in measures)))
    result = dict(case_revision=next(iter(revisions)), varied_axis=axis, candidates=rows, comparisons=comparisons,
                  status='MEASURED', smoothness_convergence='UNKNOWN',
                  limitations=[f'Only {axis} sampling varies; the other sampling axis stays fixed.',
                               'Vertex and centroid distances are not continuous Hausdorff bounds.',
                               'Angle-length density depends on topology and excludes outer joins.',
                               'No acceptance threshold fitted to these results.'],
                  inputs_unchanged=all(path.read_bytes() == raw for path, raw in inputs),
                  app_applied=False)
    filename = 'mca-transition-resolution.json' if axis == 'circumferential' else 'mca-transition-radial-resolution.json'
    (ROOT/'docs/evidence'/filename).write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(dict(candidates=[{k: v for k, v in row.items() if k != 'angles'} for row in rows],
                         comparisons=comparisons)))


if __name__ == '__main__':
    main()
