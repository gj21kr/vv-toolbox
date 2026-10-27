"""Export noncircular original profiles for the frozen eight-edge cohort."""
import hashlib
import argparse
import json
from pathlib import Path

import numpy as np
import trimesh

from vv_toolbox.atlas import load_atlas
from vv_toolbox.case_io import load_case
from vv_toolbox.source_sections import extract_source_sections


def main(*, smoothed=False, tangent_half_window_mm=None):
    root=Path(__file__).resolve().parents[1]
    path=root/'exports/atlas-case-inspection/all-arterial.snapshot.json'
    raw=path.read_bytes();case,revision=load_case(path)
    prior=json.loads((root/'docs/evidence/cerebral-radius-sections.json').read_text())
    atlas=load_atlas()
    if (hashlib.sha256(raw).hexdigest()!=prior['source_file_sha256']
            or atlas.metadata['sha256']!=prior['atlas_archive_sha256']):
        raise ValueError('Frozen input mismatch')
    parts={p['id']:p for p in atlas.meshes}
    rows=[]
    for record in prior['rows']:
        if record['source_revision']!=revision:raise ValueError('Source revision mismatch')
        selected_case,selected_revision=case,revision
        if smoothed:
            ident=record['edge_id']
            name=('workbench-mca-smoothing-exact-indices.json' if ident=='FJ1692:e0'
                  else f'workbench-smoothing-{ident.replace(":","-")}-exact-indices.json')
            saved=json.loads((root/'docs/evidence'/name).read_text())
            selected_case,selected_revision=load_case(root/saved['result_file'])
            if selected_revision!=record['result_revision']:
                raise ValueError('Smoothed revision mismatch')
        edge=next(e for e in selected_case['edges'] if e['id']==record['edge_id'])
        part=parts[edge['source_part_id']]
        mesh=trimesh.Trimesh(part['vertices'],part['faces'],process=False)
        result=extract_source_sections(mesh,edge['centerline_mm'],tangent_half_window_mm=tangent_half_window_mm)
        if result['indexing']['triangle_sha256']!=record['surface_triangle_sha256']:
            raise ValueError('Original triangles differ')
        result.update(source_case_revision=selected_revision,edge_id=edge['id'],
                      source_part_id=part['id'],atlas_sha256=atlas.metadata['sha256'])
        payload=(json.dumps(result,indent=2,allow_nan=False)+'\n').encode()
        digest=hashlib.sha256(payload).hexdigest()
        destination=root/'exports/cerebral-source-sections'/digest/'profiles.json'
        destination.parent.mkdir(parents=True,exist_ok=True)
        if destination.exists() and destination.read_bytes()!=payload:
            raise ValueError('Existing profile export differs')
        destination.write_bytes(payload)
        measured=[p for p in result['profiles'] if p['status']=='MEASURED']
        distances=[]
        for profile in measured:
            _,d,_=trimesh.proximity.closest_point(mesh,np.asarray(profile['contour_xyz_mm']))
            distances.extend(d.tolist())
        row=dict(edge_id=edge['id'],case_revision=selected_revision,counts=result['counts'],
                 artifact=destination.relative_to(root).as_posix(),sha256=digest,
                 original_triangle_sha256=record['surface_triangle_sha256'],
                 maximum_contour_vertex_surface_residual_mm=max(distances) if distances else None,
                 contour_vertices_checked=len(distances))
        rows.append(row);print(json.dumps(row),flush=True)
    if path.read_bytes()!=raw:raise ValueError('Source snapshot changed during inspection')
    report=dict(source_case_revision=revision,source_file_sha256=hashlib.sha256(raw).hexdigest(),
                atlas_archive_sha256=atlas.metadata['sha256'],rows=rows,
                centerline_group='smoothed' if smoothed else 'source',
                tangent_half_window_mm=tangent_half_window_mm,
                source_modified=False,loft_surface='NOT RUN',anatomical_validation='NOT RUN')
    output='cerebral-smoothed-section-profiles.json' if smoothed else 'cerebral-source-section-profiles.json'
    if tangent_half_window_mm is not None:
        output=output.replace('.json',f'-window{tangent_half_window_mm:g}mm.json')
    (root/'docs/evidence'/output).write_text(
        json.dumps(report,indent=2)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--smoothed',action='store_true')
    parser.add_argument('--tangent-window-mm',type=float)
    args=parser.parse_args()
    main(smoothed=args.smoothed,tangent_half_window_mm=args.tangent_window_mm)
