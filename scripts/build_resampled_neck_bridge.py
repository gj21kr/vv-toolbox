"""Rebuild estimated neck interior while retaining two complete endpoint rings."""
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh

from vv_toolbox.bridge_resampling import resample_bridge_interior
from vv_toolbox.mesh_self_contact import inspect_self_contact


def quality(mesh):
    triangles=mesh.triangles
    area2=np.linalg.norm(np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0]),axis=1)
    q=2*np.sqrt(3)*area2/np.sum((np.roll(triangles,-1,axis=1)-triangles)**2,axis=(1,2))
    return dict(faces=len(q),minimum=float(q.min()),p01=float(np.percentile(q,1)),
                below_001_count=int((q<.01).sum()),threshold_role='descriptive, not acceptance')


def main():
    root=Path('docs/evidence');pid='estimated_right_carotid_neck'
    original_report=json.loads((root/'neck-contour-candidates-corners.json').read_text())
    row=next(r for r in original_report['candidates'] if r['part_id']==pid)
    source=Path('exports/neck-contour-candidates-corners')/(pid+'.npz')
    with np.load(source,allow_pickle=False) as data:
        before=trimesh.Trimesh(data['vertices'],data['faces'],process=False)
    rings=before.vertices.reshape(row['stations'],row['perimeter_samples'],3)
    result,metadata=resample_bridge_interior(rings,samples=64,preserved_rings=2)
    target=Path('exports/brachiocephalic-source-patch/resampled-right-neck.npz')
    np.savez_compressed(target,vertices=result.vertices,faces=result.faces)
    report=dict(status='CANDIDATE',source_case_revision=original_report['case_revision'],
        source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        artifact=str(target),artifact_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
        construction=metadata,before_quality=quality(before),after_quality=quality(result),
        self_contact='RUNNING',source_modified=False,live_scene_changed=False)
    output=root/'resampled-right-neck.json'
    output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(before=report['before_quality'],after=report['after_quality'])),flush=True)
    report['self_contact']=inspect_self_contact(result.vertices,result.faces)
    output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(self_contact=report['self_contact']['status'])),flush=True)


if __name__=='__main__':
    main()
