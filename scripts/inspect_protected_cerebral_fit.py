"""Preserve complete original ends and all detected original contact faces."""
import hashlib
import io
import json
from pathlib import Path

import numpy as np
import trimesh

from vv_toolbox.atlas import load_atlas
from vv_toolbox.mesh_pair_contact import inspect_pair_contact
from vv_toolbox.mesh_self_contact import inspect_self_contact
from vv_toolbox.protected_surface_fit import fit_protected_surface
from vv_toolbox.surface_indexing import exact_vertex_index_copy


def main():
    root=Path(__file__).resolve().parents[1]
    loft_raw=(root/'docs/evidence/cerebral-smoothed-profile-lofts-window2mm.json').read_bytes()
    lofts=json.loads(loft_raw)
    profile_raw=(root/'docs/evidence/cerebral-smoothed-section-profiles-window2mm.json').read_bytes()
    if hashlib.sha256(profile_raw).hexdigest()!=lofts['source_profile_index_sha256']:
        raise ValueError('Profile index mismatch')
    profiles=json.loads(profile_raw)
    atlas=load_atlas();parts={p['id']:p for p in atlas.meshes if p['layer']=='arterial'}
    if atlas.metadata['sha256']!=lofts['atlas_archive_sha256']:raise ValueError('Atlas mismatch')
    rows=[]
    for entry in lofts['rows']:
        binding=next(r for r in profiles['rows'] if r['edge_id']==entry['edge_id'])
        raw=(root/binding['artifact']).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=entry['profile_sha256']:raise ValueError('Profile mismatch')
        profile=json.loads(raw);part=parts[profile['source_part_id']]
        source=trimesh.Trimesh(part['vertices'],part['faces'],process=False)
        target_bytes=(root/entry['artifact']).read_bytes()
        if hashlib.sha256(target_bytes).hexdigest()!=entry['sha256']:raise ValueError('Target mismatch')
        target=trimesh.load(io.BytesIO(target_bytes),file_type='ply',process=False)
        low,high=source.bounds;contacts=[];fixed_faces=set()
        for ident,other in parts.items():
            if ident==part['id']:continue
            vertices=np.asarray(other['vertices'])
            if np.any(vertices.min(axis=0)>high+1e-8) or np.any(vertices.max(axis=0)<low-1e-8):continue
            result=inspect_pair_contact(source.triangles,vertices[np.asarray(other['faces'])])
            if not result['complete']:raise ValueError('Incomplete protection context')
            if result['contact_pairs']:
                face_ids=sorted({p[0] for p in result['contact_pairs']})
                fixed_faces.update(face_ids)
                contacts.append(dict(other_part_id=ident,source_face_ids=face_ids))
        first,last=profile['profiles'][0],profile['profiles'][-1]
        v=source.vertices
        endpoint=(np.dot(v-np.asarray(first['origin_mm']),first['normal'])<=1e-8)|(
                  np.dot(v-np.asarray(last['origin_mm']),last['normal'])>=-1e-8)
        fixed=set(np.flatnonzero(endpoint).tolist())
        if fixed_faces:fixed.update(source.faces[sorted(fixed_faces)].ravel().tolist())
        row=dict(edge_id=entry['edge_id'],source_part_id=part['id'],
                 protected_contacts=contacts,protected_vertex_ids=sorted(fixed))
        try:
            candidate,metadata=fit_protected_surface(source,target,sorted(fixed),
                max_displacement_mm=.3,transition_rings=3)
        except ValueError as error:
            row.update(status='FAIL',reason=str(error))
        else:
            payload=candidate.export(file_type='ply')
            saved=trimesh.load(io.BytesIO(payload),file_type='ply',process=False)
            protected_exact=np.array_equal(saved.vertices[sorted(fixed)],source.vertices[sorted(fixed)])
            if not protected_exact:raise ValueError('Serialized protected positions differ')
            normalized,topology=exact_vertex_index_copy(saved)
            contact=inspect_self_contact(normalized.vertices,normalized.faces)
            digest=hashlib.sha256(payload).hexdigest()
            path=root/'exports/protected-cerebral-fit'/digest/'surface.ply'
            path.parent.mkdir(parents=True,exist_ok=True)
            if path.exists() and path.read_bytes()!=payload:raise ValueError('Artifact mismatch')
            path.write_bytes(payload)
            row.update(status='CANDIDATE',metadata=metadata,serialized_protected_positions_exact=True,
                       topology=topology,self_contact=contact,sha256=digest,
                       artifact=path.relative_to(root).as_posix())
        rows.append(row)
        print(json.dumps(dict(edge_id=row['edge_id'],status=row['status'],
                             moved=row.get('metadata',{}).get('moved_vertices'),
                             self_contact=row.get('self_contact',{}).get('status'),
                             reason=row.get('reason'))),flush=True)
    report=dict(source_loft_index_sha256=hashlib.sha256(loft_raw).hexdigest(),rows=rows,
                atlas_archive_sha256=atlas.metadata['sha256'],max_displacement_mm=.3,
                transition_rings=3,original_modified=False,new_surrounding_contacts='NOT RUN',
                anatomical_junction_acceptance='NOT RUN')
    (root/'docs/evidence/protected-cerebral-fit.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':
    main()
