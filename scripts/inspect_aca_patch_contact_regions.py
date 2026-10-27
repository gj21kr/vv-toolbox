"""Locate recorded Atlas contacts on exact saved patch topology."""
import hashlib
import json
from pathlib import Path
import numpy as np
from vv_toolbox.atlas import load_atlas
from vv_toolbox.patch_contact_regions import classify_patch_contacts


def main():
    root=Path(__file__).resolve().parents[1]
    raw=(root/'docs/evidence/aca-patch-atlas-contact.json').read_bytes();prior=json.loads(raw)
    artifacts=json.loads((root/'docs/evidence/aca-curved-patches.json').read_text())
    atlas=load_atlas()
    if atlas.metadata['sha256']!=prior['atlas_archive_sha256']:raise ValueError('Atlas changed')
    names={p['id']:p['name'] for p in atlas.meshes}
    rows=[]
    for row in prior['rows']:
        artifact=next(r for r in artifacts['attempts'] if r['junction_id']==row['junction_id'])
        path=root/artifact['artifact']
        if hashlib.sha256(path.read_bytes()).hexdigest()!=row['artifact_sha256']:raise ValueError('Patch changed')
        with np.load(path,allow_pickle=False) as data:faces=data['faces']
        regions=[]
        for pair in row['tested_pairs']:
            if not pair['inspection']['contact_pairs']:continue
            classified=classify_patch_contacts(faces,pair['inspection']['contact_pairs'])
            regions.append(dict(part_id=pair['part_id'],source_name=names[pair['part_id']],classification=classified))
            print(json.dumps(dict(junction=row['junction_id'],part=pair['part_id'],name=names[pair['part_id']],
                interior_faces=len(classified['interior_face_ids']),boundary_faces=len(classified['boundary_incident_face_ids']))),flush=True)
        rows.append(dict(junction_id=row['junction_id'],artifact_sha256=row['artifact_sha256'],contacts=regions))
    report=dict(schema='vv-toolbox.aca-patch-contact-regions/1',case_revision=prior['case_revision'],
        contact_report_sha256=hashlib.sha256(raw).hexdigest(),rows=rows,
        scope='Recorded intersecting faces classified by exact open boundary topology; source names copied from atlas',
        accepted_for_generation=False,app_applied=False)
    (root/'docs/evidence/aca-patch-contact-regions.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')


if __name__=='__main__':main()
