"""Separate source-derived opening candidates; do not replace the atlas."""
import hashlib
import json
from pathlib import Path
import numpy as np
from vv_toolbox.atlas import load_atlas
from vv_toolbox.mesh_neck_opening import build_neck_opening


def main():
    root=Path(__file__).resolve().parents[1]
    prior=json.loads((root/'docs/evidence/aca-mesh-rims.json').read_text())
    atlas=load_atlas()
    if atlas.metadata['sha256']!=prior['atlas_archive_sha256']:raise ValueError('Atlas changed')
    parts={p['id']:p for p in atlas.meshes};rows=[]
    output=root/'exports/aca-neck-openings';output.mkdir(exist_ok=True)
    for index,row in enumerate(prior['rows']):
        p=parts[row['parent_part_id']];neck=row['specification']['neck']
        result=dict(junction_id=row['junction_id'],parent_part_id=p['id'],status='FAIL')
        try:
            vertices,faces,meta=build_neck_opening(p['vertices'],p['faces'],neck['curve_mm'],neck['normal'])
            path=output/f'opening-{index}.npz'
            with path.open('xb') as stream:np.savez_compressed(stream,vertices_mm=vertices,faces=faces,metadata=np.array(json.dumps(meta)))
            result.update(status='CANDIDATE',artifact=str(path.relative_to(root)),artifact_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                          metadata=meta)
        except ValueError as error:result['reason']=str(error)
        rows.append(result)
        print(json.dumps(dict(junction=row['junction_id'],status=result['status'],reason=result.get('reason'),
            removed_faces=len(result.get('metadata',{}).get('removed_source_face_ids',[])),
            collar_faces=result.get('metadata',{}).get('new_collar_face_count'))),flush=True)
    report=dict(schema='vv-toolbox.aca-neck-openings/1',case_revision=prior['case_revision'],
                atlas_archive_sha256=atlas.metadata['sha256'],rows=rows,app_applied=False,accepted_for_generation=False)
    (root/'docs/evidence/aca-neck-openings.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')


if __name__=='__main__':main()
