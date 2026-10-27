"""Render saved ROI voxels in physical coordinates without interpolation."""
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
import numpy as np


def main():
    evidence = Path('docs/evidence')
    report = json.loads((evidence/'access-roi-mask.json').read_text())
    artifact = Path(report['artifact'])
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    if report['status'] != 'PASS' or digest != report['artifact_sha256']:
        raise ValueError('Completed ROI archive hash required')
    with np.load(artifact, allow_pickle=False) as saved:
        mask = saved['foreground']
        meta = json.loads(str(saved['metadata']))
        affine = np.asarray(meta['voxel_xyz_to_world_mm'])
        spacing = np.asarray(meta['spacing_xyz_mm'])
        if meta['axes'] != 'LPS' or meta['array_order'] != 'zyx':
            raise ValueError('Explicit LPS/zyx archive required')
        expected = np.eye(4)
        expected[:3, :3] = np.diag(spacing)
        expected[:3, 3] = report['grid']['origin_xyz_mm']
        if not np.array_equal(affine, expected):
            raise ValueError('Axis-aligned ROI affine mismatch')
        checks = dict(
            anatomical_unknown=bool(np.all(saved['anatomical'][mask] == 0)),
            estimated_provenance=bool(np.all(saved['provenance'][mask] == 2)),
            single_instance=bool(np.all(saved['instance'][mask] == 1)),
            no_declared_lesion=bool(not saved['lesion_instance'].any()),
            lesion_metadata_none_declared=json.loads(str(saved['lesion_metadata']))['lesion_presence'] == 'none_declared',
            membership_matches_foreground=np.array_equal(saved['membership'][0], mask))
    if not all(checks.values()):
        raise ValueError(f'ROI labels differ from declared case: {checks}')
    center = np.asarray(mask.shape)//2
    origin = affine[:3, 3]
    size_xyz = np.asarray(mask.shape[::-1])
    bounds = [(origin[i]-spacing[i]/2, origin[i]+(size_xyz[i]-.5)*spacing[i]) for i in range(3)]
    views = [(mask[center[0]], 0, 1, 2, center[0], 'Axial'),
             (mask[:, center[1], :], 0, 2, 1, center[1], 'Coronal'),
             (mask[:, :, center[2]], 1, 2, 0, center[2], 'Sagittal')]
    labels = ['L (mm)', 'P (mm)', 'S (mm)']
    fig, axes = plt.subplots(1, 3, figsize=(12, 4.7), layout='constrained')
    for ax, (pixels, h, v, fixed, index, name) in zip(axes, views):
        ax.imshow(pixels, origin='lower', extent=(*bounds[h], *bounds[v]),
                  interpolation='nearest', cmap=ListedColormap(['#101820', '#e35565']), vmin=0, vmax=1)
        ax.set(xlabel=labels[h], ylabel=labels[v], title=f'{name}: {labels[fixed][0]} = {origin[fixed]+index*spacing[fixed]:.2f} mm')
        ax.set_aspect('equal')
    fig.suptitle('Left femoral ROI | saved mask | 0.5 mm voxels\nEstimated synthetic surface; anatomical segment labels UNKNOWN', fontsize=12)
    output = Path('exports/access-candidate-roi/orthogonal-slices.png')
    fig.savefig(output, dpi=160)
    plt.close(fig)
    result = dict(status='PASS', scope='Saved ROI labels and physical-coordinate slice rendering',
                  source_sha256=digest, checks=checks, case_revision=report['case_revision'],
                  image=str(output), image_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),
                  interpolation='nearest', axes='LPS increasing; not radiological display convention',
                  visual_review='NOT RUN', clinical_validity='NOT RUN')
    (evidence/'access-roi-mask-visual.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
