"""Diagnose the right pericallosal source without moving any triangles."""
import json
import argparse
import hashlib
from pathlib import Path

import numpy as np
import trimesh

from vv_toolbox.case_io import load_case
from vv_toolbox.mesh_self_contact import inspect_self_contact
from vv_toolbox.surface_indexing import exact_vertex_index_copy


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--derive',action='store_true')
    args=parser.parse_args()
    record=json.loads(Path('docs/evidence/atlas-neck-volume-case.json').read_text())
    case,revision=load_case(record['derived_case_file'])
    part=next(p for p in case['surface_parts'] if p['part_id']=='FJ1699')
    mesh,indexing=exact_vertex_index_copy(trimesh.Trimesh(
        np.asarray(part['vertices_mm']),np.asarray(part['faces']),process=False))
    inspection=inspect_self_contact(mesh.vertices,mesh.faces)
    rows=[]
    for first,second in inspection['contact_pairs']:
        shared=np.intersect1d(mesh.faces[first],mesh.faces[second])
        triangles=mesh.triangles[[first,second]]
        rows.append(dict(face_ids=[first,second],shared_vertex_count=len(shared),
            triangles_mm=triangles.tolist(),triangle_support_bounds_mm=[
                triangles.min(axis=(0,1)).tolist(),triangles.max(axis=(0,1)).tolist()]))
    report=dict(part_id='FJ1699',source_case_revision=revision,
        registered_geometry_sha256=part['geometry_sha256'],indexing=indexing,
        self_contact=inspection,pairs=rows,source_modified=False,
        scope='Finite-precision source self-contact diagnosis; coordinates unchanged',
        anatomical_validation='NOT RUN')
    report_name='pericallosal-source-self-contact.json'
    if args.derive:
        from vv_toolbox.double_sheet_cleanup import remove_isolated_double_sheets
        derived,cleanup=remove_isolated_double_sheets(mesh)
        folder=Path('exports/pericallosal-derived');folder.mkdir(parents=True,exist_ok=True)
        output=folder/'FJ1699.npz'
        np.savez_compressed(output,vertices=derived.vertices,faces=derived.faces)
        report.update(cleanup=cleanup,output_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),
                      context_check='NOT RUN',live_scene_changed=False)
        report_name='pericallosal-source-cleanup.json'
    (Path('docs/evidence')/report_name).write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(status=inspection['status'],coverage=inspection['coverage'],
        pairs=len(rows),faces=len(mesh.faces),indexing_preserves_coordinates=indexing['triangle_coordinate_bytes_preserved'])),flush=True)


if __name__=='__main__':
    main()
