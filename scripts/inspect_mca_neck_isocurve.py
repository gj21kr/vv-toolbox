"""Inspect all parent-profile zero contours on the generated MCA surface."""
import hashlib
import json
from pathlib import Path
import numpy as np
from vv_toolbox.case_io import load_case
from vv_toolbox.saccular_surface import _parent_field
from vv_toolbox.surface_isocurve import extract_surface_isocurve

ROOT=Path(__file__).resolve().parents[1]


def main():
    evidence=json.loads((ROOT/'docs/evidence/regularized-mca-sac.json').read_text())
    case,revision=load_case(ROOT/'exports/mca-profile-regularization/case.snapshot.json')
    path=ROOT/'exports/regularized-mca-sac/surface.npz'
    raw=path.read_bytes()
    if revision!=evidence['case_revision'] or hashlib.sha256(raw).hexdigest()!=evidence['artifact_sha256']:
        raise ValueError('input mismatch')
    with np.load(path,allow_pickle=False) as data:
        v,f=data['vertices_mm'],data['faces']
    edge=next(e for e in case['edges'] if e['id']=='FJ1692:e0')
    points,radii=np.array(edge['centerline_mm']),np.array(edge['radii_mm'])
    result=extract_surface_isocurve(v,f,_parent_field(v,points,radii))
    neck=evidence['specification']['neck']
    center=np.array(neck['center_mm'])
    basis=np.column_stack([neck[k] for k in ('width_axis','depth_axis','normal')])
    for component in result['components']:
        curve=np.array(component['points_mm'])
        local=(curve-center)@basis
        component['projected_width_depth_mm']=np.ptp(local[:,:2],axis=0).tolist()
        component['minimum_distance_to_neck_center_mm']=float(np.linalg.norm(curve-center,axis=1).min())
        component['nonlinear_profile_max_abs_residual_mm']=float(np.abs(_parent_field(curve,points,radii)).max())
    result.update(case_revision=revision,artifact_sha256=evidence['artifact_sha256'],
        neck_boundary_approval='UNKNOWN',input_unchanged=raw==path.read_bytes(),
        limitation='All loops retained; no loop selected by desired size. Linear vertex interpolation can miss same-sign crossings.')
    (ROOT/'docs/evidence/mca-neck-isocurve.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(status=result['status'],components=len(result['components']),
        closed=sum(c['closed'] for c in result['components']),
        nearest=sorted([{k:v for k,v in c.items() if k!='points_mm'} for c in result['components']],
                       key=lambda c:c['minimum_distance_to_neck_center_mm'])[:3])))


if __name__=='__main__':
    main()
