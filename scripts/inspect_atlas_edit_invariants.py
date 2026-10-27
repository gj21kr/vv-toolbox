"""Read the unmodified local Atlas workspace and inspect a reproducible edit."""
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

from vv_toolbox.atlas import load_atlas
from vv_toolbox.atlas_modification import deform_part
from vv_toolbox.mesh_self_contact import inspect_self_contact

ROOT=Path(__file__).resolve().parents[1]


def main():
    with urlopen('http://127.0.0.1:8093/api/export',timeout=30) as response:
        raw=response.read()
    bundle=json.loads(raw)
    if bundle['schema']!='vv-toolbox.atlas-workspace/1' or bundle['modifications']:
        raise ValueError('Unmodified atlas workspace required')
    atlas=load_atlas()
    part=next(p for p in atlas.meshes if p['id']=='FJ1692')
    edges=[e for e in bundle['centerlines']['edges'] if e['part_id']==part['id']]
    parameters=dict(radius_scale=1.3,tortuosity=.3,torsion_deg=35.)
    result,_=deform_part(part,edges,parameters)
    report=dict(part_id=part['id'],parameters=parameters,
                source_archive_sha256=atlas.metadata['sha256'],
                input_export_sha256=hashlib.sha256(raw).hexdigest(),
                source_centerlines_sha256=hashlib.sha256(
                    json.dumps(edges,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
                inspection=result['edit_checks'],
                self_contact_before=inspect_self_contact(part['vertices'],part['faces']),
                self_contact_after=inspect_self_contact(result['vertices'],result['faces']),
                implementation_sha256={name:hashlib.sha256(
                    (ROOT/'src/vv_toolbox'/name).read_bytes()).hexdigest()
                    for name in ['atlas_modification.py','atlas_edit_checks.py','mesh_self_contact.py',
                                 'triangle_contact.py','adjacent_contact.py']},
                live_workspace_modified=False,
                scope='One actual Atlas MCA part with combined parameters; self-contact screened, surrounding collision and anatomy unverified')
    (ROOT/'docs/evidence/atlas-mca-edit-invariants.json').write_text(
        json.dumps(report,indent=2)+'\n')
    print(json.dumps({key:value for key,value in report.items() if key not in ('self_contact_before','self_contact_after')}))
    for key in ('self_contact_before','self_contact_after'):
        print(key,json.dumps({k:v for k,v in report[key].items() if k!='contact_pairs'}))
        print('contact count',len(report[key]['contact_pairs']))


if __name__=='__main__':
    main()
