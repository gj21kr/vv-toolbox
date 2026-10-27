"""Full context check for the exact protected replacement, with durable progress."""
import hashlib
import json
from pathlib import Path
import time

import numpy as np
import trimesh

from vv_toolbox.atlas import load_atlas
from vv_toolbox.atlas_neck import build_neck_repairs
from vv_toolbox.radius_context import inspect_static_context


def main():
    started=time.perf_counter();root=Path('docs/evidence')
    read=lambda name:json.loads((root/name).read_text())
    baseline=read('femoral-anterior-context.json');record=read('resampled-access-protected.json')
    path=Path(record['artifact'])
    if hashlib.sha256(path.read_bytes()).hexdigest()!=record['output_sha256']:
        raise ValueError('Replacement geometry mismatch')
    with np.load(path,allow_pickle=False) as data:
        mesh=trimesh.Trimesh(data['vertices'],data['faces'],process=False)
    atlas=load_atlas();neck,_=build_neck_repairs(atlas)
    neighbors={p['id']:trimesh.Trimesh(p['vertices'],p['faces'],process=False)
        for p in [*atlas.meshes,*neck] if p['id'] not in baseline['excluded_union_sources']
        and p['layer'] in ('arterial','systemic_venous','hepatic_portal')}
    digest=hashlib.sha256()
    for name,other in sorted(neighbors.items()):
        encoded=name.encode('utf-8');digest.update(len(encoded).to_bytes(8,'little'));digest.update(encoded)
        for array in (np.asarray(other.vertices,dtype='<f8'),np.asarray(other.faces,dtype='<i8')):
            digest.update(str(array.shape).encode('ascii'));digest.update(array.tobytes())
    if digest.hexdigest()!=baseline['context_sha256'] or len(neighbors)!=baseline['neighbor_count']:
        raise ValueError('Context differs from baseline')
    report=dict(status='RUNNING',candidate_sha256=record['output_sha256'],context_sha256=digest.hexdigest(),
        source_case_revision=record['source_case_revision'],excluded_union_sources=baseline['excluded_union_sources'],
        neighbor_count=len(neighbors),completed=0,rows=[],live_scene_changed=False)
    output=root/'resampled-access-context.json'
    def save():
        report['elapsed_seconds']=time.perf_counter()-started
        temporary=output.with_suffix('.json.tmp');temporary.write_text(json.dumps(report,indent=2)+'\n');temporary.replace(output)
    def progress(event):
        row=event['row'];report['rows'].append(dict(neighbor_id=row['neighbor_id'],**row['after']))
        report['completed']=event['completed']
        if event['completed']%10==0 or event['completed']==event['total']:save()
        if event['completed']%100==0:print(json.dumps(dict(completed=event['completed'],total=event['total'])),flush=True)
    save()
    result=inspect_static_context(mesh,neighbors,progress=progress)
    report.update(result)
    report['comparison']=dict(new_contact_neighbors=sorted(set(result['remaining_contacts'])-set(baseline['remaining_contacts'])),
        removed_contact_neighbors=sorted(set(baseline['remaining_contacts'])-set(result['remaining_contacts'])),
        same_neighbor_contact_location_equivalence='NOT RUN')
    save()
    print(json.dumps(dict(status=report['status'],neighbors=len(neighbors),contacts=len(report['remaining_contacts']),
                         unknown=len(report['unknown']),comparison=report['comparison'])),flush=True)


if __name__=='__main__':
    main()
