"""Compare frozen source and smoothed radius envelopes with original surfaces."""
import hashlib
import argparse
import json
from pathlib import Path

import numpy as np
import trimesh

from vv_toolbox.atlas import load_atlas
from vv_toolbox.case_io import load_case
from vv_toolbox.centerline_containment import inspect_radius_envelope_containment
from vv_toolbox.radius_sections import inspect_radius_sections


def main(*, normal_sections=False):
    root=Path(__file__).resolve().parents[1]
    source_path=root/'exports/atlas-case-inspection/all-arterial.snapshot.json'
    source,revision=load_case(source_path)
    source_hash=hashlib.sha256(source_path.read_bytes()).hexdigest()
    atlas=load_atlas()
    parts={p['id']:p for p in atlas.meshes}
    identifiers=['FJ1654:e0','FJ1654M:e0','FJ1660:e0','FJ1660M:e0',
                 'FJ1692:e0','FJ1692M:e0','FJ1694:e0','FJ1694M:e0']
    rows=[]
    for ident in identifiers:
        name=('workbench-mca-smoothing-exact-indices.json' if ident=='FJ1692:e0'
              else f'workbench-smoothing-{ident.replace(":","-")}-exact-indices.json')
        prior_path=root/'docs/evidence'/name
        prior=json.loads(prior_path.read_text())
        modified,modified_revision=load_case(root/prior['result_file'])
        original=next(e for e in source['edges'] if e['id']==ident)
        part=parts[original['source_part_id']]
        vertices,faces=np.asarray(part['vertices']),np.asarray(part['faces'])
        triangle_hash=hashlib.sha256(np.asarray(vertices[faces],dtype='<f8').tobytes()).hexdigest()
        if (prior['source_case_revision']!=revision or prior['source_file_sha256']!=source_hash
                or prior['result_case_revision']!=modified_revision
                or prior['surface_triangle_sha256']!=triangle_hash
                or prior['atlas_archive_sha256']!=atlas.metadata['sha256']):
            raise ValueError('Frozen identity mismatch: '+ident)
        mesh=trimesh.Trimesh(vertices,faces,process=False)
        row=dict(edge_id=ident,source_revision=revision,result_revision=modified_revision,
                 surface_triangle_sha256=triangle_hash)
        for label,case in [('source',source),('smoothed',modified)]:
            edge=next(e for e in case['edges'] if e['id']==ident)
            if normal_sections:
                row[label]=inspect_radius_sections(
                    mesh,edge['centerline_mm'],edge['radii_mm'],samples=64,tolerance_mm=1e-6)
                previous_sections={s['index']:s for s in prior['measurements'][label]['cross_sections']}
                for section in row[label]['rows']:
                    measured=previous_sections.get(section['index'])
                    if measured and measured['status']=='MEASURED':
                        area_radius=measured['metrics']['area_equivalent_radius_mm']
                        section['source_area_equivalent_radius_mm']=area_radius
                        section['stored_to_area_radius_ratio']=section['radius_mm']/area_radius
                row[label]['section_measurement_report_sha256']=hashlib.sha256(prior_path.read_bytes()).hexdigest()
            else:
                row[label]=inspect_radius_envelope_containment(
                    mesh,edge['centerline_mm'],edge['radii_mm'],
                    tolerance_mm=1e-6,max_depth=16,max_cells=100000)
        rows.append(row)
        print(json.dumps(dict(edge_id=ident,source=row['source']['status'],
                             smoothed=row['smoothed']['status'])),flush=True)
    counts={group:{status:sum(r[group]['status']==status for r in rows)
                   for status in ('PASS','FAIL','UNKNOWN')} for group in ('source','smoothed')}
    report=dict(scope=('64 circular samples per non-endpoint normal section; not continuous tube-wall acceptance'
                       if normal_sections else 'Linear-radius ball envelopes; not reconstructed tube-wall acceptance'),
                source_file_sha256=source_hash,atlas_archive_sha256=atlas.metadata['sha256'],
                counts=counts,rows=rows,
                anatomical_validation='NOT RUN',tube_wall_containment='NOT RUN',
                original_modified=False)
    output='cerebral-radius-sections.json' if normal_sections else 'cerebral-radius-envelopes.json'
    (root/'docs/evidence'/output).write_text(
        json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps(counts))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--normal-sections',action='store_true')
    main(normal_sections=parser.parse_args().normal_sections)
