"""Frozen 0.8/1.2 central-interval engineering probes; not disease presets."""
import hashlib
import io
import json
from pathlib import Path

import numpy as np
import trimesh

from vv_toolbox.profile_scale import scale_profile_interval
from vv_toolbox.profile_loft import loft_source_profiles
from vv_toolbox.mesh_self_contact import inspect_self_contact


def main():
    root = Path(__file__).resolve().parents[1]
    raw = (root / 'docs/evidence/cerebral-smoothed-section-profiles-window2mm.json').read_bytes()
    index = json.loads(raw)
    rows = []
    for entry in index['rows']:
        data = (root / entry['artifact']).read_bytes()
        if hashlib.sha256(data).hexdigest() != entry['sha256']:
            raise ValueError('Profile identity mismatch')
        source = json.loads(data)
        if source['source_case_revision'] != entry['case_revision']:
            raise ValueError('Case revision mismatch')
        profiles = source['profiles']
        origins = np.array([p['origin_mm'] for p in profiles])
        length = float(np.linalg.norm(np.diff(origins, axis=0), axis=1).sum())
        baseline, _ = loft_source_profiles(profiles, samples=64)
        for factor in (.8, 1.2):
            edited = scale_profile_interval(
                profiles, start_mm=.25 * length, end_mm=.75 * length,
                factor=factor, protected_indices=[profiles[0]['index'], profiles[-1]['index']])
            mesh, metadata = loft_source_profiles(edited['profiles'], samples=64)
            payload = mesh.export(file_type='ply')
            digest = hashlib.sha256(payload).hexdigest()
            path = root / 'exports/profile-interval-edits' / digest / 'surface.ply'
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.exists() and path.read_bytes() != payload:
                raise ValueError('Existing artifact mismatch')
            path.write_bytes(payload)
            stored = trimesh.load(io.BytesIO(payload), file_type='ply', process=False)
            # Compare at the same serialization precision.
            original = trimesh.load(io.BytesIO(baseline.export(file_type='ply')),
                                    file_type='ply', process=False)
            fixed = np.repeat(np.asarray(edited['scales']) == 1, 64)
            unchanged = np.array_equal(stored.vertices[fixed], original.vertices[fixed])
            topology = np.array_equal(stored.faces, original.faces)
            check = inspect_self_contact(stored.vertices, stored.faces,
                                         tolerance_mm=1e-8, max_pairs=2_000_000)
            row = dict(edge_id=entry['edge_id'], factor=factor,
                       profile_sha256=entry['sha256'], case_revision=entry['case_revision'],
                       start_mm=edited['start_mm'], end_mm=edited['end_mm'],
                       fixed_ring_vertices_exact=unchanged, face_indices_exact=topology,
                       metadata=metadata, self_contact=check, sha256=digest,
                       artifact=path.relative_to(root).as_posix())
            rows.append(row)
            print(json.dumps(dict(edge_id=row['edge_id'], factor=factor,
                                  self_contact=check['status'], fixed_exact=unchanged)), flush=True)
    report = dict(rows=rows, profile_index_sha256=hashlib.sha256(raw).hexdigest(),
                  scope='Open interior loft central-half interval scale probes',
                  factors=[.8, 1.2], anatomical_presets=False,
                  junction_protection='Only first and last supplied section; anatomical junctions NOT RUN',
                  other_vessel_collision='NOT RUN', original_modified=False)
    (root / 'docs/evidence/profile-interval-edits.json').write_text(
        json.dumps(report, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
