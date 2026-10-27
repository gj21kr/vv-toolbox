"""Fixed 0.25 mm / 20 degree section-centering experiment."""
import hashlib
import json
from pathlib import Path
import numpy as np
import trimesh
from vv_toolbox.atlas import load_atlas
from vv_toolbox.section_centering import center_section_path


def main():
    root=Path(__file__).resolve().parents[1]
    prior=json.loads((root/'docs/evidence/frontobasal-smoothing.json').read_text())
    path=root/prior['artifact']
    if hashlib.sha256(path.read_bytes()).hexdigest()!=prior['sha256']:raise ValueError('Path mismatch')
    with np.load(path,allow_pickle=False) as data:points=data['candidate_points_mm']
    atlas=load_atlas()
    if atlas.metadata['sha256']!=prior['atlas_archive_sha256']:raise ValueError('Atlas mismatch')
    p=next(p for p in atlas.meshes if p['id']=='FJ1690');mesh=trimesh.Trimesh(p['vertices'],p['faces'],process=False)
    candidate,meta=center_section_path(mesh,points,fixed_indices=[0,1,len(points)-2,len(points)-1],
                                     max_displacement_mm=.25,max_turn_degrees=20.)
    report=dict(schema='vv-toolbox.frontobasal-centering/1',parent_artifact_sha256=prior['sha256'],
        source_case_revision=prior['source_case_revision'],atlas_archive_sha256=atlas.metadata['sha256'],
        source_parameters=prior['source_parameters'],centering=meta,accepted_for_generation=False)
    if meta['status']=='CANDIDATE':
        output=root/'exports/frontobasal-path-centered.npz'
        with output.open('xb') as stream:
            np.savez_compressed(stream,candidate_points_mm=candidate,metadata=np.array(json.dumps(meta)))
        report.update(artifact=str(output.relative_to(root)),sha256=hashlib.sha256(output.read_bytes()).hexdigest())
    (root/'docs/evidence/frontobasal-centering.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(status=meta['status'],attempts=meta['attempts'],maximum_turn=meta.get('after',{}).get('maximum_turn_deg'),
        before=meta.get('before_residual_mm2'),after=meta.get('after_residual_mm2'))),flush=True)


if __name__=='__main__':main()
