"""Compare fixed winding batches on a declared subset of the full access mesh."""
import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np

from vv_toolbox.case_io import load_case
from vv_toolbox.case_surface import build_case_surface
from vv_toolbox.voxel_output import _inside


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stride', type=int, choices=(1, 4), default=4)
    args = parser.parse_args()
    root = Path('docs/evidence')
    source = json.loads((root/'access-candidate-case.json').read_text())
    roi = json.loads((root/'access-roi-mask.json').read_text())
    case, revision = load_case(source['case_file'])
    if revision != source['case_revision'] or revision != roi['case_revision']:
        raise ValueError('Case revision mismatch')
    vertices, faces, _ = build_case_surface(case, [e['id'] for e in case['edges']], spacing_mm=.5)
    triangles = vertices[faces]
    # Fixed voxel centers of the completed ROI, retaining the complete surface.
    z, y, x = np.meshgrid(*([np.arange(0, 33, args.stride)]*3), indexing='ij')
    points = np.column_stack((x.ravel(), y.ravel(), z.ravel()))*.5 + np.asarray(roi['grid']['origin_xyz_mm'])
    results, elapsed = {}, {}
    for batch in (32, 128):
        started = time.perf_counter()
        results[batch] = np.concatenate([
            _inside(points[i:i+128], triangles, 1e-8, triangle_chunk=batch)
            for i in range(0, len(points), 128)])
        elapsed[str(batch)] = time.perf_counter()-started
    artifact = Path(roi['artifact'])
    if hashlib.sha256(artifact.read_bytes()).hexdigest() != roi['artifact_sha256']:
        raise ValueError('ROI archive hash mismatch')
    with np.load(artifact, allow_pickle=False) as saved:
        expected = saved['foreground'][::args.stride, ::args.stride, ::args.stride].ravel()
    differences = {str(k): int(np.count_nonzero(v != expected)) for k, v in results.items()}
    report = dict(status='PASS' if not any(differences.values()) else 'FAIL',
                  scope=f'{len(points)} fixed ROI voxel centers; full surface; not whole-model timing',
                  case_revision=revision, mesh_faces=len(faces), sampled_voxels=len(points),
                  tolerance_mm=1e-8, timings_seconds=elapsed,
                  reference_seconds_over_batched=elapsed['32']/elapsed['128'],
                  disagreements_with_completed_roi=differences,
                  roi_artifact_sha256=roi['artifact_sha256'],
                  points_sha256=hashlib.sha256(points.tobytes()).hexdigest(),
                  implementation_sha256=hashlib.sha256(Path('src/vv_toolbox/voxel_output.py').read_bytes()).hexdigest(),
                  timing_limitations='Single paired run; concurrent app and atlas mask workloads; no general speedup claim')
    filename = 'winding-batching-full-roi.json' if args.stride == 1 else 'winding-batching-benchmark.json'
    (root/filename).write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
