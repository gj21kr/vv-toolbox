"""Inspect original FJ1690 contact supports without approving anatomical junctions."""
import json
import hashlib
import csv
import io
import zipfile
from pathlib import Path

import numpy as np
import trimesh

from vv_toolbox.atlas import ROOT, PINNED, parse_obj, groups_from_tables
from vv_toolbox.mesh_pair_contact import inspect_pair_contact
from vv_toolbox.surface_indexing import exact_vertex_index_copy


def support(mesh, ids):
    ids=np.asarray(sorted(set(ids)),dtype=int)
    if not len(ids): return dict(face_ids=[],components=[])
    adjacency=mesh.face_adjacency
    adjacency=adjacency[np.isin(adjacency,ids).all(axis=1)]
    components=trimesh.graph.connected_components(adjacency,nodes=ids,min_len=1)
    result=[]
    for component in components:
        triangles=mesh.triangles[component]
        area=mesh.area_faces[component]
        result.append(dict(face_ids=sorted(map(int,component)),face_count=len(component),
            support_area_mm2=float(area.sum()),
            support_centroid_mm=np.average(triangles.mean(axis=1),axis=0,weights=area).tolist(),
            bounds_mm=[triangles.min(axis=(0,1)).tolist(),triangles.max(axis=(0,1)).tolist()]))
    return dict(face_ids=ids.tolist(),components=result,
        scope='Full supporting facets, not measured intersection area or an open lumen')


def main():
    root=Path(__file__).resolve().parents[1]
    ids=['FJ1690','FJ1654','FJ1655','FJ1695']
    hashes={}
    for name,expected in PINNED.items():
        path=ROOT/name
        actual=hashlib.sha256(path.read_bytes()).hexdigest()
        hashes[name]=dict(expected=expected,actual=actual,match=actual==expected)
        if actual!=expected and name!='LICENSE.html':
            raise ValueError('Diagnostic source identity mismatch: '+name)
    # Read-only geometry diagnosis records license drift explicitly. The application
    # loader and its all-file identity gate remain unchanged and are not invoked.
    tables={tree:list(csv.DictReader(io.StringIO((ROOT/f'{tree}_element_parts.txt').read_text()),delimiter='\t'))
            for tree in ('isa','partof')}
    _,labels=groups_from_tables(tables)
    parts={}
    with zipfile.ZipFile(ROOT/'isa_BP3D_4.0_obj_99.zip') as archive:
        for key in ids:
            data=archive.read(f'isa_BP3D_4.0_obj_99/{key}.obj')
            v,f=parse_obj(data)
            parts[key]=dict(id=key,name=labels[key][1],vertices=v,faces=f,
                obj_sha256=hashlib.sha256(data).hexdigest())
    if set(parts)!=set(ids): raise ValueError('Missing source parts')
    meshes={};provenance={}
    for key,part in parts.items():
        meshes[key],indexing=exact_vertex_index_copy(trimesh.Trimesh(part['vertices'],part['faces'],process=False))
        provenance[key]=dict(name=part['name'],obj_sha256=part['obj_sha256'],indexing=indexing)
    rows=[]
    for key in ids[1:]:
        a,b=meshes['FJ1690'],meshes[key]
        check=inspect_pair_contact(a.triangles,b.triangles,tolerance_mm=1e-6)
        pairs=check['contact_pairs']
        rows.append(dict(neighbor_id=key,name=parts[key]['name'],contact=check,
            frontobasal_support=support(a,[p[0] for p in pairs]),
            neighbor_support=support(b,[p[1] for p in pairs]),
            anatomical_junction_status='UNVERIFIED',open_lumen='NOT RUN'))
    report=dict(schema='vv-toolbox.frontobasal-source-contacts/1',
        atlas_archive_sha256=hashes['isa_BP3D_4.0_obj_99.zip']['actual'],file_identity=hashes,
        application_source_gate='PASS' if all(v['match'] for v in hashes.values()) else 'FAIL',
        sources=provenance,rows=rows,
        original_modified=False,accepted_for_generation=False,
        scope='Original atlas surfaces only; not partition candidates or complete arterial context',
        centerline_ostium_alignment='NOT RUN: prior local exports unavailable in current checkout')
    path=root/'docs/evidence/frontobasal-source-contacts.json'
    path.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps([dict(id=r['neighbor_id'],name=r['name'],pairs=len(r['contact']['contact_pairs']),
        complete=r['contact']['complete'],supports=r['frontobasal_support']['components']) for r in rows]))


if __name__=='__main__': main()
