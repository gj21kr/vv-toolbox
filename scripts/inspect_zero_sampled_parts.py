"""Compare zero-sampled source parts on nested, globally aligned lattices."""
import json
from pathlib import Path
import time

import numpy as np

from vv_toolbox.case_io import load_case
from vv_toolbox.voxel_output import Grid, Surface
from vv_toolbox.voxel_tiles import iter_mask_tiles


def main():
    root = Path(__file__).resolve().parents[1]
    prior = json.loads((root/'docs/evidence/atlas-mask-reload.json').read_text())
    manifest = json.loads((root/'exports/atlas-source-masks-1mm/manifest.json').read_text())
    case, revision = load_case(root/'exports/atlas-case-capture-ui/case.snapshot.json')
    if revision != prior['case_revision'] or revision != manifest['context']['case_revision']:
        raise ValueError('Source revision mismatch')
    anchor = np.asarray(manifest['origin_xyz_mm'])
    parts = {p['part_id']: p for p in case['surface_parts']}
    rows = []
    for ident in prior['zero_sampled_voxel_parts']:
        p = parts[ident]
        if p['geometry_sha256'] != manifest['context']['part_instances'][ident]['geometry_sha256']:
            raise ValueError('Geometry identity mismatch')
        v = np.asarray(p['vertices_mm'], float)
        surface = Surface(1, 0, p['provenance'], v, np.asarray(p['faces'], np.int64),
                          case['frame']['id'], f'case:{revision};part:{ident}')
        row = dict(part_id=ident, geometry_sha256=p['geometry_sha256'],
                   bounds_mm=[v.min(0).tolist(), v.max(0).tolist()], samples=[])
        for spacing in (1.0, 0.5, 0.25):
            start = np.floor((v.min(0)-anchor)/spacing).astype(int)-1
            stop = np.ceil((v.max(0)-anchor)/spacing).astype(int)+1
            grid = Grid(tuple(int(x) for x in (stop-start+1)[::-1]),
                        (spacing,)*3, tuple(anchor+start*spacing), case['frame']['id'])
            began = time.perf_counter()
            count = sum(int(volume.foreground.sum()) for _, volume in
                        iter_mask_tiles([surface], grid, normalize_exact_indices=True))
            if spacing == 1 and count != prior['per_part_voxels'][ident]:
                raise ValueError('Local sampling differs from saved full-volume membership')
            row['samples'].append(dict(spacing_mm=spacing, origin_xyz_mm=list(grid.origin_xyz_mm),
                shape_zyx=list(grid.shape_zyx), foreground_voxels=count,
                sampled_volume_mm3=count*spacing**3, elapsed_seconds=time.perf_counter()-began))
            print(ident, spacing, count, flush=True)
        row['interpretation'] = ('coarse_lattice_missed_source' if row['samples'][-1]['foreground_voxels']
                                 else 'unresolved_at_tested_spacings')
        rows.append(row)
    report = dict(schema='vv-toolbox.zero-sample-resolution/1', status='PASS',
        case_revision=revision, lattice_anchor_xyz_mm=anchor.tolist(), parts=rows,
        scope='All zero-sampled parts from the saved 1 mm source mask; identical source geometry and nested lattice',
        anatomy='NOT RUN', geometric_accuracy='NOT RUN',
        limitation='Positive fine-grid membership does not prove converged volume or complete thin-vessel representation.')
    (root/'docs/evidence/zero-sample-resolution.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')


if __name__ == '__main__':
    main()
