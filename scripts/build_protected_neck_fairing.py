"""One fixed fairing configuration on neck-only interior vertices."""
import hashlib
import json
from pathlib import Path

import numpy as np

from vv_toolbox.constrained_fairing import fair_surface
from vv_toolbox.protected_patch_check import check_protected_patch


def main():
    root=Path('docs/evidence')
    record=json.loads((root/'femoral-anterior-union.json').read_text())
    protected=json.loads((root/'brachiocephalic-source-patch.json').read_text())
    source=Path('exports/femoral-anterior-union/candidate.npz')
    patch_path=Path(protected['artifact'])
    if (hashlib.sha256(source.read_bytes()).hexdigest()!=record['output_sha256']
            or protected['source_surface_sha256']!=record['output_sha256']
            or hashlib.sha256(patch_path.read_bytes()).hexdigest()!=protected['artifact_sha256']):
        raise ValueError('Source/patch identity mismatch')
    with np.load(source,allow_pickle=False) as data:
        vertices,faces=data['vertices'].copy(),data['faces'].copy()
    with np.load(patch_path,allow_pickle=False) as data:
        patch={key:data[key].copy() for key in data.files}
    lineage=record['face_lineage']
    owner=lineage['source_names'].index('estimated_right_carotid_neck')
    selected=np.asarray(lineage['face_source_indices'])==owner
    # Every shared boundary and every non-neck vertex stays fixed.
    free=np.setdiff1d(np.unique(faces[selected]),np.unique(faces[~selected]))
    options=dict(strength=.1,max_displacement_mm=.5,max_volume_change_fraction=.01)
    report=dict(status='RUNNING',source_surface_sha256=record['output_sha256'],
        protected_patch_sha256=protected['artifact_sha256'],configuration=options,
        free_vertex_count=len(free),source_modified=False,live_scene_changed=False,
        self_contact='NOT RUN',surroundings='NOT RUN',smoothness_acceptance='NOT RUN')
    try:
        moved,measurement=fair_surface(vertices,faces,free,**options)
        check=check_protected_patch(vertices,moved,faces,patch,allowed_vertex_ids=free,
                                    max_displacement_mm=options['max_displacement_mm'])
        target=Path('exports/brachiocephalic-source-patch/protected-neck-fairing.npz')
        np.savez_compressed(target,vertices=moved,faces=faces,free_vertex_ids=free)
        report.update(status='CANDIDATE',fairing=measurement,protection=check,
            artifact=str(target),artifact_sha256=hashlib.sha256(target.read_bytes()).hexdigest())
    except ValueError as error:
        report.update(status='REJECTED',reason=str(error))
    (root/'protected-neck-fairing.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
