"""Restore protected-patch roundoff in a separate union candidate and recheck it."""
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh

from vv_toolbox.patch_roundoff_restore import restore_patch_coordinates
from vv_toolbox.mesh_self_contact import inspect_self_contact


def main():
    root=Path('docs/evidence')
    union=json.loads((root/'resampled-access-union.json').read_text())
    record=json.loads((root/'brachiocephalic-source-patch.json').read_text())
    source=Path(union['artifact']);patch_path=Path(record['artifact'])
    if (hashlib.sha256(source.read_bytes()).hexdigest()!=union['output_sha256']
            or hashlib.sha256(patch_path.read_bytes()).hexdigest()!=record['artifact_sha256']):
        raise ValueError('Source/patch identity mismatch')
    with np.load(source,allow_pickle=False) as data:
        vertices,faces=data['vertices'].copy(),data['faces'].copy()
    with np.load(patch_path,allow_pickle=False) as data:
        patch={k:data[k].copy() for k in data.files}
    lineage=union['face_lineage']
    selected=np.flatnonzero(np.isin(lineage['face_source_indices'],
        [lineage['source_names'].index(n) for n in record['selected_owners']]))
    restored,check=restore_patch_coordinates(vertices,faces,selected,patch,max_roundoff_mm=1e-8)
    mesh=trimesh.Trimesh(restored,faces,process=False)
    if not mesh.is_volume or np.any(mesh.area_faces<=1e-12):raise ValueError('Restoration invalidates volume')
    target=source.with_name('protected-candidate.npz')
    np.savez_compressed(target,vertices=restored,faces=faces)
    report=dict(status='RUNNING',parent_sha256=union['output_sha256'],source_case_revision=union['source_case_revision'],
        patch_sha256=record['artifact_sha256'],artifact=str(target),output_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
        restoration=check,closed_positive_volume=True,faces_unchanged=True,
        live_scene_changed=False,source_modified=False,centerline_containment='NOT RUN',whole_context='NOT RUN')
    output=root/'resampled-access-protected.json'
    output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(check),flush=True)
    report['self_contact']=inspect_self_contact(mesh.vertices,mesh.faces)
    report['status']='CANDIDATE' if report['self_contact']['status']=='NO_CONTACT_DETECTED' else 'UNKNOWN'
    output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(status=report['status'],self_contact=report['self_contact']['status'])),flush=True)


if __name__=='__main__':
    main()
