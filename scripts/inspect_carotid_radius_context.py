"""Inspect fixed radius candidates against the complete original vascular context."""
import hashlib
import argparse
import json
import time
from pathlib import Path

import numpy as np
import trimesh

from vv_toolbox.atlas import load_atlas
from vv_toolbox.atlas_neck import build_neck_repairs
from vv_toolbox.radius_context import inspect_radius_context


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',default='docs/evidence/carotid-radius-context.json')
    args=parser.parse_args()
    started=time.perf_counter()
    atlas = load_atlas()
    neck, _ = build_neck_repairs(atlas)
    context = {p['id']:trimesh.Trimesh(p['vertices'], p['faces'], process=False)
               for p in [*atlas.meshes, *neck]
               if p['layer'] in ('arterial', 'systemic_venous', 'hepatic_portal')}
    lineage = json.loads(Path('docs/evidence/carotid-solid-union-diagnostic-float64-lineage.json').read_text())
    sources = {r['part_id']:r['face_lineage']['source_names'] for r in lineage['rows']}
    edits = json.loads(Path('docs/evidence/carotid-radius-candidates.json').read_text())
    reports = []
    for row in edits['rows']:
        pid = row['part_id']
        meshes = []
        for folder, hash_key in [('carotid-solid-union-diagnostic-float64-lineage', 'input_sha256'),
                                 ('carotid-radius-candidates', 'output_sha256')]:
            path = Path('exports')/folder/(pid+'.npz')
            if hashlib.sha256(path.read_bytes()).hexdigest() != row[hash_key]:
                raise ValueError('Candidate file identity mismatch')
            with np.load(path, allow_pickle=False) as data:
                meshes.append(trimesh.Trimesh(data['vertices'], data['faces'], process=False))
        neighbors = {name:mesh for name, mesh in context.items() if name not in sources[pid]}
        result = inspect_radius_context(*meshes, neighbors)
        reports.append(dict(part_id=pid, input_sha256=row['input_sha256'],
                            output_sha256=row['output_sha256'], neighbor_count=len(neighbors), **result))
        print(json.dumps(dict(part_id=pid, status=result['status'], neighbors=len(neighbors),
                              new=result['new_or_extended_contacts'], unknown=result['unknown'])), flush=True)
    Path(args.output).write_text(json.dumps(dict(
        rows=reports, context='Original atlas vascular surfaces and existing estimated neck connectors',
        other_side='Unedited original context; not simultaneous bilateral replacement',
        elapsed_seconds=time.perf_counter()-started,live_scene_changed=False), indent=2)+'\n')


if __name__ == '__main__':
    main()
