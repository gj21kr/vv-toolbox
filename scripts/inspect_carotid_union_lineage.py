"""Verify actual carotid output triangles against named source face lineage."""
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh

from vv_toolbox.case_io import load_case
from vv_toolbox.estimated_tube_volume import cap_estimated_neck
from vv_toolbox.union_lineage import verify_face_lineage


def main():
    report=json.loads(Path('docs/evidence/carotid-solid-union-diagnostic-float64-lineage.json').read_text())
    record=json.loads(Path('docs/evidence/atlas-neck-volume-case.json').read_text())
    case,revision=load_case(record['derived_case_file'])
    if revision!=report['source_case_revision']:raise ValueError('Source revision mismatch')
    parts={p['part_id']:p for p in case['surface_parts']}
    rows=[]
    for row in report['rows']:
        pid=row['part_id']
        if row['status']!='CANDIDATE':raise ValueError('Unavailable union')
        path=Path('exports/carotid-solid-union-diagnostic-float64-lineage')/(pid+'.npz')
        with np.load(path,allow_pickle=False) as data:
            mesh=trimesh.Trimesh(data['vertices'],data['faces'],process=False)
        sources={}
        for name in row['face_lineage']['source_names']:
            if name==pid:
                with np.load(Path('exports/neck-contour-candidates-corners')/(pid+'.npz'),allow_pickle=False) as data:
                    closed=cap_estimated_neck(dict(vertices=data['vertices'],faces=data['faces'],
                        metadata=dict(kind='estimated-neck-connector',original_atlas_geometry=False)),
                        max_planarity_mm=.001,cap_method='planar-earcut')
                source=trimesh.Trimesh(closed['vertices'],closed['faces'],process=False)
            else:
                p=parts[name];source=trimesh.Trimesh(p['vertices_mm'],p['faces'],process=False)
            digest=hashlib.sha256()
            digest.update(np.asarray(source.vertices,dtype='<f8').tobytes())
            digest.update(np.asarray(source.faces,dtype='<i8').tobytes())
            if digest.hexdigest()!=row['input_surfaces'][name]['geometry_sha256']:
                raise ValueError('Source geometry changed')
            sources[name]=source
        check=verify_face_lineage(mesh,sources,row['face_lineage'])
        rows.append(dict(part_id=pid,union_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),**check))
        print(json.dumps(rows[-1]),flush=True)
    Path('docs/evidence/carotid-union-lineage.json').write_text(json.dumps(dict(
        source_case_revision=revision,rows=rows,live_scene_changed=False),indent=2)+'\n')


if __name__=='__main__':
    main()
