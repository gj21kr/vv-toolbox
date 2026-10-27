"""Try fixed near-planar flips on estimated neck faces; preserve source patch."""
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh

from vv_toolbox.planar_patch_flips import improve_planar_patch


def main():
    root=Path('docs/evidence')
    record=json.loads((root/'femoral-anterior-union.json').read_text())
    path=Path('exports/femoral-anterior-union/candidate.npz')
    if hashlib.sha256(path.read_bytes()).hexdigest()!=record['output_sha256']:
        raise ValueError('Source identity mismatch')
    with np.load(path,allow_pickle=False) as data:
        vertices,faces=data['vertices'].copy(),data['faces'].copy()
    lineage=record['face_lineage'];owner=lineage['source_names'].index('estimated_right_carotid_neck')
    selected=np.flatnonzero(np.asarray(lineage['face_source_indices'])==owner)
    changed,report=improve_planar_patch(vertices,faces,selected,plane_tolerance_mm=1e-8,sweeps=3)
    mesh=trimesh.Trimesh(vertices,changed,process=False)
    target=Path('exports/brachiocephalic-source-patch/neck-planar-flips.npz')
    np.savez_compressed(target,vertices=vertices,faces=changed)
    report.update(source_surface_sha256=record['output_sha256'],artifact=str(target),
        artifact_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
        closed_positive_volume=bool(mesh.is_volume),source_modified=False,live_scene_changed=False,
        source_face_lineage='Changed faces are derived from recorded face pairs; old one-face ownership cannot be copied')
    (root/'neck-planar-flips.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('flips','minimum_quality_before','minimum_quality_after','closed_positive_volume','unselected_faces_unchanged')}))


if __name__=='__main__':
    main()
