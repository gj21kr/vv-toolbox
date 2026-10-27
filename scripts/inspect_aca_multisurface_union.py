"""Explicit three-part geometric union experiment; no anatomical acceptance."""
import hashlib
import json
from pathlib import Path
import importlib.metadata
import numpy as np
import trimesh
from vv_toolbox.atlas import load_atlas


def main():
    root=Path(__file__).resolve().parents[1]
    prior=json.loads((root/'docs/evidence/aca-source-cut-sac-unions.json').read_text())
    item=next(r for r in prior['rows'] if r['parent_part_id']=='FJ1654')
    atlas=load_atlas()
    if atlas.metadata['sha256']!=prior['atlas_archive_sha256']:raise ValueError('Atlas mismatch')
    path=root/item['artifact']
    if hashlib.sha256(path.read_bytes()).hexdigest()!=item['sha256']:raise ValueError('Candidate mismatch')
    parts={p['id']:p for p in atlas.meshes};ids=['FJ1654','FJ1655','FJ1690']
    with np.load(path,allow_pickle=False) as data:
        candidate=trimesh.Trimesh(vertices=data['vertices_mm'],faces=data['faces'],process=False)
    origin=candidate.vertices.mean(0);sources=[]
    for ident in ids:
        p=parts[ident];v,inverse=np.unique(np.asarray(p['vertices'],float),axis=0,return_inverse=True)
        mesh=trimesh.Trimesh(vertices=v-origin,faces=inverse[p['faces']],process=False)
        if not mesh.is_volume:raise ValueError('Closed source required: '+ident)
        sources.append(mesh)
    candidate.apply_translation(-origin)
    baseline=trimesh.boolean.union(sources,engine='manifold',check_volume=True)
    result=trimesh.boolean.union([candidate,*sources[1:]],engine='manifold',check_volume=True)
    removed=trimesh.boolean.difference([baseline,result],engine='manifold',check_volume=True)
    added=trimesh.boolean.difference([result,baseline],engine='manifold',check_volume=True)
    output=root/'exports/aca-multisurface-union.npz'
    report=dict(schema='vv-toolbox.aca-multisurface-union/1',case_revision=prior['case_revision'],
        atlas_archive_sha256=atlas.metadata['sha256'],candidate_sha256=item['sha256'],
        included_parts=ids,engine='manifold',engine_version=importlib.metadata.version('manifold3d'),
        calculation_origin_mm=origin.tolist(),closed_volume=bool(result.is_volume),
        component_count=len(result.split(only_watertight=False)),
        baseline_volume_mm3=float(baseline.volume),candidate_volume_mm3=float(result.volume),
        removed_volume_mm3=float(removed.volume),added_volume_mm3=float(added.volume),
        anatomical_union_authorization='NOT VERIFIED',branch_patency='NOT RUN',
        self_contact='NOT RUN',surrounding_clearance='NOT RUN',accepted_for_generation=False,
        limitation='Explicit experimental inclusion of ACom and contacting neighbor, not proof of branch attachment. Boolean arithmetic retriangulates inputs; exact source-face identity is not preserved.')
    with output.open('xb') as stream:
        np.savez_compressed(stream,vertices_mm=result.vertices+origin,faces=result.faces,metadata=np.array(json.dumps(report)))
    report.update(artifact=str(output.relative_to(root)),sha256=hashlib.sha256(output.read_bytes()).hexdigest())
    (root/'docs/evidence/aca-multisurface-union.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps(report),flush=True)


if __name__=='__main__':main()
