"""Diagnostic only: substitute declared closed estimates in a separate context."""
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh

from vv_toolbox.case_io import load_case
from vv_toolbox.radius_context import inspect_radius_context


def main():
    record = json.loads(Path('docs/evidence/atlas-neck-volume-case.json').read_text())
    parent, parent_revision = load_case('exports/atlas-case-estimates-ui/case.snapshot.json')
    closed, revision = load_case(record['derived_case_file'])
    if parent_revision != record['parent_revision'] or revision != record['derived_revision']:
        raise ValueError('Closed context case identity mismatch')
    original_parts = {p['part_id']:p for p in parent['surface_parts']}
    closed_parts = {p['part_id']:p for p in closed['surface_parts']}
    edits = json.loads(Path('docs/evidence/carotid-radius-candidates.json').read_text())
    if edits['source_case_revision'] != revision:
        raise ValueError('Edit and closed context revisions differ')
    rows = []
    for edit in edits['rows']:
        pid = edit['part_id']
        neighbor_id = pid.replace('carotid', 'vertebral')
        original, replacement = original_parts[neighbor_id], closed_parts[neighbor_id]
        if original['provenance'] != 'estimated' or replacement['provenance'] != 'estimated':
            raise ValueError('Only declared estimates can use derived caps')
        v, f = np.asarray(replacement['vertices_mm']), np.asarray(replacement['faces'])
        original_triangles = np.asarray(original['vertices_mm'])[np.asarray(original['faces'])]
        if not np.array_equal(v[f[:len(original_triangles)]], original_triangles):
            raise ValueError('Derived context changed original side triangles')
        meshes = []
        for folder, key in [('carotid-solid-union-diagnostic-float64-lineage','input_sha256'),
                            ('carotid-radius-candidates','output_sha256')]:
            path = Path('exports')/folder/(pid+'.npz')
            if hashlib.sha256(path.read_bytes()).hexdigest() != edit[key]:
                raise ValueError('Carotid candidate hash mismatch')
            with np.load(path, allow_pickle=False) as data:
                meshes.append(trimesh.Trimesh(data['vertices'], data['faces'], process=False))
        result = inspect_radius_context(*meshes, {neighbor_id:trimesh.Trimesh(v, f, process=False)})
        rows.append(dict(part_id=pid, neighbor_id=neighbor_id,
            original_side_triangles_preserved=True, added_cap_faces=len(f)-len(original_triangles),
            input_sha256=edit['input_sha256'], output_sha256=edit['output_sha256'], **result))
        print(json.dumps(dict(part_id=pid, status=result['status'],
            unknown=result['unknown'], contacts=result['remaining_contacts'])), flush=True)
    Path('docs/evidence/closed-vertebral-context-diagnostic.json').write_text(json.dumps(dict(
        parent_case_revision=parent_revision, closed_case_revision=revision, rows=rows,
        scope='Two previously unresolved neighbor pairs with separate derived closed context',
        whole_context='NOT RUN in this diagnostic', live_scene_changed=False,
        original_context_result_preserved=True), indent=2)+'\n')


if __name__ == '__main__':
    main()
