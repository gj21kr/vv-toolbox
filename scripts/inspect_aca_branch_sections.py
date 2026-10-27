"""Compare all interior source-centerline stations with the saved union."""
import hashlib
import json
from pathlib import Path
import numpy as np
import trimesh
from vv_toolbox.atlas import load_atlas
from vv_toolbox.case_io import load_case
from vv_toolbox.source_sections import extract_source_sections


def main():
    root=Path(__file__).resolve().parents[1]
    prior=json.loads((root/'docs/evidence/aca-multisurface-checked.json').read_text())
    path=root/prior['artifact']
    if hashlib.sha256(path.read_bytes()).hexdigest()!=prior['sha256']:raise ValueError('Candidate hash mismatch')
    with np.load(path,allow_pickle=False) as data:
        candidate=trimesh.Trimesh(data['vertices_mm'],data['faces'],process=False)
    case,revision=load_case(root/'exports/atlas-case-inspection/all-arterial.snapshot.json')
    atlas=load_atlas()
    if atlas.metadata['sha256']!=prior['atlas_archive_sha256'] or next(s['sha256'] for s in case['sources'] if s['id']=='bp3d')!=atlas.metadata['sha256']:
        raise ValueError('Atlas identity mismatch')
    parts={p['id']:p for p in atlas.meshes};rows=[]
    keys=('index','status','origin_mm','normal','area_mm2','center_boundary_distance_mm','reason','enclosing_contour_count')
    for ident in ['FJ1654','FJ1655','FJ1690']:
        # Extraction-edge ID convention; no anatomical segment label inferred.
        edges=[e for e in case['edges'] if e['id'].startswith(ident+':')]
        if not edges or any(e['centerline_mm'] is None for e in edges):raise ValueError('Complete explicit source paths required: '+ident)
        part=parts[ident];source=trimesh.Trimesh(part['vertices'],part['faces'],process=False)
        for edge in edges:
            points=np.asarray(edge['centerline_mm'],float)
            before=extract_source_sections(source,points)
            after=extract_source_sections(candidate,points)
            comparisons=[]
            for a,b in zip(before['profiles'],after['profiles']):
                row=dict(index=a['index'],before={k:a[k] for k in keys if k in a},after={k:b[k] for k in keys if k in b})
                if a['status']==b['status']=='MEASURED':row['area_change_mm2']=b['area_mm2']-a['area_mm2']
                comparisons.append(row)
            rows.append(dict(part_id=ident,edge_id=edge['id'],station_count=len(points),
                before_counts=before['counts'],after_counts=after['counts'],comparisons=comparisons))
            print(ident,edge['id'],before['counts'],after['counts'],flush=True)
    result=dict(schema='vv-toolbox.aca-branch-sections/1',source_case_revision=revision,
        artifact_sha256=prior['sha256'],atlas_archive_sha256=atlas.metadata['sha256'],rows=rows,
        endpoint_sections='NOT RUN',continuous_patency='NOT RUN',accepted_for_generation=False,
        limitation='Sampled sections on extracted source centerlines. Area preservation alone does not prove identical contour or continuous open path.')
    (root/'docs/evidence/aca-branch-sections.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')


if __name__=='__main__':main()
