"""Absolute context inspection for the separately built ICA/ACA union."""
import hashlib
import argparse
import json
from pathlib import Path
import time

import numpy as np
import trimesh

from vv_toolbox.atlas import load_atlas
from vv_toolbox.atlas_neck import build_neck_repairs
from vv_toolbox.radius_context import inspect_static_context


def main():
    parser=argparse.ArgumentParser()
    group=parser.add_mutually_exclusive_group()
    group.add_argument('--acom',action='store_true')
    group.add_argument('--anterior-core',action='store_true')
    group.add_argument('--brachiocephalic',action='store_true')
    group.add_argument('--access-trunks',action='store_true')
    args=parser.parse_args()
    tag='carotid-aca-acom' if args.acom else 'carotid-aca'
    started=time.perf_counter()
    stem=('femoral-anterior' if args.access_trunks else
          'anterior-brachiocephalic' if args.brachiocephalic else
          'anterior-core' if args.anterior_core else f'left-{tag}')
    record=json.loads((Path('docs/evidence')/f'{stem}-union.json').read_text())
    path=(Path('exports')/(stem+'-union')/'candidate.npz' if args.anterior_core or args.brachiocephalic or args.access_trunks
          else Path('exports')/(tag+'-junction')/'left.npz')
    if (record['status']!='CANDIDATE' or record['lineage_check']['status']!='PASS'
            or hashlib.sha256(path.read_bytes()).hexdigest()!=record['output_sha256']):
        raise ValueError('Union does not match validated candidate')
    with np.load(path,allow_pickle=False) as data:
        mesh=trimesh.Trimesh(data['vertices'],data['faces'],process=False)
    atlas=load_atlas()
    neck,_=build_neck_repairs(atlas)
    excluded=set(record['face_lineage']['source_names'])
    neighbors={p['id']:trimesh.Trimesh(p['vertices'],p['faces'],process=False)
               for p in [*atlas.meshes,*neck] if p['id'] not in excluded
               and p['layer'] in ('arterial','systemic_venous','hepatic_portal')}
    print(json.dumps(dict(status='RUNNING',neighbors=len(neighbors))),flush=True)
    result=inspect_static_context(mesh,neighbors)
    report=dict(candidate_sha256=record['output_sha256'],
                source_case_revision=record['source_case_revision'],
                excluded_union_sources=sorted(excluded),neighbor_count=len(neighbors),
                elapsed_seconds=time.perf_counter()-started,live_scene_changed=False,**result)
    (Path('docs/evidence')/f'{stem}-context.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({key:report[key] for key in ('status','neighbor_count','remaining_contacts','unknown','elapsed_seconds')}),flush=True)


if __name__=='__main__':
    main()
