"""Replay the recorded right MCA design without changing its tolerances."""
import hashlib
import argparse
import json
from pathlib import Path
import numpy as np
from vv_toolbox.case_io import load_case
from vv_toolbox.saccular_surface import build_saccular_candidate, _neck_grid_bounds

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--max-grid-voxels',type=int)
    args=parser.parse_args()
    prior_path=ROOT/'docs/evidence/atlas-saccular-candidates.json'
    prior=json.loads(prior_path.read_text())
    source=ROOT/'exports/atlas-case-inspection/all-arterial.snapshot.json'
    before=source.read_bytes()
    case,revision=load_case(source)
    if revision!=prior['case_revision']:
        raise ValueError('source revision changed')
    spec=next(r['specification'] for r in prior['attempts'] if r['edge_id']=='FJ1692:e0')
    edge=next(e for e in case['edges'] if e['id']=='FJ1692:e0')
    points,radii=np.asarray(edge['centerline_mm']),np.asarray(edge['radii_mm'])
    neck,p=spec['neck'],spec['parameters']
    spacing=prior['spacing_mm']
    budget=args.max_grid_voxels or prior['max_grid_voxels']
    low,high=_neck_grid_bounds(points,radii,neck,p,spacing)
    shape=np.rint((high-low)/spacing).astype(int)+1
    report=dict(case_revision=revision,prior_evidence_sha256=hashlib.sha256(prior_path.read_bytes()).hexdigest(),
                edge_id=edge['id'],specification=spec,spacing_mm=spacing,
                max_grid_voxels=budget,original_max_grid_voxels=prior['max_grid_voxels'],
                resource_budget_changed=budget!=prior['max_grid_voxels'],grid_shape_xyz=shape.tolist(),
                grid_voxel_count=int(np.prod(shape)),generator_version='saccular-sidewall-5',
                tolerances_unchanged=True,full_context_edge_count=len(case['edges']),
                surface_published=False,status='FAIL')
    try:
        v,f,meta=build_saccular_candidate(case,spec,spacing_mm=spacing,
                                         max_grid_voxels=budget)
        output=ROOT/'exports/atlas-saccular-candidates/FJ1692-e0-grid-v5.npz'
        np.savez_compressed(output,vertices_mm=v,faces=f,metadata=np.array(json.dumps(meta)))
        report.update(status='CANDIDATE',surface_published=True,metadata=meta,
                      surface_sha256=hashlib.sha256(output.read_bytes()).hexdigest())
    except ValueError as error:
        report['reason']=str(error)
    if source.read_bytes()!=before:
        raise ValueError('input snapshot changed')
    report.update(input_unchanged=True,anatomy='UNKNOWN',app_applied=False)
    suffix='' if args.max_grid_voxels is None else '-'+str(budget)
    (ROOT/f'docs/evidence/mca-saccular-grid-recheck{suffix}.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('specification','metadata')}))


if __name__=='__main__':
    main()
