"""Exact saved open patches versus every original arterial atlas surface."""
import hashlib
import json
from pathlib import Path
import numpy as np
from vv_toolbox.atlas import load_atlas
from vv_toolbox.case_io import load_case
from vv_toolbox.mesh_pair_contact import inspect_pair_contact


def main():
    root=Path(__file__).resolve().parents[1]
    case,revision=load_case(root/'exports/candidate-case-download/case.snapshot.json')
    prior=json.loads((root/'docs/evidence/aca-curved-patches.json').read_text())
    if revision!=prior['case_revision']:raise ValueError('Patch source case changed')
    atlas=load_atlas()
    if next(s['sha256'] for s in case['sources'] if s['id']=='bp3d')!=atlas.metadata['sha256']:
        raise ValueError('Atlas archive differs from source case')
    parts={p['id']:p for p in atlas.meshes if p['layer']=='arterial'}
    bounds={key:(np.min(p['vertices'],axis=0),np.max(p['vertices'],axis=0)) for key,p in parts.items()}
    rows=[];tolerance=1e-8
    for item in prior['attempts']:
        path=root/item['artifact'];before=path.read_bytes()
        if hashlib.sha256(before).hexdigest()!=item['sha256']:raise ValueError('Patch hash mismatch')
        with np.load(path,allow_pickle=False) as data:
            vertices=data['vertices_mm'];triangles=vertices[data['faces']]
            metadata=json.loads(str(data['metadata']))
        if metadata['case_revision']!=revision or metadata['frame']!=case['frame']:
            raise ValueError('Patch coordinate frame or revision mismatch')
        low,high=vertices.min(axis=0),vertices.max(axis=0)
        separated=[];pairs=[]
        for ident in sorted(parts):
            lo,hi=bounds[ident]
            if np.any(lo>high+tolerance) or np.any(hi<low-tolerance):
                separated.append(ident);continue
            part=parts[ident]
            result=inspect_pair_contact(triangles,np.asarray(part['vertices'])[np.asarray(part['faces'])],tolerance_mm=tolerance)
            pairs.append(dict(part_id=ident,inspection=result))
        contacts=[r['part_id'] for r in pairs if r['inspection']['status']=='CONTACT_DETECTED']
        complete=all(r['inspection']['complete'] for r in pairs)
        if path.read_bytes()!=before:raise RuntimeError('Patch changed during inspection')
        row=dict(junction_id=item['junction_id'],artifact_sha256=item['sha256'],input_unchanged=True,
            arterial_part_count=len(parts),aabb_separated_parts=separated,tested_pairs=pairs,
            contacting_parts=contacts,coverage_complete=complete,
            status='CONTACT_DETECTED' if contacts else 'NO_SURFACE_CONTACT_DETECTED' if complete else 'UNKNOWN')
        rows.append(row)
        print(json.dumps({k:v for k,v in row.items() if k not in ('aabb_separated_parts','tested_pairs')}),flush=True)
    report=dict(schema='vv-toolbox.aca-patch-atlas-contact/1',case_revision=revision,
        atlas_archive_sha256=atlas.metadata['sha256'],rows=rows,
        scope='Exact saved open patch against all original arterial surfaces, including its parent parts',
        containment='NOT RUN',parent_attachment_classification='UNKNOWN',closed_lumen=False,
        accepted_for_generation=False,app_applied=False)
    (root/'docs/evidence/aca-patch-atlas-contact.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')


if __name__=='__main__':main()
