"""Screen serialized window-profile candidates against every other atlas artery."""
import hashlib
import io
import json
from pathlib import Path

import numpy as np
import trimesh

from vv_toolbox.atlas import load_atlas
from vv_toolbox.mesh_pair_contact import inspect_pair_contact


def main():
    root=Path(__file__).resolve().parents[1]
    index_raw=(root/'docs/evidence/cerebral-smoothed-profile-lofts-window2mm.json').read_bytes()
    index=json.loads(index_raw)
    profile_raw=(root/'docs/evidence/cerebral-smoothed-section-profiles-window2mm.json').read_bytes()
    if hashlib.sha256(profile_raw).hexdigest()!=index['source_profile_index_sha256']:
        raise ValueError('Profile index mismatch')
    profile_index=json.loads(profile_raw)
    atlas=load_atlas()
    if atlas.metadata['sha256']!=index['atlas_archive_sha256']:
        raise ValueError('Source atlas mismatch')
    arterial={p['id']:p for p in atlas.meshes if p['layer']=='arterial'}
    bounds={ident:(np.min(p['vertices'],axis=0),np.max(p['vertices'],axis=0))
            for ident,p in arterial.items()}
    tolerance=1e-8;rows=[]
    for entry in index['rows']:
        if entry['status']!='CANDIDATE':
            rows.append(dict(edge_id=entry['edge_id'],status='UNKNOWN',reason='Candidate unavailable'))
            continue
        binding=next(r for r in profile_index['rows'] if r['edge_id']==entry['edge_id'])
        profile=(root/binding['artifact']).read_bytes()
        if hashlib.sha256(profile).hexdigest()!=entry['profile_sha256']:
            raise ValueError('Profile binding mismatch')
        part_id=json.loads(profile)['source_part_id']
        part=arterial[part_id]
        data=(root/entry['artifact']).read_bytes()
        if hashlib.sha256(data).hexdigest()!=entry['sha256']:
            raise ValueError('Candidate artifact mismatch')
        mesh=trimesh.load(io.BytesIO(data),file_type='ply',process=False)
        low,high=mesh.bounds
        candidates=[];separated=[]
        for ident,(other_low,other_high) in bounds.items():
            if ident==part_id:continue
            if np.any(other_low>high+tolerance) or np.any(other_high<low-tolerance):
                separated.append(ident)
            else:candidates.append(ident)
        pairs=[]
        source_triangles=np.asarray(part['vertices'])[np.asarray(part['faces'])]
        for ident in sorted(candidates):
            other=arterial[ident]
            triangles=np.asarray(other['vertices'])[np.asarray(other['faces'])]
            result=inspect_pair_contact(mesh.triangles,triangles,tolerance_mm=tolerance)
            pair=dict(other_part_id=ident,candidate=result)
            if result['status']=='CONTACT_DETECTED':
                pair['original_pair']=inspect_pair_contact(source_triangles,triangles,tolerance_mm=tolerance)
            pairs.append(pair)
        contacts=[p for p in pairs if p['candidate']['status']=='CONTACT_DETECTED']
        complete=all(p['candidate']['complete'] for p in pairs)
        row=dict(edge_id=entry['edge_id'],source_part_id=part_id,artifact_sha256=entry['sha256'],
                 status='CONTACT_DETECTED' if contacts else 'NO_SURFACE_CONTACT_DETECTED' if complete else 'UNKNOWN',
                 coverage_complete=complete,other_arteries=len(arterial)-1,
                 aabb_separated_parts=sorted(separated),tested_pairs=pairs)
        rows.append(row)
        print(json.dumps(dict(edge_id=entry['edge_id'],status=row['status'],
                             other_arteries=len(arterial)-1,aabb_candidates=len(candidates),
                             contacting_parts=[p['other_part_id'] for p in contacts])),flush=True)
    report=dict(scope='Each serialized open candidate against all other original arterial parts',
                atlas_archive_sha256=atlas.metadata['sha256'],
                loft_index_sha256=hashlib.sha256(index_raw).hexdigest(),rows=rows,
                containment='NOT RUN',anatomical_junction_acceptance='NOT RUN',
                candidate_to_candidate='NOT RUN',original_modified=False)
    (root/'docs/evidence/cerebral-loft-surroundings-window2mm.json').write_text(
        json.dumps(report,indent=2)+'\n')


if __name__=='__main__':
    main()
