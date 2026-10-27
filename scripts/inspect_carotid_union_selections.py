"""Resolve source selections on actual geometry with verified face lineage."""
import hashlib
import json
from pathlib import Path

import numpy as np

from vv_toolbox.union_selection import select_union_source


def main():
    union=json.loads(Path('docs/evidence/carotid-solid-union-diagnostic-float64-lineage.json').read_text())
    verified=json.loads(Path('docs/evidence/carotid-union-lineage.json').read_text())
    checks={r['part_id']:r for r in verified['rows']}
    rows=[]
    for row in union['rows']:
        pid=row['part_id'];check=checks[pid]
        path=Path('exports/carotid-solid-union-diagnostic-float64-lineage')/(pid+'.npz')
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        if check['status']!='PASS' or check['union_sha256']!=digest:
            raise ValueError('Verified lineage does not match union')
        with np.load(path,allow_pickle=False) as data:
            selections=[select_union_source(data['vertices'],data['faces'],row['face_lineage'],name)
                        for name in row['face_lineage']['source_names']]
            face_ids=[face for selection in selections for face in selection['face_ids']]
            if sorted(face_ids)!=list(range(len(data['faces']))):
                raise ValueError('Incomplete or duplicated source selection')
            total=len(data['faces'])
        rows.append(dict(part_id=pid,union_sha256=digest,faces=total,
            selections=[dict(source_name=s['source_name'],faces=len(s['face_ids']),
                             vertices=len(s['vertex_ids']),exclusive_vertices=len(s['exclusive_vertex_ids']),
                             shared_vertices=len(s['shared_interface_vertex_ids'])) for s in selections]))
    result=dict(status='PASS',rows=rows,scope='Complete source face partition and shared vertex classification',
                geometry_changed=False,interactive_selection='NOT RUN',modification='NOT RUN')
    Path('docs/evidence/carotid-union-selections.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__':
    main()
