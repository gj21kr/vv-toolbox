"""Join original ACA surface openings and curved dome patches as candidates."""
import hashlib
import json
from pathlib import Path
import numpy as np
from vv_toolbox.atlas import load_atlas
from vv_toolbox.case_io import load_case
from vv_toolbox.source_sac_union import build_source_sac_union


def main():
    root=Path(__file__).resolve().parents[1]
    case,revision=load_case(root/'exports/candidate-case-download/case.snapshot.json')
    prior=json.loads((root/'docs/evidence/aca-mesh-rims.json').read_text())
    atlas=load_atlas()
    if revision!=prior['case_revision'] or atlas.metadata['sha256']!=prior['atlas_archive_sha256']:
        raise ValueError('Source identity changed')
    parts={p['id']:p for p in atlas.meshes};rows=[]
    output=root/'exports/aca-source-cut-sac-unions';output.mkdir(exist_ok=True)
    for index,row in enumerate(prior['rows']):
        p=parts[row['parent_part_id']];result=dict(junction_id=row['junction_id'],parent_part_id=p['id'],status='FAIL')
        try:
            v,f,meta=build_source_sac_union(case,row['specification'],p['vertices'],p['faces'],source_part_id=p['id'])
            path=output/f'union-{index}.npz'
            with path.open('xb') as stream:np.savez_compressed(stream,vertices_mm=v,faces=f,metadata=np.array(json.dumps(meta)))
            result.update(status='CANDIDATE',artifact=str(path.relative_to(root)),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),metadata=meta)
        except ValueError as error:result['reason']=str(error)
        rows.append(result)
        print(json.dumps(dict(junction=row['junction_id'],status=result['status'],reason=result.get('reason'),
                             volume_mm3=result.get('metadata',{}).get('volume_mm3'))),flush=True)
    report=dict(schema='vv-toolbox.aca-source-sac-unions/1',case_revision=revision,
                atlas_archive_sha256=atlas.metadata['sha256'],rows=rows,app_applied=False,accepted_for_generation=False)
    (root/'docs/evidence/aca-source-cut-sac-unions.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')


if __name__=='__main__':main()
