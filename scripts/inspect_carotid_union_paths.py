"""Check complete declared bridge polylines inside validated union candidates."""
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh

from vv_toolbox.case_io import load_case
from vv_toolbox.centerline_containment import inspect_centerline_containment


def main():
    report=json.loads(Path('docs/evidence/carotid-solid-union-diagnostic-float64.json').read_text())
    record=json.loads(Path('docs/evidence/atlas-neck-volume-case.json').read_text())
    case,revision=load_case(record['derived_case_file'])
    if revision!=report['source_case_revision']:
        raise ValueError('Source case identity mismatch')
    metadata=case['inspection']['atlas_scene_capture']['estimated_metadata']
    results=[]
    for row in report['rows']:
        pid=row['part_id']
        if row['status']!='CANDIDATE':
            results.append(dict(part_id=pid,status='NOT RUN',reason='Union candidate unavailable'))
            continue
        path=Path('exports/carotid-solid-union-diagnostic-float64')/(pid+'.npz')
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        with np.load(path,allow_pickle=False) as data:
            mesh=trimesh.Trimesh(data['vertices'],data['faces'],process=False)
        # Keep the declared original Hermite centerline as an independent path;
        # do not fit a new path merely to the output surface.
        points=np.asarray(metadata[pid]['centerline'])
        result=inspect_centerline_containment(mesh,points)
        results.append(dict(part_id=pid,union_file_sha256=digest,**result))
        print(json.dumps(dict(part_id=pid,status=result['status'],
                              segments=result['segment_count'],
                              outside=len(result['outside_witnesses']),
                              unresolved=len(result['unresolved_segments']))),flush=True)
    Path('docs/evidence/carotid-union-paths.json').write_text(json.dumps(dict(
        source_case_revision=revision,rows=results,
        scope='Declared neck bridge polyline intervals only; not all femoral-cerebral routes',
        live_scene_changed=False),indent=2)+'\n')


if __name__=='__main__':
    main()
