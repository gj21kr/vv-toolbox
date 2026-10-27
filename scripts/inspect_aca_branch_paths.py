"""Whole-interval centerline containment for the three source parts."""
import json
from pathlib import Path
import numpy as np
import trimesh
from inspect_aca_checked_context import read_mesh
from vv_toolbox.atlas import load_atlas
from vv_toolbox.case_io import load_case
from vv_toolbox.centerline_containment import inspect_centerline_containment


def main():
    root=Path(__file__).resolve().parents[1]
    prior=json.loads((root/'docs/evidence/aca-multisurface-checked.json').read_text())
    sections=json.loads((root/'docs/evidence/aca-branch-sections.json').read_text())
    candidate=read_mesh(root,prior)
    case,revision=load_case(root/'exports/atlas-case-inspection/all-arterial.snapshot.json')
    atlas=load_atlas()
    if revision!=sections['source_case_revision'] or atlas.metadata['sha256']!=prior['atlas_archive_sha256']:
        raise ValueError('Source identity mismatch')
    if sections['artifact_sha256']!=prior['sha256']:raise ValueError('Section candidate mismatch')
    parts={p['id']:p for p in atlas.meshes};edges={e['id']:e for e in case['edges']};rows=[]
    for previous in sections['rows']:
        part=parts[previous['part_id']];edge=edges[previous['edge_id']]
        source=trimesh.Trimesh(part['vertices'],part['faces'],process=False)
        points=np.asarray(edge['centerline_mm'],float)
        before=inspect_centerline_containment(source,points)
        after=inspect_centerline_containment(candidate,points)
        row=dict(part_id=part['id'],edge_id=edge['id'],before=before,after=after)
        rows.append(row)
        print(edge['id'],before['status'],after['status'],len(before['outside_witnesses']),len(after['outside_witnesses']),flush=True)
    result=dict(schema='vv-toolbox.aca-branch-paths/1',source_case_revision=revision,
        artifact_sha256=prior['sha256'],atlas_archive_sha256=atlas.metadata['sha256'],rows=rows,
        scope='Complete source extraction polylines, including first and last segments; no points moved or cropped',
        radius_envelope='NOT RUN',anatomical_path_identity='NOT VERIFIED',accepted_for_generation=False)
    (root/'docs/evidence/aca-branch-paths.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')


if __name__=='__main__':main()
