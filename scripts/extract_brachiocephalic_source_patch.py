"""Preserve the complete union-owned BCT/RCCA/RSA surface region for review."""
import hashlib
import json
from pathlib import Path

import numpy as np

from vv_toolbox.source_patch import extract_source_patch


def main():
    evidence = Path('docs/evidence')
    record = json.loads((evidence/'femoral-anterior-union.json').read_text())
    source = Path('exports/femoral-anterior-union/candidate.npz')
    if hashlib.sha256(source.read_bytes()).hexdigest() != record['output_sha256']:
        raise ValueError('Union identity mismatch')
    lineage = record['face_lineage']
    names = ['FJ3417', 'FJ3564', 'FJ3579']
    owners = np.asarray(lineage['face_source_indices'])
    selected = np.flatnonzero(np.isin(owners, [lineage['source_names'].index(n) for n in names]))
    with np.load(source, allow_pickle=False) as data:
        patch = extract_source_patch(data['vertices'], data['faces'], selected)
    folder = Path('exports/brachiocephalic-source-patch')
    folder.mkdir(parents=True, exist_ok=True)
    target = folder/'candidate.npz'
    np.savez_compressed(target, **{key: patch[key] for key in
        ('vertices','faces','source_vertex_ids','source_face_ids')})
    report = dict(**patch['report'], source_surface_sha256=record['output_sha256'],
        source_case_revision=record['source_case_revision'], selected_owners=names,
        source_face_counts={n:int(np.sum(owners[selected]==lineage['source_names'].index(n))) for n in names},
        artifact=str(target), artifact_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
        live_scene_changed=False, replacement_applied=False,
        scope='Exact subset of existing union; protected branch surface, not new smoothing or fused replacement')
    (evidence/'brachiocephalic-source-patch.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k: report[k] for k in ('faces','vertices','components','boundary_topology','source_face_counts')}))


if __name__ == '__main__':
    main()
