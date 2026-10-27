"""Separate time-step and source-tessellation effects at a frozen field support."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

import numpy as np
import trimesh

from vv_toolbox.atlas import load_atlas
from vv_toolbox.atlas_modification import deform_part
from vv_toolbox.mesh_self_contact import inspect_self_contact

ROOT = Path(__file__).resolve().parents[1]


def main():
    baseline = json.loads((ROOT/'docs/evidence/atlas-mca-protected-edit-surroundings-width8-product-v3-polyline-flow32.json').read_text())
    with urlopen('http://127.0.0.1:8093/api/export', timeout=30) as response:
        raw = response.read()
    if hashlib.sha256(raw).hexdigest() != baseline['input_export_sha256']:
        raise ValueError('Export differs from frozen baseline')
    bundle = json.loads(raw)
    atlas = load_atlas()
    original = next(p for p in atlas.meshes if p['id'] == baseline['part_id'])
    digest = hashlib.sha256(np.asarray(original['vertices'][original['faces']], dtype='<f8').tobytes()).hexdigest()
    if digest != baseline['surface_sha256']['before'] or atlas.metadata['sha256'] != baseline['archive_sha256']:
        raise ValueError('Source differs from frozen baseline')
    edges = [e for e in bundle['centerlines']['edges'] if e['part_id'] == original['id']]
    support = baseline['deformation_method']['field_support_mm']
    rows = []
    reference = None
    for level, steps in ((0, 32), (0, 64), (1, 32), (2, 32)):
        part = deepcopy(original)
        for _ in range(level):
            part['vertices'], part['faces'] = trimesh.remesh.subdivide(part['vertices'], part['faces'])
        count = len(original['vertices'])
        np.testing.assert_array_equal(part['vertices'][:count], original['vertices'])
        edited, paths = deform_part(
            part, edges, baseline['parameters'], protected_regions=baseline['protected_regions'],
            anchor_blend='product', field_version='v3', radial_mode='polyline',
            integration_steps=steps, field_support_mm=support)
        if reference is None:
            reference = np.asarray(edited['vertices'][:count]).copy()
        contact = inspect_self_contact(edited['vertices'], edited['faces'])
        row = dict(subdivision_level=level, integration_steps=steps,
                   vertex_count=len(part['vertices']), face_count=len(part['faces']),
                   source_self_contact=inspect_self_contact(part['vertices'], part['faces']),
                   edited_self_contact=contact,
                   original_vertex_difference_from_flow32_mm=float(
                       np.linalg.norm(edited['vertices'][:count]-reference, axis=1).max()),
                   surface_sha256=hashlib.sha256(np.asarray(edited['vertices'][edited['faces']], dtype='<f8').tobytes()).hexdigest(),
                   basic_checks=edited['edit_checks'])
        rows.append(row)
        print(json.dumps({k:v for k,v in row.items() if k not in
                          ('basic_checks','source_self_contact','edited_self_contact')} |
                         dict(self_contact_pairs=len(contact['contact_pairs']))), flush=True)
        report = dict(part_id=original['id'], source_surface_sha256=digest,
                      input_export_sha256=hashlib.sha256(raw).hexdigest(),
                      field_support_mm=support, parameters=baseline['parameters'],
                      implementation_sha256=hashlib.sha256((ROOT/'src/vv_toolbox/atlas_modification.py').read_bytes()).hexdigest(),
                      adjacent_contact_sha256=hashlib.sha256((ROOT/'src/vv_toolbox/adjacent_contact.py').read_bytes()).hexdigest(),
                      planned_cases=4, completed_cases=len(rows), rows=rows,
                      live_workspace_modified=False,
                      scope='Same source planar surface subdivided before deformation. Surrounding surfaces and containment NOT RUN.')
        (ROOT/'docs/evidence/atlas-mca-flow-resolution-reviewed.json').write_text(json.dumps(report, indent=2)+'\n')


if __name__ == '__main__':
    main()
