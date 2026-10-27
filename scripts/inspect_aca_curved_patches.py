"""Generate separate open ACA dome patches from fixed saved rim proposals."""
import hashlib
import json
from pathlib import Path
import numpy as np
from vv_toolbox.case_io import load_case
from vv_toolbox.curved_sac_patch import build_curved_sac_patch


def main():
    root=Path(__file__).resolve().parents[1]
    source=root/'exports/candidate-case-download/case.snapshot.json'
    before=source.read_bytes();case,revision=load_case(source)
    prior=json.loads((root/'docs/evidence/aca-projected-rims.json').read_text())
    if revision!=prior['case_revision']:raise ValueError('Source revision changed')
    output=root/'exports/aca-curved-patches';output.mkdir(exist_ok=True)
    rows=[]
    for index,item in enumerate(prior['attempts']):
        row=dict(junction_id=item['junction_id'],status='FAIL',surface_published=False)
        try:
            v,f,meta=build_curved_sac_patch(case,item['specification'],item['projection'],rim_tolerance_mm=.02)
            path=output/f'patch-{index}.npz'
            with path.open('xb') as stream:
                np.savez_compressed(stream,vertices_mm=v,faces=f,metadata=np.array(json.dumps(meta)))
            row.update(status='CANDIDATE',surface_published=True,vertices=len(v),triangles=len(f),
                artifact=str(path.relative_to(root)),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),metadata=meta)
        except ValueError as error:row['reason']=str(error)
        rows.append(row);print(json.dumps({k:v for k,v in row.items() if k!='metadata'}))
    if source.read_bytes()!=before:raise RuntimeError('Source changed')
    report=dict(schema='vv-toolbox.aca-curved-patch-diagnostic/1',case_revision=revision,input_unchanged=True,
                attempts=rows,closed_lumen=False,accepted_for_generation=False,app_applied=False)
    (root/'docs/evidence/aca-curved-patches.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')


if __name__=='__main__':main()
