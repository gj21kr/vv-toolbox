"""Generate complete corrected vessel surfaces at an explicit fine resolution."""
import hashlib
import json
import math
from pathlib import Path
import numpy as np
from vv_toolbox.case_io import load_case
from vv_toolbox.case_surface import build_case_surface

ROOT=Path(__file__).resolve().parents[1]


def main():
    path=ROOT/'exports/synthetic-full-iliac-profiles/case.snapshot.json'
    raw=path.read_bytes();case,revision=load_case(path)
    prior=json.loads((ROOT/'docs/evidence/full-iliac-profile-candidate.json').read_text())
    if revision!=prior['case_revision']:raise ValueError('candidate revision mismatch')
    ids=['R-EIA-retained','FJ3617:e0'];spacing=.15;budget=1_000_000_000
    selected=[e for e in case['edges'] if e['id'] in ids]
    points=np.concatenate([e['centerline_mm'] for e in selected]);radius=max(max(e['radii_mm']) for e in selected)
    estimate=math.prod(int(n) for n in np.ceil((np.ptp(points,axis=0)+2*radius+12*spacing)/spacing)+1)
    print(json.dumps(dict(stage='preflight',spacing_mm=spacing,grid_bound=estimate,budget=budget)),flush=True)
    out=ROOT/'exports/full-iliac-surface';out.mkdir(parents=True,exist_ok=True)
    try:
        v,f,metadata=build_case_surface(case,ids,spacing_mm=spacing,max_grid_voxels=budget)
        artifact=out/'surface.npz'
        np.savez_compressed(artifact,vertices_mm=v,faces=f,metadata=np.array(json.dumps(metadata)))
        surface=dict(status='PASS',vertices=len(v),triangles=len(f),metadata=metadata,
                     sha256=hashlib.sha256(artifact.read_bytes()).hexdigest())
    except ValueError as error:
        surface=dict(status='FAIL',reason=str(error),surface_published=False)
    if path.read_bytes()!=raw:raise ValueError('input changed')
    report=dict(schema='vv-toolbox.full-iliac-surface/1',case_revision=revision,edge_ids=ids,
        spacing_mm=spacing,max_grid_voxels=budget,grid_bound=estimate,surface=surface,input_unchanged=True,
        scope='Complete two selected paths; not the whole arterial atlas',
        final_mesh_collision='NOT RUN',visual_review='NOT RUN',default_app_applied=False)
    (ROOT/'docs/evidence/full-iliac-surface.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in surface.items() if k!='metadata'}))


if __name__=='__main__':main()
