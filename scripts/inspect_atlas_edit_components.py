"""Isolate deformation components without changing the live atlas or parameters."""
import hashlib
import argparse
import itertools
import json
from pathlib import Path
from urllib.request import urlopen

import numpy as np

from vv_toolbox.atlas import load_atlas
from vv_toolbox.atlas_modification import deform_part
from vv_toolbox.mesh_self_contact import inspect_self_contact
from inspect_atlas_edit_surroundings import boundary_angles

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--radial-mode', choices=['tangent', 'polyline'], default='tangent')
    args = parser.parse_args()
    evidence = json.loads((ROOT / 'docs/evidence/atlas-mca-protected-edit-surroundings-width8-product-v3.json').read_text())
    with urlopen('http://127.0.0.1:8093/api/export', timeout=30) as response:
        raw = response.read()
    bundle = json.loads(raw)
    if bundle['schema'] != 'vv-toolbox.atlas-workspace/1' or bundle['modifications']:
        raise ValueError('Unmodified atlas required')
    if hashlib.sha256(raw).hexdigest() != evidence['input_export_sha256']:
        raise ValueError('Export differs from comparison evidence')
    atlas = load_atlas()
    part = next(p for p in atlas.meshes if p['id'] == evidence['part_id'])
    triangles = np.asarray(part['vertices'])[part['faces']]
    fingerprint = hashlib.sha256(np.asarray(triangles, dtype='<f8').tobytes()).hexdigest()
    if fingerprint != evidence['surface_sha256']['before'] or atlas.metadata['sha256'] != evidence['archive_sha256']:
        raise ValueError('Source differs from comparison evidence')
    edges = [e for e in bundle['centerlines']['edges'] if e['part_id'] == part['id']]
    rows = []
    for protected, radius, bend, twist in itertools.product((False, True), repeat=4):
        params = dict(radius_scale=1.3 if radius else 1.,
                      tortuosity=.3 if bend else 0., torsion_deg=35. if twist else 0.)
        edited, paths = deform_part(
            part, edges, params, field_version='v3', anchor_blend='product', radial_mode=args.radial_mode,
            protected_regions=evidence['protected_regions'] if protected else ())
        contact = inspect_self_contact(edited['vertices'], edited['faces'])
        row = dict(contact_protection=protected, parameters=params,
                   self_contact=contact, basic_checks=edited['edit_checks'],
                   field_support_mm=edited['modification'].get('field_support_mm'),
                   maximum_centerline_displacement_mm=max(
                       float(np.linalg.norm(np.asarray(a['points']) - b['points'], axis=1).max())
                       for a, b in zip(paths, edges)),
                   boundary_angles=boundary_angles(part, edited))
        rows.append(row)
        print(json.dumps(dict(protected=protected, parameters=params,
                              contacts=len(contact['contact_pairs']),
                              path_movement_mm=row['maximum_centerline_displacement_mm'])), flush=True)
    report = dict(part_id=part['id'], field_version='v3', radial_mode=args.radial_mode,
                  input_export_sha256=hashlib.sha256(raw).hexdigest(),
                  archive_sha256=atlas.metadata['sha256'], source_surface_sha256=fingerprint,
                  implementation_sha256=hashlib.sha256(
                      (ROOT/'src/vv_toolbox/atlas_modification.py').read_bytes()).hexdigest(),
                  rows=rows, live_workspace_modified=False,
                  scope='Component isolation on one native MCA. Endpoint collars always active. '
                        'Surrounding-vessel intersections and volume containment NOT RUN.')
    destination = ROOT/'docs/evidence/atlas-mca-edit-component-isolation.json'
    if args.radial_mode != 'tangent':
        destination = destination.with_name(destination.stem + '-' + args.radial_mode + '.json')
    destination.write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
