"""Audit all intervals on the same frozen eight-edge smoothing cohort."""
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh

from vv_toolbox.atlas import load_atlas
from vv_toolbox.case_io import load_case
from vv_toolbox.centerline_containment import inspect_centerline_containment

ROOT=Path(__file__).resolve().parents[1]
IDS=['FJ1654:e0','FJ1654M:e0','FJ1660:e0','FJ1660M:e0',
     'FJ1692:e0','FJ1692M:e0','FJ1694:e0','FJ1694M:e0']
source_path=ROOT/'exports/atlas-case-inspection/all-arterial.snapshot.json'
source,revision=load_case(source_path)
source_hash=hashlib.sha256(source_path.read_bytes()).hexdigest()
atlas=load_atlas();parts={p['id']:p for p in atlas.meshes}
rows=[]
for ident in IDS:
    name=('workbench-mca-smoothing-exact-indices.json' if ident=='FJ1692:e0'
          else f'workbench-smoothing-{ident.replace(":","-")}-exact-indices.json')
    prior_path=ROOT/'docs/evidence'/name
    prior=json.loads(prior_path.read_text())
    modified,changed_revision=load_case(ROOT/prior['result_file'])
    part=parts[ident.split(':')[0]]
    vertices,faces=np.asarray(part['vertices']),np.asarray(part['faces'])
    digest=hashlib.sha256(np.asarray(vertices[faces],dtype='<f8').tobytes()).hexdigest()
    if (prior['source_case_revision']!=revision or prior['source_file_sha256']!=source_hash
            or prior['result_case_revision']!=changed_revision
            or prior['surface_triangle_sha256']!=digest
            or prior['atlas_archive_sha256']!=atlas.metadata['sha256']):
        raise ValueError('Frozen source/result/surface identity mismatch: '+ident)
    mesh=trimesh.Trimesh(vertices,faces,process=False)
    row=dict(edge_id=ident,source_revision=revision,result_revision=changed_revision,
        prior_report_sha256=hashlib.sha256(prior_path.read_bytes()).hexdigest())
    for label,case in [('source',source),('smoothed',modified)]:
        edge=next(e for e in case['edges'] if e['id']==ident)
        row[label]=inspect_centerline_containment(mesh,edge['centerline_mm'],
            tolerance_mm=1e-6,max_depth=16,max_cells=100000)
    rows.append(row)
    print(json.dumps(dict(edge_id=ident,source=row['source']['status'],
        smoothed=row['smoothed']['status'],cells=row['smoothed']['processed_cells'])))
states=[r[s]['status'] for r in rows for s in ('source','smoothed')]
report=dict(scope='Numerical interior-ball coverage of each interval, assuming valid closed solid surfaces',
    status='FAIL' if 'FAIL' in states else 'UNKNOWN' if 'UNKNOWN' in states else 'PASS',
    rows=rows,source_file_sha256=source_hash,atlas_sha256=atlas.metadata['sha256'],
    anatomical_validity='NOT RUN',surface_self_intersection='NOT RUN',radius_surface_accuracy='NOT RUN')
(ROOT/'docs/evidence/cerebral-interval-containment.json').write_text(json.dumps(report,indent=2)+'\n')
