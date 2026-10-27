"""Directed union-surface sampling against source and uncapped bridge surfaces."""
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh

from vv_toolbox.case_io import load_case


def main():
    accepted=json.loads(Path('docs/evidence/carotid-solid-union-diagnostic-float64.json').read_text())
    paths=json.loads(Path('docs/evidence/carotid-union-paths.json').read_text())
    identities={r['part_id']:r['union_file_sha256'] for r in paths['rows']}
    record=json.loads(Path('docs/evidence/atlas-neck-volume-case.json').read_text())
    case,revision=load_case(record['derived_case_file'])
    if revision!=accepted['source_case_revision'] or revision!=paths['source_case_revision']:
        raise ValueError('Source revision mismatch')
    parts={p['part_id']:p for p in case['surface_parts']}
    metadata=case['inspection']['atlas_scene_capture']['estimated_metadata']
    rows=[]
    for result in accepted['rows']:
        pid=result['part_id']
        if result['status']!='CANDIDATE':
            raise ValueError('Union not accepted for geometry inspection')
        path=Path('exports/carotid-solid-union-diagnostic-float64')/(pid+'.npz')
        if hashlib.sha256(path.read_bytes()).hexdigest()!=identities[pid]:
            raise ValueError('Union file changed')
        with np.load(path,allow_pickle=False) as data:
            union=trimesh.Trimesh(data['vertices'],data['faces'],process=False)
        source=[]
        for target in metadata[pid]['source_endpoint_ids']:
            part=parts[target]
            source.append(trimesh.Trimesh(part['vertices_mm'],part['faces'],process=False))
        bridge_path=Path('exports/neck-contour-candidates-corners')/(pid+'.npz')
        with np.load(bridge_path,allow_pickle=False) as data:
            source.append(trimesh.Trimesh(data['vertices'],data['faces'],process=False))
        # Deliberately omit the temporary bridge caps: an exposed cap should
        # not silently count as source fidelity.
        reference=trimesh.util.concatenate(source)
        probes=np.vstack([union.vertices,union.triangles_center])
        distances=[]
        for start in range(0,len(probes),256):
            _,distance,_=trimesh.proximity.closest_point(reference,probes[start:start+256])
            if not np.isfinite(distance).all():
                raise ValueError('Nonfinite surface distances')
            distances.extend(distance.tolist())
        distances=np.asarray(distances)
        rows.append(dict(part_id=pid,union_file_sha256=identities[pid],
            bridge_file_sha256=hashlib.sha256(bridge_path.read_bytes()).hexdigest(),
            vertices=len(union.vertices),face_centers=len(union.faces),
            samples=len(probes),maximum_distance_mm=float(distances.max()),
            mean_distance_mm=float(distances.mean()),p99_distance_mm=float(np.quantile(distances,.99)),
            samples_over_1e_minus6_mm=int((distances>1e-6).sum()),
            worst_position_mm=probes[int(distances.argmax())].tolist()))
        print(json.dumps(rows[-1]),flush=True)
    Path('docs/evidence/carotid-union-fidelity.json').write_text(json.dumps(dict(
        source_case_revision=revision,rows=rows,
        scope='All output vertices and triangle centers to source and open bridge surfaces',
        reverse_distance='NOT RUN',continuous_surface_bound='NOT RUN',
        exposed_cap_area='NOT RUN',anatomical_validation='NOT RUN',
        live_scene_changed=False),indent=2)+'\n')


if __name__=='__main__':
    main()
