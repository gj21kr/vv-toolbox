"""Screen the new transition against all non-vertex-adjacent mesh triangles."""
import hashlib
import argparse
import io
import json
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
from vv_toolbox.triangle_contact import triangle_contacts
from vv_toolbox.adjacent_contact import overlap_beyond_shared

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--adjacent', action='store_true')
    parser.add_argument('--whole-surface', action='store_true')
    parser.add_argument('--retained-fairing', action='store_true')
    args = parser.parse_args()
    if args.whole_surface and not args.adjacent:
        parser.error('whole surface requires adjacent topology checks')
    name = 'mca-tangent-transition-constant-earcut-flips-uniform'
    if args.retained_fairing:
        name = 'mca-retained-fairing'
    source = json.loads((ROOT/'docs/evidence'/f'{name}.json').read_text())
    path = ROOT/'exports'/name/'surface.npz'
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != source['artifact_sha256']:
        raise ValueError('source hash mismatch')
    with np.load(io.BytesIO(raw), allow_pickle=False) as data:
        v, faces = data['vertices_mm'], data['faces']
        meta = json.loads(str(data['metadata'].item()))
    triangles = v[faces]
    centers = triangles.mean(axis=1)
    radii = np.linalg.norm(triangles-centers[:, None], axis=2).max(axis=1)
    lo, hi = triangles.min(axis=1), triangles.max(axis=1)
    tree = cKDTree(centers)
    patch = np.asarray(meta['face_origin_labels']) == 4
    if args.whole_surface:
        patch = np.ones(len(faces), dtype=bool)
    tolerance = 1e-8
    tested = 0
    adjacent_excluded = 0
    contacts = []
    adjacent_contacts = []
    for i in np.flatnonzero(patch):
        candidates = np.asarray(tree.query_ball_point(centers[i], radii[i]+radii.max()+tolerance), dtype=int)
        candidates = candidates[(candidates != i) & (~patch[candidates] | (candidates > i))]
        overlap = (lo[candidates] <= hi[i]+tolerance).all(axis=1) & (hi[candidates] >= lo[i]-tolerance).all(axis=1)
        candidates = candidates[overlap]
        adjacent = np.isin(faces[candidates], faces[i]).any(axis=1)
        adjacent_excluded += int(adjacent.sum())
        if args.adjacent:
            for j in candidates[adjacent]:
                shared = np.intersect1d(faces[i], faces[j])
                if len(shared) == 3 or overlap_beyond_shared(triangles[i], triangles[j], v[shared], tolerance):
                    adjacent_contacts.append([int(i), int(j)])
        candidates = candidates[~adjacent]
        if not len(candidates):
            continue
        hits = triangle_contacts(np.broadcast_to(triangles[i], (len(candidates), 3, 3)),
                                 triangles[candidates], tolerance)
        tested += len(candidates)
        contacts.extend([[int(i), int(j)] for j in candidates[hits]])
    report = dict(artifact_sha256=source['artifact_sha256'], case_revision=meta['case_revision'],
                  scope='new transition versus all non-vertex-adjacent triangles in this single vessel candidate',
                  tolerance_mm=tolerance, narrow_phase_pairs=tested,
                  adjacent_pairs_excluded=adjacent_excluded, contact_pairs=contacts,
                  status='CONTACT_DETECTED' if contacts else 'NO_CONTACT_DETECTED',
                  full_self_intersection='UNKNOWN',
                  limitations=['Shared-vertex pairs excluded; overlap beyond shared topology not checked.',
                               'Unmodified source-source pairs and other vessels not checked.',
                               'Finite precision SAT; not an exact predicate certificate.'],
                  input_unchanged=raw == path.read_bytes(), app_applied=False)
    if args.adjacent:
        report.update(scope='new transition versus all other triangles in this single vessel candidate',
                      adjacent_pairs_excluded=0, adjacent_pairs_checked=adjacent_excluded,
                      beyond_shared_contact_pairs=adjacent_contacts,
                      status='CONTACT_DETECTED' if contacts or adjacent_contacts else 'NO_CONTACT_DETECTED',
                      limitations=['Unmodified source-source pairs and other vessels not checked.',
                                   'Finite precision tests, not an exact predicate certificate.'])
    filename = 'mca-transition-adjacent-contacts.json' if args.adjacent else 'mca-transition-contacts.json'
    if args.whole_surface:
        report.update(scope='all distinct triangle pairs of this single vessel candidate',
                      full_self_intersection=report['status'],
                      limitations=['Other vessels not checked by this surface self-contact inspection.',
                                   'Finite precision tests, not an exact predicate certificate.'])
        filename = 'mca-uniform-full-surface-contacts.json'
    report['tolerance_semantics'] = (
        'Nonadjacent SAT conservatively includes near contact; adjacent test checks geometric '
        'overlap beyond shared topology with numerical tolerance, not minimum clearance.')
    report['implementation_sha256'] = {
        name: hashlib.sha256((ROOT/'src/vv_toolbox'/name).read_bytes()).hexdigest()
        for name in ('triangle_contact.py', 'adjacent_contact.py')}
    if args.retained_fairing:
        filename = filename.replace('mca-', 'mca-retained-fairing-', 1)
    (ROOT/'docs/evidence'/filename).write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k: v for k, v in report.items()
                      if k not in ('contact_pairs', 'beyond_shared_contact_pairs')}))
    print('contact_pairs', len(contacts))
    print('beyond_shared_contact_pairs', len(adjacent_contacts))


if __name__ == '__main__':
    main()
