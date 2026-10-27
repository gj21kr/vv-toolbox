"""Inspect original index topology without capping or moving source triangles."""
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh

from vv_toolbox.atlas import load_atlas

ROOT=Path(__file__).resolve().parents[1]
PARTS=['FJ1654','FJ1654M','FJ1660','FJ1660M','FJ1692','FJ1692M','FJ1694','FJ1694M']


def triangle_hash(vertices,faces):
    return hashlib.sha256(np.asarray(vertices[faces],dtype='<f8').tobytes()).hexdigest()


def inspect(vertices,faces):
    mesh=trimesh.Trimesh(vertices,faces,process=False)
    edges,counts=np.unique(mesh.edges_sorted,axis=0,return_counts=True)
    boundary=edges[counts==1]
    adjacency={}
    for first,last in boundary:
        adjacency.setdefault(int(first),set()).add(int(last))
        adjacency.setdefault(int(last),set()).add(int(first))
    pending=set(adjacency);components=[]
    while pending:
        todo=[min(pending)];found=set()
        while todo:
            current=todo.pop()
            if current in found:continue
            found.add(current);todo.extend(adjacency[current]-found)
        pending-=found
        points=vertices[sorted(found)]
        component_edges=np.asarray([edge for edge in boundary if int(edge[0]) in found])
        components.append(dict(vertex_count=len(found),edge_count=len(component_edges),
            simple_closed_loop=all(len(adjacency[i])==2 for i in found),
            vertex_degree_counts={str(n):sum(len(adjacency[i])==n for i in found)
                                  for n in sorted({len(adjacency[i]) for i in found})},
            centroid_mm=points.mean(0).tolist(),bounds_mm=[points.min(0).tolist(),points.max(0).tolist()],
            perimeter_mm=float(np.linalg.norm(vertices[component_edges[:,0]]-vertices[component_edges[:,1]],axis=1).sum())))
    unique,inverse=np.unique(vertices,axis=0,return_inverse=True)
    remapped=inverse[faces]
    welded=trimesh.Trimesh(unique,remapped,process=False)
    _,face_counts=np.unique(np.sort(faces,axis=1),axis=0,return_counts=True)
    return dict(vertices=len(vertices),faces=len(faces),watertight=bool(mesh.is_watertight),
        winding_consistent=bool(mesh.is_winding_consistent),
        boundary_edges=int(sum(counts==1)),nonmanifold_edges=int(sum(counts>2)),
        maximum_edge_incidence=int(max(counts)),boundary_components=components,
        duplicate_face_excess=int(sum(face_counts-1)),
        zero_area_faces=int(sum(mesh.area_faces<=1e-12)),
        exact_vertex_merge_diagnostic=dict(duplicate_vertex_excess=len(vertices)-len(unique),
            watertight=bool(welded.is_watertight),
            winding_consistent=bool(welded.is_winding_consistent),
            triangle_positions_unchanged=triangle_hash(vertices,faces)==triangle_hash(unique,remapped)),
        triangle_sha256=triangle_hash(vertices,faces))


def main():
    atlas=load_atlas()
    by_id={p['id']:p for p in atlas.meshes}
    rows=[]
    for ident in PARTS:
        part=by_id[ident]
        row=dict(part_id=ident,**inspect(np.asarray(part['vertices']),np.asarray(part['faces'])))
        rows.append(row)
        print(json.dumps({k:row[k] for k in ('part_id','watertight','boundary_edges','nonmanifold_edges','exact_vertex_merge_diagnostic')}))
    report=dict(scope='Original triangle/index topology; no anatomical opening classification',
        atlas_sha256=atlas.metadata['sha256'],source_modified=False,capping_performed=False,rows=rows)
    (ROOT/'docs/evidence/cerebral-source-surface-topology.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':
    main()
