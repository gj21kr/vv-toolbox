"""Validate saved union lineage and all remaining arterial context."""
import hashlib
import json
from pathlib import Path
import numpy as np
import trimesh
from vv_toolbox.atlas import load_atlas
from vv_toolbox.radius_context import inspect_static_context
from vv_toolbox.union_lineage import verify_face_lineage


def read_mesh(root,item):
    path=root/item['artifact']
    if hashlib.sha256(path.read_bytes()).hexdigest()!=item['sha256']:raise ValueError('Artifact mismatch')
    with np.load(path,allow_pickle=False) as data:
        return trimesh.Trimesh(data['vertices_mm'],data['faces'],process=False)


def main():
    root=Path(__file__).resolve().parents[1]
    report=json.loads((root/'docs/evidence/aca-multisurface-checked.json').read_text())
    prior=json.loads((root/'docs/evidence/aca-source-cut-sac-unions.json').read_text())
    item=next(r for r in prior['rows'] if r['parent_part_id']=='FJ1654')
    if report['candidate_sha256']!=item['sha256']:raise ValueError('Parent binding changed')
    atlas=load_atlas()
    if atlas.metadata['sha256']!=report['atlas_archive_sha256']:raise ValueError('Atlas mismatch')
    parts={p['id']:p for p in atlas.meshes if p['layer']=='arterial'}
    def mesh(ident):
        p=parts[ident];return trimesh.Trimesh(p['vertices'],p['faces'],process=False)
    sources={'FJ1654-sac-candidate':read_mesh(root,item),'FJ1655':mesh('FJ1655'),'FJ1690':mesh('FJ1690')}
    candidate=read_mesh(root,report)
    lineage=verify_face_lineage(candidate,sources,report['metadata']['face_lineage'])
    neighbors={ident:mesh(ident) for ident in parts if ident not in ['FJ1654','FJ1655','FJ1690']}
    def progress(value):
        if value['completed']%100==0:print(value['completed'],value['total'],flush=True)
    context=inspect_static_context(candidate,neighbors,progress=progress)
    result=dict(schema='vv-toolbox.aca-checked-context/1',artifact_sha256=report['sha256'],
        atlas_archive_sha256=atlas.metadata['sha256'],face_lineage=lineage,context=context,
        neighbor_count=len(neighbors),branch_patency='NOT RUN',accepted_for_generation=False)
    (root/'docs/evidence/aca-checked-context.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(lineage=lineage['status'],context=context['status'],contacts=context['remaining_contacts'],unknown=context['unknown'])),flush=True)


if __name__=='__main__':main()
