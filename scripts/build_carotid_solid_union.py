"""Join each source carotid pair through a separate estimated contour bridge."""
import json
import argparse
from pathlib import Path

import numpy as np
import trimesh

from vv_toolbox.case_io import load_case
from vv_toolbox.estimated_tube_volume import cap_estimated_neck
from vv_toolbox.solid_union import build_solid_union


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--diagnostics',action='store_true')
    parser.add_argument('--float64',action='store_true')
    parser.add_argument('--lineage',action='store_true')
    args=parser.parse_args()
    suffix='-diagnostic' if args.diagnostics else ''
    if args.float64:suffix+='-float64'
    if args.lineage:
        if not args.float64:parser.error('--lineage requires --float64')
        suffix+='-lineage'
    record=json.loads(Path('docs/evidence/atlas-neck-volume-case.json').read_text())
    case,revision=load_case(record['derived_case_file'])
    parts={p['part_id']:p for p in case['surface_parts']}
    metadata=case['inspection']['atlas_scene_capture']['estimated_metadata']
    folder=Path('exports/carotid-solid-union'+suffix);folder.mkdir(parents=True,exist_ok=True)
    rows=[]
    for pid in sorted(metadata):
        if 'carotid' not in pid:continue
        diagnostics={}
        def capture(mesh,details):
            diagnostics.update(details)
            np.savez_compressed(folder/(pid+'-unaccepted.npz'),vertices=mesh.vertices,faces=mesh.faces)
        try:
            with np.load(Path('exports/neck-contour-candidates-corners')/(pid+'.npz'),allow_pickle=False) as data:
                closed=cap_estimated_neck(dict(vertices=data['vertices'],faces=data['faces'],
                    metadata=dict(kind='estimated-neck-connector',original_atlas_geometry=False)),
                    max_planarity_mm=.001,cap_method='planar-earcut')
            meshes={pid:trimesh.Trimesh(closed['vertices'],closed['faces'],process=False)}
            for target in metadata[pid]['source_endpoint_ids']:
                p=parts[target]
                meshes[target]=trimesh.Trimesh(p['vertices_mm'],p['faces'],process=False)
            merged,report=build_solid_union(meshes,diagnostic_callback=capture if args.diagnostics else None,
                                           precision='float64' if args.float64 else 'float32')
            np.savez_compressed(folder/(pid+'.npz'),vertices=merged.vertices,faces=merged.faces)
            rows.append(dict(part_id=pid,**report))
        except ValueError as error:
            rows.append(dict(part_id=pid,status='FAIL',reason=str(error)))
        if args.diagnostics:
            rows[-1]['diagnostics']=diagnostics
        print(json.dumps({k:v for k,v in rows[-1].items() if k not in ('diagnostics','input_surfaces','self_contact','face_lineage')} |
                         {'diagnostics':{k:v for k,v in diagnostics.items() if k!='input_surfaces'}}),flush=True)
    Path('docs/evidence/carotid-solid-union'+suffix+'.json').write_text(json.dumps(dict(
        source_case_revision=revision,rows=rows,live_scene_changed=False),indent=2)+'\n')


if __name__=='__main__':
    main()
