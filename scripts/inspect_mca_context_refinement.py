"""Refine only unresolved context pairs with full triangle coverage accounting."""
import hashlib
import json
from pathlib import Path
import numpy as np
from vv_toolbox.case_io import load_case
from vv_toolbox.surface_context import refine_profile_separation

ROOT=Path(__file__).resolve().parents[1]


def main():
    evidence_path=ROOT/'docs/evidence/regularized-mca-sac.json'
    evidence_raw=evidence_path.read_bytes()
    evidence=json.loads(evidence_raw)
    case,revision=load_case(ROOT/'exports/mca-profile-regularization/case.snapshot.json')
    path=ROOT/'exports/regularized-mca-sac/surface.npz'
    raw=path.read_bytes()
    if evidence['case_revision']!=revision or hashlib.sha256(raw).hexdigest()!=evidence['artifact_sha256']:
        raise ValueError('input evidence mismatch')
    with np.load(path,allow_pickle=False) as data:
        vertices,faces=data['vertices_mm'],data['faces']
    edges={e['id']:e for e in case['edges']}
    rows=[]
    for old in evidence['context_inspection']['results']:
        if old['status']!='UNKNOWN':
            continue
        edge=edges[old['edge_id']]
        result=refine_profile_separation(vertices,faces,edge['centerline_mm'],edge['radii_mm'],
                                        max_depth=8,max_cells=100000)
        rows.append(dict(edge_id=edge['id'],previous_status='UNKNOWN',**result))
    report=dict(case_revision=revision,artifact_sha256=evidence['artifact_sha256'],
        evidence_sha256=hashlib.sha256(evidence_raw).hexdigest(),results=rows,
        other_pair_verdicts_unchanged=True,app_applied=False,
        scope='all triangles of previously unresolved pairs versus enclosing profile capsules',
        original_mesh_collision='NOT RUN')
    if raw!=path.read_bytes() or evidence_raw!=evidence_path.read_bytes():
        raise ValueError('inspection input changed')
    (ROOT/'docs/evidence/mca-context-refinement.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))


if __name__=='__main__':
    main()
