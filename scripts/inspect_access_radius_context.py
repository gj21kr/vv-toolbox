"""Compare the fixed-topology femoral edit against the full frozen context."""
import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np
import trimesh

from vv_toolbox.atlas import load_atlas
from vv_toolbox.atlas_neck import build_neck_repairs
from vv_toolbox.radius_context import inspect_radius_context


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--edit', choices=('radius', 'bend'), default='radius')
    args = parser.parse_args()
    root = Path('docs/evidence')
    read = lambda name: json.loads((root / name).read_text())
    before = read('resampled-access-protected.json')
    report_name = 'access-radius-edit.json' if args.edit == 'radius' else 'access-shape-edit-bend.json'
    after = read(report_name)
    input_report_sha256 = hashlib.sha256((root/report_name).read_bytes()).hexdigest()
    if args.edit == 'bend':
        if after['status'] != 'CANDIDATE' or after['parameters']['twist_deg'] != 0:
            raise ValueError('Completed fixed bend candidate required')
        after = dict(after, source_case_revision=before['source_case_revision'],
                     output_sha256=hashlib.sha256(Path(after['artifact']).read_bytes()).hexdigest(),
                     radius_edit=dict(self_contact=after['audit']['self_contact'], faces_unchanged=True))
    baseline = read('resampled-access-context.json')
    if (after['parent_surface_sha256'] != before['output_sha256']
            or after['source_case_revision'] != before['source_case_revision']
            or baseline['candidate_sha256'] != before['output_sha256']
            or baseline['completed'] != baseline['neighbor_count']
            or after['radius_edit']['self_contact']['status'] != 'NO_CONTACT_DETECTED'
            or not after['radius_edit']['faces_unchanged']):
        raise ValueError('Edit/context identity mismatch')

    def load(record):
        path = Path(record['artifact'])
        if hashlib.sha256(path.read_bytes()).hexdigest() != record['output_sha256']:
            raise ValueError('Surface artifact mismatch')
        with np.load(path, allow_pickle=False) as data:
            return trimesh.Trimesh(data['vertices'], data['faces'], process=False)

    old, new = load(before), load(after)
    if args.edit == 'bend':
        if not np.array_equal(old.faces, new.faces) or old.vertices.shape != new.vertices.shape:
            raise ValueError('Bend topology mismatch')
        measured = float(np.linalg.norm(new.vertices-old.vertices, axis=1).max())
        if not np.isclose(measured, after['audit']['displacement_measurements']['surface_maximum_mm'], rtol=0, atol=1e-12):
            raise ValueError('Bend artifact displacement differs from report')
    atlas = load_atlas()
    neck, _ = build_neck_repairs(atlas)
    neighbors = {p['id']: trimesh.Trimesh(p['vertices'], p['faces'], process=False)
                 for p in [*atlas.meshes, *neck]
                 if p['id'] not in baseline['excluded_union_sources']
                 and p['layer'] in ('arterial', 'systemic_venous', 'hepatic_portal')}
    digest = hashlib.sha256()
    for name, mesh in sorted(neighbors.items()):
        encoded = name.encode('utf-8')
        digest.update(len(encoded).to_bytes(8, 'little'))
        digest.update(encoded)
        for array in (np.asarray(mesh.vertices, dtype='<f8'), np.asarray(mesh.faces, dtype='<i8')):
            digest.update(str(array.shape).encode('ascii'))
            digest.update(array.tobytes())
    if len(neighbors) != baseline['neighbor_count'] or digest.hexdigest() != baseline['context_sha256']:
        raise ValueError('Frozen context mismatch')
    started = time.perf_counter()
    report = dict(status='RUNNING', before_sha256=before['output_sha256'],
                  after_sha256=after['output_sha256'], context_sha256=digest.hexdigest(),
                  source_case_revision=before['source_case_revision'],
                  edit_kind=args.edit, edit_report_sha256=input_report_sha256,
                  neighbor_count=len(neighbors), completed=0, rows=[], live_scene_changed=False)
    target = root / ('access-radius-context.json' if args.edit == 'radius' else 'access-bend-context.json')

    def save():
        report['elapsed_seconds'] = time.perf_counter() - started
        temp = target.with_suffix('.json.tmp')
        temp.write_text(json.dumps(report, indent=2) + '\n')
        temp.replace(target)

    def progress(event):
        report['rows'].append(event['row'])
        report['completed'] = event['completed']
        if event['completed'] % 10 == 0 or event['completed'] == event['total']:
            save()
        if event['completed'] % 100 == 0:
            print(json.dumps(dict(completed=event['completed'], total=event['total'])), flush=True)

    save()
    report.update(inspect_radius_context(old, new, neighbors, progress=progress))
    save()
    print(json.dumps(dict(status=report['status'], new_contacts=report['new_or_extended_contacts'],
                          unknown=len(report['unknown']))), flush=True)


if __name__ == '__main__':
    main()
