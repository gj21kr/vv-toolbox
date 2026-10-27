"""Diagnose rejected unions without publishing them as usable geometry."""
import json
import argparse
from pathlib import Path
import numpy as np
from vv_toolbox.atlas import load_atlas
from vv_toolbox.case_io import load_case
from vv_toolbox.bifurcation_saccular import validate_bifurcation_saccular_spec
from vv_toolbox.mesh_neck_opening import build_neck_opening
from vv_toolbox.curved_sac_patch import _build_rim_patch
from vv_toolbox.mesh_self_contact import inspect_self_contact


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--source-cut',action='store_true')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    prior=json.loads((root/'docs/evidence/aca-mesh-rims.json').read_text())
    case,revision=load_case(root/'exports/candidate-case-download/case.snapshot.json')
    atlas=load_atlas()
    if revision!=prior['case_revision'] or atlas.metadata['sha256']!=prior['atlas_archive_sha256']:
        raise ValueError('Source identity mismatch')
    parts={p['id']:p for p in atlas.meshes};rows=[]
    for row in prior['rows']:
        spec=row['specification'];validate_bifurcation_saccular_spec(case,spec)
        p=parts[row['parent_part_id']];neck=spec['neck']
        builder=build_neck_opening
        if args.source_cut:
            from vv_toolbox.source_neck_opening import build_source_neck_opening
            builder=build_source_neck_opening
        v,f,opening=builder(p['vertices'],p['faces'],neck['curve_mm'],neck['normal'])
        rim=np.asarray(opening['neck_boundary_vertex_ids']);n=len(rim)
        pv,pf,_=_build_rim_patch(spec,v[rim],opening['trace'])
        mapping=np.r_[rim,np.arange(len(v),len(v)+len(pv)-n)]
        vertices=np.vstack([v,pv[n:]]);faces=np.vstack([f,mapping[pf]])
        lineage=opening['source_face_ids']
        def region(i):
            if args.source_cut:
                return 'dome' if i>=len(f) else 'source_surface'
            return 'dome' if i>=len(f) else ('retained_source' if lineage[i]>=0 else 'collar')
        contact=inspect_self_contact(vertices,faces)
        pairs=[]
        for a,b in contact['contact_pairs']:
            pairs.append(dict(face_ids=[a,b],regions=[region(a),region(b)],
                shared_vertex_ids=sorted(set(faces[a].tolist())&set(faces[b].tolist())),
                triangles_mm=vertices[faces[[a,b]]].tolist()))
        groups={}
        for pair in pairs:
            key=' / '.join(sorted(pair['regions']));groups[key]=groups.get(key,0)+1
        import trimesh
        mesh=trimesh.Trimesh(vertices=vertices,faces=faces,process=False)
        result=dict(part_id=p['id'],self_contact=contact,region_pair_counts=groups,
                    single_closed_volume=bool(mesh.is_volume and len(mesh.split(only_watertight=False))==1),
                    face_counts=dict(opening=len(f),dome=len(pf)),pairs=pairs)
        rows.append(result)
        print(p['id'],groups,flush=True)
    report=dict(schema='vv-toolbox.aca-union-contact-diagnosis/1',case_revision=revision,
        atlas_archive_sha256=atlas.metadata['sha256'],rows=rows,
        accepted_for_generation=False,app_applied=False)
    filename='aca-source-cut-union-contacts.json' if args.source_cut else 'aca-union-contact-diagnosis.json'
    (root/'docs/evidence'/filename).write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')


if __name__=='__main__':main()
