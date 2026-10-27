"""Locate retained contacts in unchanged versus deformed union triangles."""
import hashlib
import json
from pathlib import Path

import numpy as np


def main():
    inspection = json.loads(Path('docs/evidence/carotid-radius-context.json').read_text())
    lineage = json.loads(Path('docs/evidence/carotid-solid-union-diagnostic-float64-lineage.json').read_text())
    owners = {row['part_id']:row['face_lineage'] for row in lineage['rows']}
    rows = []
    for candidate in inspection['rows']:
        pid = candidate['part_id']
        meshes = []
        for folder, key in [('carotid-solid-union-diagnostic-float64-lineage','input_sha256'),
                            ('carotid-radius-candidates','output_sha256')]:
            path = Path('exports')/folder/(pid+'.npz')
            if hashlib.sha256(path.read_bytes()).hexdigest() != candidate[key]:
                raise ValueError('Contact evidence geometry changed')
            with np.load(path, allow_pickle=False) as data:
                meshes.append((data['vertices'].copy(), data['faces'].copy()))
        (before, faces), (after, after_faces) = meshes
        if not np.array_equal(faces, after_faces):
            raise ValueError('Topology changed')
        changed = np.any(before[faces] != after[faces], axis=(1,2))
        ownership = owners[pid]
        for pair in candidate['rows']:
            contacts = pair['after']['contact_pairs']
            if not contacts:
                continue
            ids = np.unique(np.asarray(contacts)[:,0])
            source_ids = np.asarray(ownership['face_source_indices'])[ids]
            counts = {name:int((source_ids==index).sum())
                      for index,name in enumerate(ownership['source_names']) if np.any(source_ids==index)}
            rows.append(dict(part_id=pid, neighbor_id=pair['neighbor_id'],
                contacting_union_faces=len(ids), source_face_counts=counts,
                changed_contacting_union_faces=int(changed[ids].sum()),
                added_contact_pairs=len(pair['added_contact_pairs']),
                removed_contact_pairs=len(pair['removed_contact_pairs'])))
    Path('docs/evidence/radius-retained-contact-locations.json').write_text(json.dumps(dict(
        rows=rows, source='carotid-radius-context.json',
        scope='Exact triangle-coordinate comparison and source ownership; not junction approval',
        source_junction_union='NOT RUN', clearance_status='NOT GRANTED'), indent=2)+'\n')
    print(json.dumps(dict(neighbor_pairs=len(rows),
        changed_contacting_faces=sum(r['changed_contacting_union_faces'] for r in rows))))


if __name__ == '__main__':
    main()
