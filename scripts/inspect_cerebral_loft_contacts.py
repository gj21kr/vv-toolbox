"""Inspect the actual exported smoothed profile candidates for self-contact."""
import hashlib
import argparse
import io
import json
from pathlib import Path

import trimesh

from vv_toolbox.mesh_self_contact import inspect_self_contact


def main(*, tangent_half_window_mm=None):
    root=Path(__file__).resolve().parents[1]
    source=root/'docs/evidence/cerebral-smoothed-profile-lofts.json'
    if tangent_half_window_mm is not None:
        source=source.with_stem(source.stem+f'-window{tangent_half_window_mm:g}mm')
    raw=source.read_bytes();index=json.loads(raw)
    rows=[]
    for entry in index['rows']:
        row=dict(edge_id=entry['edge_id'],status='UNKNOWN')
        if entry['status']!='CANDIDATE':
            row['reason']='No candidate artifact exists'
        else:
            data=(root/entry['artifact']).read_bytes()
            if hashlib.sha256(data).hexdigest()!=entry['sha256']:
                raise ValueError('Candidate artifact hash mismatch')
            mesh=trimesh.load(io.BytesIO(data),file_type='ply',process=False)
            if not isinstance(mesh,trimesh.Trimesh) or len(mesh.faces)!=entry['triangles']:
                raise ValueError('Candidate triangle count mismatch')
            result=inspect_self_contact(mesh.vertices,mesh.faces,
                                        tolerance_mm=1e-8,max_pairs=2_000_000)
            row.update(status=result['status'],artifact_sha256=entry['sha256'],
                       triangles=len(mesh.faces),self_contact=result)
        rows.append(row)
        print(json.dumps(dict(edge_id=row['edge_id'],status=row['status'],
                             checked_pairs=row.get('self_contact',{}).get('checked_pairs'),
                             contacts=len(row.get('self_contact',{}).get('contact_pairs',[])))),flush=True)
    report=dict(scope='Actual serialized PLY candidates, including shared-topology triangle pairs',
                source_index_sha256=hashlib.sha256(raw).hexdigest(),rows=rows,
                other_vessels='NOT RUN',anatomical_validation='NOT RUN',
                closed_surface_acceptance='NOT RUN',original_modified=False)
    output='cerebral-loft-self-contact.json'
    if tangent_half_window_mm is not None:
        output=output.replace('.json',f'-window{tangent_half_window_mm:g}mm.json')
    (root/'docs/evidence'/output).write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--tangent-window-mm',type=float)
    main(tangent_half_window_mm=parser.parse_args().tangent_window_mm)
