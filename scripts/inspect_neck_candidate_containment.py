"""Close contour candidates separately and screen nonattachment overlap."""
import json
import argparse
from pathlib import Path

import numpy as np
import trimesh

from vv_toolbox.atlas import load_atlas
from vv_toolbox.atlas_neck import build_neck_repairs
from vv_toolbox.disjoint_containment import inspect_disjoint_containment, _SurfaceValidationCache
from vv_toolbox.estimated_tube_volume import cap_estimated_neck
from vv_toolbox.mesh_pair_contact import inspect_pair_contact


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--preserve-corners',action='store_true')
    args=parser.parse_args()
    suffix='-corners' if args.preserve_corners else ''
    prior=json.loads(Path('docs/evidence/neck-candidate-contacts'+suffix+'.json').read_text())
    atlas=load_atlas();neck,_=build_neck_repairs(atlas)
    parts={p['id']:p for p in [*atlas.meshes,*neck]}
    volumes={};cap_reports={}
    for pid in prior['candidate_file_sha256']:
        path=Path('exports/neck-contour-candidates'+suffix)/(pid+'.npz')
        import hashlib
        if hashlib.sha256(path.read_bytes()).hexdigest()!=prior['candidate_file_sha256'][pid]:
            raise ValueError('Candidate changed since surface contact inspection')
        with np.load(path,allow_pickle=False) as data:
            part=dict(vertices=data['vertices'],faces=data['faces'],
                      metadata=dict(kind='estimated-neck-connector',original_atlas_geometry=False))
            closed=cap_estimated_neck(part,max_planarity_mm=.001,cap_method='planar-earcut')
        parts[pid]=closed
        volumes[pid]=trimesh.Trimesh(closed['vertices'],closed['faces'],process=False)
        cap_reports[pid]=closed['metadata']['volume_derivation']
    rows=[];cache=_SurfaceValidationCache()
    for row in prior['rows']:
        if row['declared_attachment']:
            continue
        pid,other=row['part_id'],row['other_id']
        if row['status']=='AABB_SEPARATED':
            rows.append(dict(part_id=pid,other_id=other,status='AABB_SEPARATED'))
            continue
        p=parts[other];mesh=trimesh.Trimesh(p['vertices'],p['faces'],process=False)
        # Caps are new geometry: repeat surface separation before containment.
        contact=inspect_pair_contact(volumes[pid].triangles,mesh.triangles)
        if contact['status']!='NO_SURFACE_CONTACT_DETECTED':
            check=dict(status=contact['status'],complete=contact['complete'])
        else:
            check=inspect_disjoint_containment(volumes[pid],mesh,_validation_cache=cache)
        rows.append(dict(part_id=pid,other_id=other,**check))
        print(pid,other,check['status'],flush=True)
    failures=[r for r in rows if r['status'] not in ('AABB_SEPARATED','NO_CONTAINMENT_DETECTED')]
    result=dict(candidate_file_sha256=prior['candidate_file_sha256'],cap_reports=cap_reports,
                rows=rows,unresolved_or_overlap=len(failures),
                status='CLEAR_NONATTACHMENT_VOLUMES' if not failures else 'UNRESOLVED_OR_OVERLAP',
                source_attachment_union='NOT RUN',anatomical_validation='NOT RUN',
                live_scene_changed=False)
    Path('docs/evidence/neck-candidate-containment'+suffix+'.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('rows','cap_reports')}))


if __name__=='__main__':
    main()
