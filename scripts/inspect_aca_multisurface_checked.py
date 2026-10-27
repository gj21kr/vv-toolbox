"""Run existing precision/provenance/self-contact gates on the three-part union."""
import hashlib
import json
from pathlib import Path
import numpy as np
import trimesh
from vv_toolbox.atlas import load_atlas
from vv_toolbox.solid_union import build_solid_union


def main():
    root=Path(__file__).resolve().parents[1]
    prior=json.loads((root/'docs/evidence/aca-source-cut-sac-unions.json').read_text())
    item=next(r for r in prior['rows'] if r['parent_part_id']=='FJ1654')
    atlas=load_atlas();parts={p['id']:p for p in atlas.meshes}
    if atlas.metadata['sha256']!=prior['atlas_archive_sha256']:raise ValueError('Atlas mismatch')
    path=root/item['artifact']
    if hashlib.sha256(path.read_bytes()).hexdigest()!=item['sha256']:raise ValueError('Candidate mismatch')
    with np.load(path,allow_pickle=False) as data:
        candidate=trimesh.Trimesh(vertices=data['vertices_mm'],faces=data['faces'],process=False)
    sources={'FJ1654-sac-candidate':candidate}
    for ident in ['FJ1655','FJ1690']:
        p=parts[ident]
        sources[ident]=trimesh.Trimesh(vertices=p['vertices'],faces=p['faces'],process=False)
    report=dict(schema='vv-toolbox.aca-multisurface-checked/1',case_revision=prior['case_revision'],
        atlas_archive_sha256=atlas.metadata['sha256'],candidate_sha256=item['sha256'],
        included_sources=sorted(sources),precision='float64',status='FAIL',accepted_for_generation=False)
    try:
        mesh,metadata=build_solid_union(sources,precision='float64')
        output=root/'exports/aca-multisurface-checked.npz'
        with output.open('xb') as stream:
            np.savez_compressed(stream,vertices_mm=mesh.vertices,faces=mesh.faces,metadata=np.array(json.dumps(metadata)))
        report.update(status='CANDIDATE',metadata=metadata,artifact=str(output.relative_to(root)),
                      sha256=hashlib.sha256(output.read_bytes()).hexdigest())
    except ValueError as error:report['reason']=str(error)
    (root/'docs/evidence/aca-multisurface-checked.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(report['status'],report.get('reason'),flush=True)


if __name__=='__main__':main()
