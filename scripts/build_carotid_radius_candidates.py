"""Exercise boundary-preserving radius edits on the two estimated neck sources."""
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh

from vv_toolbox.case_io import load_case
from vv_toolbox.union_radius import scale_selected_radius


def main():
    union=json.loads(Path('docs/evidence/carotid-solid-union-diagnostic-float64-lineage.json').read_text())
    checks={r['part_id']:r for r in json.loads(Path('docs/evidence/carotid-union-lineage.json').read_text())['rows']}
    record=json.loads(Path('docs/evidence/atlas-neck-volume-case.json').read_text())
    case,revision=load_case(record['derived_case_file'])
    if revision!=union['source_case_revision']:raise ValueError('Revision mismatch')
    metadata=case['inspection']['atlas_scene_capture']['estimated_metadata']
    folder=Path('exports/carotid-radius-candidates');folder.mkdir(parents=True,exist_ok=True)
    rows=[]
    for row in union['rows']:
        pid=row['part_id'];path=Path('exports/carotid-solid-union-diagnostic-float64-lineage')/(pid+'.npz')
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        if checks[pid]['status']!='PASS' or checks[pid]['union_sha256']!=digest:
            raise ValueError('Lineage identity mismatch')
        with np.load(path,allow_pickle=False) as data:
            mesh=trimesh.Trimesh(data['vertices'],data['faces'],process=False)
        try:
            result,audit=scale_selected_radius(mesh,row['face_lineage'],pid,metadata[pid]['centerline'],
                scale=.9,transition_mm=5.,max_displacement_mm=.5)
            output=folder/(pid+'.npz')
            np.savez_compressed(output,vertices=result.vertices,faces=result.faces)
            rows.append(dict(part_id=pid,input_sha256=digest,output_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),**audit))
        except ValueError as error:
            rows.append(dict(part_id=pid,input_sha256=digest,status='FAIL',reason=str(error)))
        print(json.dumps({k:v for k,v in rows[-1].items() if k!='self_contact'}),flush=True)
    Path('docs/evidence/carotid-radius-candidates.json').write_text(json.dumps(dict(
        source_case_revision=revision,rows=rows,live_scene_changed=False),indent=2)+'\n')


if __name__=='__main__':
    main()
