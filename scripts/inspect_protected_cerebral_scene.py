"""Compare every affected pair when all eight protected surfaces replace sources."""
import hashlib
import io
import itertools
import json
from pathlib import Path

import numpy as np
import trimesh

from vv_toolbox.atlas import load_atlas
from vv_toolbox.mesh_pair_contact import inspect_pair_contact


def main():
    root=Path(__file__).resolve().parents[1]
    raw=(root/'docs/evidence/protected-cerebral-fit.json').read_bytes()
    candidates=json.loads(raw)
    atlas=load_atlas()
    if atlas.metadata['sha256']!=candidates['atlas_archive_sha256']:
        raise ValueError('Atlas identity mismatch')
    parts={p['id']:p for p in atlas.meshes if p['layer']=='arterial'}
    before={ident:np.asarray(p['vertices'])[np.asarray(p['faces'])] for ident,p in parts.items()}
    after=before.copy();changed={}
    for entry in candidates['rows']:
        if entry['status']!='CANDIDATE':raise ValueError('Incomplete candidate set')
        ident=entry['source_part_id'];part=parts[ident]
        data=(root/entry['artifact']).read_bytes()
        if hashlib.sha256(data).hexdigest()!=entry['sha256']:raise ValueError('Artifact mismatch')
        mesh=trimesh.load(io.BytesIO(data),file_type='ply',process=False)
        if not np.array_equal(mesh.faces,part['faces']):raise ValueError('Face IDs changed')
        protected=entry['protected_vertex_ids']
        if not np.array_equal(mesh.vertices[protected],np.asarray(part['vertices'])[protected]):
            raise ValueError('Protected vertices changed')
        if ident in changed:raise ValueError('Duplicate replacement part')
        changed[ident]=entry['sha256'];after[ident]=mesh.triangles
    def bounds(scene):
        return {k:(v.min(axis=(0,1)),v.max(axis=(0,1))) for k,v in scene.items()}
    old_bounds,new_bounds=bounds(before),bounds(after)
    def separated(b,a,c):
        low,high=b[a];other_low,other_high=b[c]
        return bool(np.any(low>other_high+1e-8) or np.any(other_low>high+1e-8))
    def check(scene,bounds,a,b):
        if separated(bounds,a,b):
            return dict(status='BOUNDS_SEPARATED',complete=True,contact_pairs=[],checked_pairs=0)
        return inspect_pair_contact(scene[a],scene[b],tolerance_mm=1e-8)
    rows=[];separated_pairs=[];affected=0
    for a,b in itertools.combinations(sorted(parts),2):
        if a not in changed and b not in changed:continue
        affected+=1
        if separated(old_bounds,a,b) and separated(new_bounds,a,b):
            separated_pairs.append([a,b]);continue
        old=check(before,old_bounds,a,b);new=check(after,new_bounds,a,b)
        old_set=set(map(tuple,old['contact_pairs']));new_set=set(map(tuple,new['contact_pairs']))
        rows.append(dict(parts=[a,b],both_replaced=a in changed and b in changed,
                         before=old,after=new,
                         gained_face_pairs=[list(p) for p in sorted(new_set-old_set)],
                         lost_face_pairs=[list(p) for p in sorted(old_set-new_set)]))
        print(json.dumps(dict(parts=[a,b],before=len(old_set),after=len(new_set),
                             gained=len(new_set-old_set),lost=len(old_set-new_set))),flush=True)
    summary=dict(arterial_parts=len(parts),replacement_parts=len(changed),affected_pairs=affected,
                 bounds_separated_before_and_after=len(separated_pairs),detailed_pairs=len(rows),
                 all_coverage_complete=all(r[s]['complete'] for r in rows for s in ('before','after')),
                 gained_face_pairs=sum(len(r['gained_face_pairs']) for r in rows),
                 lost_face_pairs=sum(len(r['lost_face_pairs']) for r in rows),
                 contacting_relations_before=sum(bool(r['before']['contact_pairs']) for r in rows),
                 contacting_relations_after=sum(bool(r['after']['contact_pairs']) for r in rows),
                 detailed_both_replaced_pairs=sum(r['both_replaced'] for r in rows))
    report=dict(scope='All unordered artery pairs affected by simultaneous eight-part replacement',
                input_candidate_report_sha256=hashlib.sha256(raw).hexdigest(),
                atlas_archive_sha256=atlas.metadata['sha256'],replacement_sha256=changed,
                summary=summary,bounds_separated_pairs=separated_pairs,rows=rows,
                volume_containment='NOT RUN',anatomical_junction_acceptance='NOT RUN',
                original_modified=False)
    (root/'docs/evidence/protected-cerebral-scene.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(summary),flush=True)


if __name__=='__main__':
    main()
