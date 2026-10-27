"""Fixed high-resolution ROI of the exact registered access candidate."""
import hashlib
import json
from pathlib import Path
import time

import numpy as np
import trimesh

from vv_toolbox.case_io import load_case
from vv_toolbox.case_surface import build_case_surface
from vv_toolbox.case_masks import build_case_masks
from vv_toolbox.volume_cli import save_volume


def main():
    started = time.perf_counter()
    root = Path('docs/evidence')
    source = json.loads((root/'access-candidate-case.json').read_text())
    case, revision = load_case(source['case_file'])
    if revision != source['case_revision']:
        raise ValueError('Registered case changed')
    paths = [e for e in case['edges'] if e.get('source_part_id') == 'FJ2074']
    if len(paths) != 1:
        raise ValueError('Explicit unique femoral source path required')
    path = np.asarray(paths[0]['centerline_mm'])
    arc = np.r_[0., np.cumsum(np.linalg.norm(np.diff(path, axis=0), axis=1))]
    center = np.array([np.interp(arc[-1]/2, arc, path[:, i]) for i in range(3)])
    grid = dict(shape_zyx=(33, 33, 33), spacing_xyz_mm=(.5, .5, .5),
                origin_xyz_mm=tuple(center-8.), frame_id=case['frame']['id'])
    ids = [e['id'] for e in case['edges']]
    vertices, faces, _ = build_case_surface(case, ids, spacing_mm=.5)
    report = dict(status='RUNNING', phase='voxelizing', case_revision=revision,
                  source_edge=paths[0]['id'], center_lps_mm=center.tolist(), grid=grid,
                  scope='33 cubed ROI; not whole-model masks or anatomical segment approval',
                  accepted_for_generation=False, anatomical_validation='NOT RUN', live_scene_changed=False)
    target = root/'access-roi-mask.json'
    def save():
        report['elapsed_seconds'] = time.perf_counter()-started
        temp = target.with_suffix('.json.tmp')
        temp.write_text(json.dumps(report, indent=2)+'\n')
        temp.replace(target)
    save()
    volume, lesions, lesion_meta, quality = build_case_masks(case, ids, vertices, faces,
        spacing_mm=.5, grid_config=grid, coverage='roi', max_bytes=256*1024**2)
    report.update(phase='independent-ray-check', quality=quality)
    save()
    z, y, x = np.indices(volume.foreground.shape)
    xyz = np.column_stack((x.ravel(), y.ravel(), z.ravel()))*.5 + np.asarray(grid['origin_xyz_mm'])
    mesh = trimesh.Trimesh(vertices, faces, process=False)
    ray = mesh.contains(xyz).reshape(volume.foreground.shape)
    differences = np.argwhere(ray != volume.foreground)
    report.update(foreground_voxels=int(volume.foreground.sum()), sampled_voxels=volume.foreground.size,
                  independent_ray_disagreements=len(differences),
                  disagreement_indices_zyx= differences.tolist(),
                  anatomical_labels_unknown=not bool(volume.anatomical.any()),
                  estimated_foreground=bool(np.all(volume.provenance[volume.foreground] == 2)))
    center_world = volume.grid.affine_xyz @ np.array([16,16,16,1])
    if not np.allclose(center_world[:3], center, rtol=0, atol=1e-12):
        raise ValueError('ROI affine center mismatch')
    artifact = Path('exports/access-candidate-roi/femoral-05mm.npz')
    if artifact.exists():
        raise ValueError('ROI artifact exists; refusing overwrite')
    save_volume(artifact, volume, lesion_labels=lesions, lesion_metadata=lesion_meta)
    with np.load(artifact, allow_pickle=False) as saved:
        for key in ('foreground','anatomical','instance','provenance','overlap_count','membership'):
            if not np.array_equal(saved[key], getattr(volume,key)):
                raise ValueError('ROI archive roundtrip mismatch')
        if json.loads(str(saved['metadata'])) != volume.metadata():
            raise ValueError('ROI metadata changed')
    report.update(status='PASS' if not len(differences) and 0<report['foreground_voxels']<volume.foreground.size else 'FAIL',
                  phase='complete', artifact=str(artifact), artifact_sha256=hashlib.sha256(artifact.read_bytes()).hexdigest(),
                  archive_roundtrip='PASS', affine_center_check='PASS')
    save()
    print(json.dumps({k:report[k] for k in ('status','foreground_voxels','independent_ray_disagreements','elapsed_seconds')}),flush=True)


if __name__=='__main__':
    main()
