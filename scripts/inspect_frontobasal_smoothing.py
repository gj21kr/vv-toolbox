"""Inspect bounded smoothing of the saved inside-path candidate."""
import hashlib
import json
from pathlib import Path
import numpy as np
import trimesh
from vv_toolbox.atlas import load_atlas
from vv_toolbox.contained_path_smoothing import smooth_contained_path
from vv_toolbox.source_sections import extract_source_sections


def main():
    root=Path(__file__).resolve().parents[1]
    prior=json.loads((root/'docs/evidence/frontobasal-path-adaptive.json').read_text())
    path=root/prior['artifact']
    if hashlib.sha256(path.read_bytes()).hexdigest()!=prior['sha256']:raise ValueError('Path changed')
    with np.load(path,allow_pickle=False) as data:
        points=data['candidate_points_mm'];original=data['original_points_mm']
    atlas=load_atlas()
    if atlas.metadata['sha256']!=prior['atlas_archive_sha256']:raise ValueError('Atlas changed')
    p=next(p for p in atlas.meshes if p['id']=='FJ1690');mesh=trimesh.Trimesh(p['vertices'],p['faces'],process=False)
    candidate,meta=smooth_contained_path(mesh,points,fixed_indices=[0,1,len(points)-2,len(points)-1],max_displacement_mm=.25)
    params=prior['projection']['source_parameters']
    reference=np.column_stack([np.interp(params,np.arange(len(original)),original[:,k]) for k in range(3)])
    sections=extract_source_sections(mesh,candidate)
    output=root/'exports/frontobasal-path-smoothed.npz'
    with output.open('xb') as stream:
        np.savez_compressed(stream,candidate_points_mm=candidate,metadata=np.array(json.dumps(meta)))
    report=dict(schema='vv-toolbox.frontobasal-smoothing/1',parent_artifact_sha256=prior['sha256'],
        source_case_revision=prior['source_case_revision'],atlas_archive_sha256=atlas.metadata['sha256'],
        artifact=str(output.relative_to(root)),sha256=hashlib.sha256(output.read_bytes()).hexdigest(),
        smoothing=meta,source_parameters=params,maximum_displacement_from_original_mm=float(np.linalg.norm(candidate-reference,axis=1).max()),
        source_sections=sections,accepted_for_generation=False)
    (root/'docs/evidence/frontobasal-smoothing.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(before=meta['before']['maximum_turn_deg'],after=meta['after']['maximum_turn_deg'],
        steps=len(meta['accepted_steps']),containment=meta['containment']['status'],sections=sections['counts'])),flush=True)


if __name__=='__main__':main()
