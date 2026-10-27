"""Evaluate all four captured neck estimates with a fixed cap tolerance."""
import json
from pathlib import Path

import numpy as np

from vv_toolbox.case_io import load_case
from vv_toolbox.estimated_tube_volume import cap_estimated_neck


def main():
    case,revision=load_case('exports/atlas-case-estimates-ui/case.snapshot.json')
    records=case['inspection']['atlas_scene_capture']['estimated_metadata']
    rows=[]
    for p in case['surface_parts']:
        if p['part_id'] not in records:
            continue
        part=dict(id=p['part_id'],layer='arterial',vertices=np.asarray(p['vertices_mm']),
                  faces=np.asarray(p['faces']),metadata=records[p['part_id']])
        try:
            result=cap_estimated_neck(part,max_planarity_mm=.001)
            derivation=result['metadata']['volume_derivation']
            folder=Path('exports/estimated-neck-volumes');folder.mkdir(parents=True,exist_ok=True)
            path=folder/(p['part_id']+'.npz')
            if path.exists():
                raise ValueError('Existing candidate artifact preserved')
            with path.open('xb') as stream:
                np.savez_compressed(stream,vertices_mm=result['vertices'],faces=result['faces'],
                                    metadata=json.dumps(derivation))
            rows.append(dict(part_id=p['part_id'],status='PASS',derivation=derivation))
        except ValueError as error:
            rows.append(dict(part_id=p['part_id'],status='FAIL',error=str(error)))
    result=dict(status='PASS' if len(rows)==4 and all(r['status']=='PASS' for r in rows) else 'FAIL',
                case_revision=revision,max_planarity_mm=.001,rows=rows,
                scope='Four estimated display tubes closed as independent candidate volumes',
                active_scene_changed=False,source_modified=False,
                source_lumen_union='NOT RUN',surrounding_contact='NOT RUN')
    Path('docs/evidence/estimated-neck-volumes.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({**result,'rows':[{k:v for k,v in r.items() if k!='derivation'} for r in rows]}))


if __name__=='__main__':
    main()
