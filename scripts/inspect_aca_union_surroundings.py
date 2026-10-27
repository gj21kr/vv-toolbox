"""Compare saved source-cut unions and originals against all other arteries."""
import hashlib
import json
from pathlib import Path
import numpy as np
from vv_toolbox.atlas import load_atlas
from vv_toolbox.mesh_pair_contact import inspect_pair_contact


def main():
    root=Path(__file__).resolve().parents[1]
    prior=json.loads((root/'docs/evidence/aca-source-cut-sac-unions.json').read_text())
    atlas=load_atlas()
    if atlas.metadata['sha256']!=prior['atlas_archive_sha256']:raise ValueError('Atlas identity mismatch')
    parts={p['id']:p for p in atlas.meshes if p['layer']=='arterial'}
    rows=[]
    for item in prior['rows']:
        if item['status']!='CANDIDATE':raise ValueError('Expected both completed candidates')
        path=root/item['artifact']
        if hashlib.sha256(path.read_bytes()).hexdigest()!=item['sha256']:raise ValueError('Candidate hash mismatch')
        with np.load(path,allow_pickle=False) as data:
            v=data['vertices_mm'];f=data['faces'];meta=json.loads(str(data['metadata']))
        if meta['case_revision']!=prior['case_revision']:raise ValueError('Revision mismatch')
        parent=parts[item['parent_part_id']]
        original=np.asarray(parent['vertices'],float)[np.asarray(parent['faces'])]
        triangles=v[f];lineage=np.asarray(meta['source_face_ids'])
        low=np.minimum(triangles.min((0,1)),original.min((0,1)))
        high=np.maximum(triangles.max((0,1)),original.max((0,1)))
        separated=[];checks=[]
        for ident,part in sorted(parts.items()):
            if ident==parent['id']:continue
            other=np.asarray(part['vertices'],float)[np.asarray(part['faces'])]
            if np.any(other.min((0,1))>high+1e-8) or np.any(other.max((0,1))<low-1e-8):
                separated.append(ident);continue
            before=inspect_pair_contact(original,other)
            after=inspect_pair_contact(triangles,other)
            baseline={tuple(pair) for pair in before['contact_pairs']}
            added=[pair for pair in after['contact_pairs'] if (int(lineage[pair[0]]),pair[1]) not in baseline]
            checks.append(dict(part_id=ident,original=before,candidate=after,
                contacts_without_original_face_pair=added,
                dome_contact_pairs=[pair for pair in after['contact_pairs'] if lineage[pair[0]]<0]))
        complete=all(c['original']['complete'] and c['candidate']['complete'] for c in checks)
        added_parts=[c['part_id'] for c in checks if c['contacts_without_original_face_pair']]
        row=dict(parent_part_id=parent['id'],artifact_sha256=item['sha256'],
            compared_other_arteries=len(parts)-1,aabb_separated_parts=separated,checks=checks,
            coverage_complete=complete,parts_with_new_face_pair_contacts=added_parts,
            status='UNKNOWN' if not complete else 'NEW_CONTACTS' if added_parts else 'NO_NEW_FACE_PAIR_CONTACTS')
        rows.append(row)
        print(parent['id'],row['status'],added_parts,flush=True)
    report=dict(schema='vv-toolbox.aca-union-surroundings/1',case_revision=prior['case_revision'],
        atlas_archive_sha256=atlas.metadata['sha256'],rows=rows,
        containment='NOT RUN',branch_patency='NOT RUN',accepted_for_generation=False,
        limitation='Triangle surface contacts and source-face-pair comparison only; unchanged face pairs do not prove unchanged contact extent.')
    (root/'docs/evidence/aca-union-surroundings.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')


if __name__=='__main__':main()
