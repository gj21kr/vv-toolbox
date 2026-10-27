"""Fixed real-access bend/twist experiment, separate from the live viewer."""
import argparse
import json
from pathlib import Path
import time

import numpy as np
import trimesh

from vv_toolbox.resampled_access_preview import load_resampled_access_preview
from vv_toolbox.union_shape import deform_selected_shape


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--component', choices=('combined', 'bend', 'twist'), default='combined')
    args = parser.parse_args()
    started = time.perf_counter()
    suffix = '' if args.component == 'combined' else '-'+args.component
    evidence = Path(f'docs/evidence/access-shape-edit{suffix}.json')
    params = dict(bend_mm=.25, bend_direction=[1., 0., 0.], twist_deg=5.,
                  collar_mm=1., transition_mm=10., max_displacement_mm=1.)
    if args.component == 'bend':
        params['twist_deg'] = 0.
    elif args.component == 'twist':
        params['bend_mm'] = 0.
    report = dict(status='RUNNING', source='FJ2074', parameters=params,
                  scope='Selected source shape kernel; not complete graph deformation or live editing',
                  neighboring_vessels='NOT RUN', accepted_for_generation=False)
    evidence.write_text(json.dumps(report, indent=2)+'\n')
    try:
        candidate = load_resampled_access_preview(Path('.'))
        path = candidate['source_centerlines']['FJ2074']['points_mm']
        report['parent_surface_sha256'] = candidate['summary']['surface_sha256']
        mesh = trimesh.Trimesh(candidate['vertices_mm'], candidate['faces'], process=False)
        changed, points, audit = deform_selected_shape(mesh, candidate['face_lineage'], 'FJ2074', path, **params)
        output = Path(f'exports/access-shape-edit{suffix}/candidate.npz')
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open('xb') as stream:
            np.savez_compressed(stream, vertices=changed.vertices, faces=changed.faces, centerline_mm=points)
        report.update(status='CANDIDATE', audit=audit, artifact=str(output))
    except ValueError as error:
        report.update(status='FAIL', reason=str(error))
        if hasattr(error, 'measurements'):
            report['measurements'] = error.measurements
    finally:
        report['elapsed_seconds'] = time.perf_counter()-started
        evidence.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
