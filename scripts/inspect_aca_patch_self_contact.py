"""Inspect the exact saved ACA patch artifacts without regenerating them."""
import hashlib
import json
from pathlib import Path
import numpy as np
from vv_toolbox.mesh_self_contact import inspect_self_contact


def main():
    root=Path(__file__).resolve().parents[1]
    prior=json.loads((root/'docs/evidence/aca-curved-patches.json').read_text())
    rows=[]
    for item in prior['attempts']:
        path=root/item['artifact'];before=path.read_bytes()
        if hashlib.sha256(before).hexdigest()!=item['sha256']:raise ValueError('Saved patch hash mismatch')
        with np.load(path,allow_pickle=False) as archive:
            report=inspect_self_contact(archive['vertices_mm'],archive['faces'])
        if path.read_bytes()!=before:raise RuntimeError('Saved patch changed')
        rows.append(dict(junction_id=item['junction_id'],artifact=item['artifact'],sha256=item['sha256'],
                         input_unchanged=True,inspection=report))
        print(json.dumps(dict(junction_id=item['junction_id'],status=report['status'],
                             checked_pairs=report['checked_pairs'],contacts=len(report['contact_pairs']))),flush=True)
    result=dict(schema='vv-toolbox.aca-patch-self-contact/1',case_revision=prior['case_revision'],
                attempts=rows,accepted_for_generation=False,closed_lumen=False,app_applied=False)
    (root/'docs/evidence/aca-patch-self-contact.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')


if __name__=='__main__':main()
