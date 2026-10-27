"""Locate changed triangle contacts without declaring anatomical acceptance."""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

import numpy as np

from vv_toolbox.atlas import load_atlas


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--edit', choices=('radius', 'bend'), default='radius')
    args = parser.parse_args()
    root = Path('docs/evidence')
    read = lambda name: json.loads((root/name).read_text())
    context_path = root/('access-radius-context.json' if args.edit == 'radius' else 'access-bend-context.json')
    context_bytes = context_path.read_bytes()
    context = json.loads(context_bytes)
    edit_name = 'access-radius-edit.json' if args.edit == 'radius' else 'access-shape-edit-bend.json'
    edit = read(edit_name)
    if args.edit == 'bend':
        if context['edit_report_sha256'] != hashlib.sha256((root/edit_name).read_bytes()).hexdigest():
            raise ValueError('Bend contact input report mismatch')
        edit = dict(edit, output_sha256=hashlib.sha256(Path(edit['artifact']).read_bytes()).hexdigest())
    parent = read('resampled-access-protected.json')
    union = read('resampled-access-union.json')
    if (context['after_sha256'] != edit['output_sha256']
            or context['before_sha256'] != parent['output_sha256']
            or parent['parent_sha256'] != union['output_sha256']):
        raise ValueError('Contact localization ancestry mismatch')
    meshes = []
    for record in (parent, edit):
        path = Path(record['artifact'])
        if hashlib.sha256(path.read_bytes()).hexdigest() != record['output_sha256']:
            raise ValueError('Contact surface mismatch')
        with np.load(path, allow_pickle=False) as data:
            meshes.append((data['vertices'].copy(), data['faces'].copy()))
    (old, faces), (new, new_faces) = meshes
    if not np.array_equal(faces, new_faces):
        raise ValueError('Contact pair comparison requires unchanged topology')
    lineage = union['face_lineage']
    owners = np.asarray(lineage['face_source_indices'])
    if len(owners) != len(faces):
        raise ValueError('Face ownership coverage mismatch')
    atlas = load_atlas()
    parts = {p['id']:p for p in atlas.meshes}
    report = dict(status='PARTIAL' if context['status']=='RUNNING' else 'MEASURED',
                  context_status=context['status'], context_completed=context['completed'],
                  context_total=context['neighbor_count'],
                  context_report_sha256=hashlib.sha256(context_bytes).hexdigest(),
                  before_sha256=parent['output_sha256'], after_sha256=edit['output_sha256'],
                  anatomical_contact_classification='UNKNOWN', rows=[])
    for row in context['rows']:
        if not row['added_contact_pairs'] and not row['removed_contact_pairs']:
            continue
        neighbor = parts.get(row['neighbor_id'], {})
        result = dict(neighbor_id=row['neighbor_id'], name=neighbor.get('name'), layer=neighbor.get('layer'),
                      before_status=row['before']['status'], after_status=row['after']['status'])
        for kind in ('added', 'removed'):
            pairs = row[kind+'_contact_pairs']
            ids = np.unique([p[0] for p in pairs]).astype(int)
            vertices = np.unique(faces[ids])
            coordinates = (new if kind=='added' else old)[vertices]
            result[kind] = dict(pairs=len(pairs), union_faces=ids.tolist(),
                owner_counts=dict(Counter(lineage['source_names'][owners[i]] for i in ids)),
                bounds_lps_mm=[coordinates.min(axis=0).tolist(),coordinates.max(axis=0).tolist()] if len(vertices) else None,
                maximum_vertex_displacement_mm=float(np.linalg.norm(new[vertices]-old[vertices],axis=1).max()) if len(vertices) else 0.)
        report['rows'].append(result)
    name = 'access-radius-contact-locations.json' if args.edit == 'radius' else 'access-bend-contact-locations.json'
    (root/name).write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(status=report['status'], changed_neighbors=len(report['rows']),
                          neighbors=[dict(id=r['neighbor_id'],name=r['name'],layer=r['layer']) for r in report['rows']])),flush=True)


if __name__=='__main__':
    main()
