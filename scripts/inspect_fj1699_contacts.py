"""Read-only source contact diagnosis with exact binary-coordinate arithmetic."""
import hashlib
import json
from fractions import Fraction as F
from pathlib import Path

import numpy as np
import trimesh

from vv_toolbox.atlas import load_atlas
from vv_toolbox.mesh_self_contact import inspect_self_contact
from vv_toolbox.surface_indexing import exact_vertex_index_copy
from vv_toolbox.radius_context import inspect_radius_context
from vv_toolbox.disjoint_containment import _SurfaceValidationCache


def sub(a,b): return [x-y for x,y in zip(a,b)]
def dot(a,b): return sum(x*y for x,y in zip(a,b))
def cross(a,b):
    return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]


def exact_shared_vertex_check(a,b,origin):
    """Exact plane intersection intervals for noncoplanar triangles sharing a point."""
    origin=list(map(F,origin))
    a=[sub(list(map(F,p)),origin) for p in a]
    b=[sub(list(map(F,p)),origin) for p in b]
    na=cross(sub(a[1],a[0]),sub(a[2],a[0]))
    nb=cross(sub(b[1],b[0]),sub(b[2],b[0]))
    axis=cross(na,nb)
    if not any(axis): return dict(status='COPLANAR_REQUIRES_SEPARATE_CHECK')
    def interval(triangle,normal):
        signed=[dot(p,normal) for p in triangle]
        points=[p for p,d in zip(triangle,signed) if d==0]
        for i,j in ((0,1),(1,2),(2,0)):
            if signed[i]*signed[j]<0:
                t=signed[i]/(signed[i]-signed[j])
                points.append([x+t*(y-x) for x,y in zip(triangle[i],triangle[j])])
        values=[dot(p,axis) for p in points]
        return min(values),max(values)
    ia,ib=interval(a,nb),interval(b,na)
    lo,hi=max(ia[0],ib[0]),min(ia[1],ib[1])
    norm=float(dot(axis,axis))**.5
    beyond=lo<=hi and (lo<0 or hi>0)
    return dict(status='OVERLAP_BEYOND_SHARED_POINT' if beyond else 'SHARED_POINT_ONLY',
        first_interval_mm=[float(x)/norm for x in ia],
        second_interval_mm=[float(x)/norm for x in ib],
        overlap_interval_mm=[float(lo)/norm,float(hi)/norm],
        method='Exact rational operations on stored binary64 coordinates; lengths converted to float for reporting')


def main():
    root=Path(__file__).resolve().parents[1]
    atlas=load_atlas()
    source=next(p for p in atlas.meshes if p['id']=='FJ1699')
    mesh,indexing=exact_vertex_index_copy(trimesh.Trimesh(source['vertices'],source['faces'],process=False))
    scans=[inspect_self_contact(mesh.vertices,mesh.faces,tolerance_mm=t) for t in (1e-10,1e-8,1e-6)]
    pairs=sorted({tuple(pair) for scan in scans for pair in scan['contact_pairs']})
    rows=[]
    for i,j in pairs:
        shared=np.intersect1d(mesh.faces[i],mesh.faces[j])
        row=dict(face_ids=[i,j],shared_vertex_ids=shared.tolist(),triangles_mm=mesh.triangles[[i,j]].tolist())
        if len(shared)==1:
            row['exact_check']=exact_shared_vertex_check(mesh.triangles[i],mesh.triangles[j],mesh.vertices[shared[0]])
        elif len(shared)==3:
            row['exact_check']=dict(status='IDENTICAL_TRIANGLE_SUPPORT',
                normal_dot=float(mesh.face_normals[i]@mesh.face_normals[j]),
                area_mm2=float(mesh.area_faces[i]),
                incident_faces=np.flatnonzero(np.isin(mesh.faces,shared).any(axis=1)).tolist())
        else:
            row['exact_check']=dict(status='NOT_RUN',reason='Diagnostic handles one shared vertex only')
        rows.append(row)
    components=trimesh.graph.connected_components(mesh.face_adjacency,nodes=np.arange(len(mesh.faces)),min_len=1)
    component_rows=[]
    for ids in components:
        part=mesh.submesh([ids],append=True,repair=False)
        component_rows.append(dict(face_count=len(ids),face_ids=ids.tolist() if len(ids)<10 else None,
            volume_mm3=float(part.volume),watertight=bool(part.is_watertight)))
    report=dict(schema='vv-toolbox.source-contact-diagnosis/1',part_id='FJ1699',name=source['name'],
        atlas_archive_sha256=atlas.metadata['sha256'],indexing=indexing,scans=scans,pairs=rows,
        components=component_rows,original_modified=False,repair_applied=False,anatomical_validation='NOT RUN')
    removable=[]
    for ids in components:
        if len(ids)!=2: continue
        i,j=ids
        if (np.array_equal(np.sort(mesh.faces[i]),np.sort(mesh.faces[j])) and
                mesh.face_normals[i]@mesh.face_normals[j]<-.999999):
            removable.extend(map(int,ids))
    if sorted(removable)!=[0,24,32,33]:
        raise ValueError('Unexpected zero-volume duplicate components; review source')
    kept=np.setdiff1d(np.arange(len(mesh.faces)),removable)
    derived=trimesh.Trimesh(mesh.vertices.copy(),mesh.faces[kept],process=False)
    check=inspect_self_contact(derived.vertices,derived.faces)
    report['diagnostic_copy']=dict(removed_face_ids=sorted(removable),retained_face_count=len(kept),
        retained_triangle_coordinates_unchanged=bool(np.array_equal(derived.triangles,mesh.triangles[kept])),
        watertight=bool(derived.is_watertight),winding_consistent=bool(derived.is_winding_consistent),
        self_contact=check,accepted_for_generation=False)
    if check['status']!='NO_CONTACT_DETECTED':
        raise ValueError('Diagnostic copy still has contact')
    inputs=json.loads((root/'docs/evidence/frontobasal-external-protected-radius.json').read_text())
    parent=json.loads((root/'docs/evidence/frontobasal-junction-partition.json').read_text())
    if parent['atlas_archive_sha256']!=atlas.metadata['sha256']:
        raise ValueError('Atlas identity changed')
    def read_mesh(item):
        path=root/item['artifact']
        if hashlib.sha256(path.read_bytes()).hexdigest()!=item['sha256']:
            raise ValueError('Artifact changed')
        with np.load(path,allow_pickle=False) as data:
            return trimesh.Trimesh(data['vertices_mm'],data['faces'],process=False)
    before=read_mesh(parent)
    cache=_SurfaceValidationCache()
    comparisons=[]
    for row in inputs['rows']:
        result=inspect_radius_context(before,read_mesh(row),{'FJ1699-diagnostic-copy':derived},_validation_cache=cache)
        comparisons.append(dict(edge_id=row['edge_id'],scale=row['scale'],artifact_sha256=row['sha256'],context=result))
    report['diagnostic_copy']['candidate_comparisons']=comparisons
    report['diagnostic_copy']['scope']='Only FJ1699 with four isolated duplicate faces removed; not full-context or anatomical approval'
    path=root/'docs/evidence/fj1699-contact-diagnosis.json'
    path.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(name=source['name'],removed=removable,self_contact=check['status'],comparisons=[r['context']['status'] for r in comparisons],sha256=hashlib.sha256(path.read_bytes()).hexdigest())))


if __name__=='__main__': main()
