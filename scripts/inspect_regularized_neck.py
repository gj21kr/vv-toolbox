"""Measure final regularized MCA triangles against the stored design attachment."""
import hashlib
import json
from pathlib import Path
import numpy as np
from vv_toolbox.neck_conformity import inspect_neck_conformity

ROOT=Path(__file__).resolve().parents[1]


def main():
    report=json.loads((ROOT/'docs/evidence/regularized-mca-sac.json').read_text())
    path=ROOT/'exports/regularized-mca-sac/surface.npz'
    raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=report['artifact_sha256']:
        raise ValueError('surface hash mismatch')
    with np.load(path,allow_pickle=False) as data:
        vertices,faces=data['vertices_mm'],data['faces']
        meta=json.loads(str(data['metadata'].item()))
    if meta['case_revision']!=report['case_revision']:
        raise ValueError('case revision mismatch')
    neck=report['specification']['neck']
    basis=np.column_stack([neck[k] for k in ('width_axis','depth_axis','normal')])
    result=inspect_neck_conformity(vertices,faces,meta['attachment']['curve_mm'],
        neck['center_mm'],basis,distance_limit_mm=.30)
    result.update(case_revision=report['case_revision'],artifact_sha256=report['artifact_sha256'],
                  input_unchanged=path.read_bytes()==raw,app_applied=False)
    if not result['input_unchanged']:
        raise ValueError('surface changed')
    (ROOT/'docs/evidence/regularized-neck-conformity.json').write_text(
        json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in
        ('mapped_points_mm','triangle_indices','sampled_distances_mm')}))


if __name__=='__main__':
    main()
