"""Inspect bounded retained-surface fairing while freezing the junction collar."""
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh
from vv_toolbox.constrained_fairing import fair_surface

ROOT = Path(__file__).resolve().parents[1]


def main():
    name = 'mca-tangent-transition-constant-earcut-flips-uniform'
    path = ROOT/'exports'/name/'surface.npz'
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    evidence = json.loads((ROOT/'docs/evidence'/f'{name}.json').read_text())
    if digest != evidence['artifact_sha256']:
        raise ValueError('source fingerprint mismatch')
    with np.load(path, allow_pickle=False) as data:
        vertices = data['vertices_mm'].copy()
        faces = data['faces'].copy()
        metadata = json.loads(str(data['metadata'].item()))
    labels = np.asarray(metadata['face_origin_labels'])
    if labels.shape != (len(faces),):
        raise ValueError('face provenance mismatch')
    used, inverse = np.unique(faces, return_inverse=True)
    compact_faces = inverse.reshape(faces.shape)
    compact = vertices[used]
    # All generated faces plus one complete adjacent face collar stay exact.
    patch_vertices = np.unique(faces[labels == 4])
    collar_faces = np.any(np.isin(faces, patch_vertices), axis=1)
    frozen = np.unique(faces[collar_faces])
    free = np.flatnonzero(~np.isin(used, frozen))
    if not len(patch_vertices):
        raise ValueError('missing generated junction')
    moved, report = fair_surface(compact, compact_faces, free, strength=10.,
        max_displacement_mm=.15, max_volume_change_fraction=.02)
    result = vertices.copy()
    result[used] = moved
    if not np.array_equal(result[frozen], vertices[frozen]):
        raise ValueError('junction collar changed')
    design = np.asarray(metadata['design_vertex_ids'])
    if not np.array_equal(result[design], vertices[design]):
        raise ValueError('neck design changed')

    def angles(points):
        mesh = trimesh.Trimesh(vertices=points, faces=faces, process=False)
        values = np.degrees(mesh.face_adjacency_angles)
        pairs = mesh.face_adjacency
        retained = np.all(labels[pairs] != 4, axis=1)
        return {key: dict(p95_deg=float(np.percentile(values[mask], 95)),
                          max_deg=float(values[mask].max()),
                          above_90=int(np.count_nonzero(values[mask] > 90)))
                for key, mask in [('retained', retained), ('junction', ~retained)]}

    report.update(source_artifact_sha256=digest,
        case_revision=metadata['case_revision'], frame=metadata['frame'],
        frozen_vertices=len(frozen), unused_vertices=len(vertices)-len(used),
        junction_collar_exact=True, design_curve_exact=True,
        before=angles(vertices), after=angles(result),
        smoothness='UNKNOWN', context_collision='NOT RUN',
        app_applied=False)
    out = ROOT/'exports/mca-retained-fairing'
    out.mkdir(exist_ok=True)
    output_metadata = dict(metadata, retained_fairing=report)
    np.savez_compressed(out/'surface.npz', vertices_mm=result, faces=faces,
                        metadata=np.array(json.dumps(output_metadata)))
    report['artifact_sha256'] = hashlib.sha256((out/'surface.npz').read_bytes()).hexdigest()
    report['input_unchanged'] = path.read_bytes() == raw
    if not report['input_unchanged']:
        raise ValueError('source modified')
    (ROOT/'docs/evidence/mca-retained-fairing.json').write_text(
        json.dumps(report, indent=2)+'\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
