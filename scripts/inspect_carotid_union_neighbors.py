"""Compare contacting neighbor identities before and after carotid solid union."""
import hashlib
import argparse
import json
from pathlib import Path

import numpy as np
import trimesh

from vv_toolbox.atlas import load_atlas
from vv_toolbox.atlas_neck import build_neck_repairs
from vv_toolbox.mesh_pair_contact import inspect_pair_contact


def separated(a,b):
    return bool(np.any(a.min(0)>b.max(0)+1e-8) or np.any(b.min(0)>a.max(0)+1e-8))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--radius-edit',action='store_true')
    args=parser.parse_args()
    atlas=load_atlas();neck,_=build_neck_repairs(atlas)
    parts={p['id']:p for p in [*atlas.meshes,*neck]
           if p['layer'] in ('arterial','systemic_venous','hepatic_portal')}
    endpoints={p['id']:p['metadata']['source_endpoint_ids'] for p in neck if 'carotid' in p['id']}
    identity=json.loads(Path('docs/evidence/carotid-union-fidelity.json').read_text())
    edits={r['part_id']:r for r in json.loads(Path('docs/evidence/carotid-radius-candidates.json').read_text())['rows']} if args.radius_edit else {}
    output_hashes={}
    unions={};baselines={}
    for row in identity['rows']:
        pid=row['part_id']
        path=Path('exports/carotid-solid-union-diagnostic-float64')/(pid+'.npz')
        if hashlib.sha256(path.read_bytes()).hexdigest()!=row['union_file_sha256']:
            raise ValueError('Union changed')
        with np.load(path,allow_pickle=False) as data:
            unions[pid]=trimesh.Trimesh(data['vertices'],data['faces'],process=False)
        output_hashes[pid]=row['union_file_sha256']
        if args.radius_edit:
            edit=edits[pid]
            if edit['status']!='CANDIDATE' or edit['input_sha256']!=row['union_file_sha256']:
                raise ValueError('Radius edit input identity mismatch')
            baseline=unions[pid]
            edited_path=Path('exports/carotid-radius-candidates')/(pid+'.npz')
            if hashlib.sha256(edited_path.read_bytes()).hexdigest()!=edit['output_sha256']:
                raise ValueError('Radius output changed')
            with np.load(edited_path,allow_pickle=False) as data:
                unions[pid]=trimesh.Trimesh(data['vertices'],data['faces'],process=False)
            baselines[pid]=baseline
            output_hashes[pid]=edit['output_sha256']
            continue
        bridge=Path('exports/neck-contour-candidates-corners')/(pid+'.npz')
        if hashlib.sha256(bridge.read_bytes()).hexdigest()!=row['bridge_file_sha256']:
            raise ValueError('Bridge changed')
        with np.load(bridge,allow_pickle=False) as data:
            meshes=[trimesh.Trimesh(data['vertices'],data['faces'],process=False)]
        for target in endpoints[pid]:
            p=parts[target];meshes.append(trimesh.Trimesh(p['vertices'],p['faces'],process=False))
        baselines[pid]=trimesh.util.concatenate(meshes)
    for pid,mesh in unions.items():
        for target in endpoints[pid]:parts.pop(target)
        parts[pid]=dict(vertices=mesh.vertices,faces=mesh.faces)
    rows=[]
    for pid,union in unions.items():
        for other_id,p in sorted(parts.items()):
            if pid==other_id:continue
            mesh=trimesh.Trimesh(p['vertices'],p['faces'],process=False)
            before=baselines.get(other_id,mesh)
            row=dict(part_id=pid,other_id=other_id)
            if separated(union.vertices,mesh.vertices) and separated(baselines[pid].vertices,before.vertices):
                row.update(before='AABB_SEPARATED',after='AABB_SEPARATED')
            else:
                for key,a,b in [('before',baselines[pid],before),('after',union,mesh)]:
                    check=inspect_pair_contact(a.triangles,b.triangles)
                    row[key]=check['status']
                    row[key+'_contacts']=len(check['contact_pairs'])
                    row[key+'_complete']=check['complete']
            rows.append(row)
        print(pid,'checked',len(parts)-1,'neighbors',flush=True)
    new=[r for r in rows if r['after']=='CONTACT_DETECTED' and r['before']!='CONTACT_DETECTED']
    unknown=[r for r in rows if any(r.get(k)=='UNKNOWN' for k in ('before','after'))
             or any(r.get(k) is False for k in ('before_complete','after_complete'))]
    report=dict(union_files=[dict(part_id=pid,sha256=digest) for pid,digest in output_hashes.items()],
                rows=rows,new_contacting_neighbors=new,unknown=unknown,
                scope='Surface-contacting neighbor identity comparison; contact-location equivalence not established',
                volume_containment='NOT RUN',anatomical_validation='NOT RUN',live_scene_changed=False)
    name='carotid-radius-neighbors.json' if args.radius_edit else 'carotid-union-neighbors.json'
    Path('docs/evidence',name).write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(comparisons=len(rows),new=len(new),unknown=len(unknown))))


if __name__=='__main__':
    main()
