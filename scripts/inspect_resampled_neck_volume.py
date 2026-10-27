"""Sample two-way wall deviation and cap the separately resampled neck."""
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh

from vv_toolbox.estimated_tube_volume import cap_estimated_neck


def sample_distances(source,target):
    points=np.vstack([source.vertices,source.triangles_center])
    values=[]
    for start in range(0,len(points),128):
        _,distance,_=trimesh.proximity.closest_point(target,points[start:start+128])
        if not np.isfinite(distance).all():raise ValueError('Nonfinite distance')
        values.extend(distance.tolist())
    return dict(samples=len(values),maximum_mm=float(np.max(values)),mean_mm=float(np.mean(values)),
                p95_mm=float(np.percentile(values,95)),scope='vertices and triangle centroids; not continuous Hausdorff bound')


def main():
    root=Path('docs/evidence')
    record=json.loads((root/'resampled-right-neck.json').read_text())
    old=Path('exports/neck-contour-candidates-corners/estimated_right_carotid_neck.npz')
    new=Path(record['artifact'])
    if (hashlib.sha256(old.read_bytes()).hexdigest()!=record['source_sha256']
            or hashlib.sha256(new.read_bytes()).hexdigest()!=record['artifact_sha256']):
        raise ValueError('Candidate/source identity mismatch')
    with np.load(old,allow_pickle=False) as data:
        original=trimesh.Trimesh(data['vertices'],data['faces'],process=False)
    with np.load(new,allow_pickle=False) as data:
        candidate=trimesh.Trimesh(data['vertices'],data['faces'],process=False)
    report=dict(status='RUNNING',source_sha256=record['source_sha256'],
        candidate_sha256=record['artifact_sha256'],source_case_revision=record['source_case_revision'],
        source_modified=False,live_scene_changed=False,acceptance_limits='NOT SET')
    output=root/'resampled-right-neck-volume.json'

    def save():
        temporary=output.with_suffix('.json.tmp')
        temporary.write_text(json.dumps(report,indent=2)+'\n')
        temporary.replace(output)

    save()
    report['source_to_candidate']=sample_distances(original,candidate)
    report['candidate_to_source']=sample_distances(candidate,original)
    save()
    print(json.dumps(dict(source_to_candidate=report['source_to_candidate'],candidate_to_source=report['candidate_to_source'])),flush=True)
    closed=cap_estimated_neck(dict(vertices=candidate.vertices,faces=candidate.faces,
        metadata=dict(kind='estimated-neck-connector',original_atlas_geometry=False)),
        max_planarity_mm=.001,cap_method='planar-earcut')
    target=Path('exports/brachiocephalic-source-patch/resampled-right-neck-closed.npz')
    np.savez_compressed(target,vertices=closed['vertices'],faces=closed['faces'])
    report.update(status='CANDIDATE',volume_derivation=closed['metadata']['volume_derivation'],
        artifact=str(target),artifact_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
        source_union='NOT RUN',surroundings='NOT RUN',centerline_containment='NOT RUN')
    save()
    print(json.dumps(dict(status=report['status'],self_contact=report['volume_derivation']['self_contact']['status'])),flush=True)


if __name__=='__main__':
    main()
