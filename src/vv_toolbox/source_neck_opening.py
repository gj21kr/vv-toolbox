"""Conforming source-face partitions for a separate neck opening candidate."""
import numpy as np
import trimesh
from .mesh_neck_opening import build_neck_opening
from .triangle_neck_cut import partition_triangle
from .patch_boundary import patch_boundary_loops, vertices_to_closed_curve_distance


def build_source_neck_opening(vertices,faces,polygon,normal):
    original=np.asarray(vertices,float);source_faces=np.asarray(faces)
    # Reuse the checked unique source trace and region selection, not its collar.
    _,_,selection=build_neck_opening(original,source_faces,polygon,normal)
    base,inverse=np.unique(original,axis=0,return_inverse=True)
    indexed=inverse[source_faces];points=list(base.copy())
    center=np.asarray(polygon,float).mean(0);normal=np.asarray(normal,float)
    width=np.asarray(polygon,float)[1]-polygon[0];width-=normal*(width@normal);width/=np.linalg.norm(width)
    basis=np.column_stack([width,np.cross(normal,width)])
    neck=(np.asarray(polygon)-center)@basis
    selected=set(selection['removed_source_face_ids']);polygons=[]
    def register(p):
        distance=np.linalg.norm(np.asarray(points)-p,axis=1)
        closest=int(np.argmin(distance))
        if distance[closest]<=1e-9:return closest
        points.append(p);return len(points)-1
    for i,face in enumerate(indexed):
        if i not in selected:polygons.append((i,face.tolist()));continue
        tri=base[face]
        _,outside=partition_triangle((tri-center)@basis,neck)
        for bary in outside:polygons.append((i,[register(p) for p in bary@tri]))
    for side in selection['trace']['sides']:
        for segment in side['segments']:
            register(np.asarray(segment['points_mm'][0]))
    candidates=np.asarray(points);output=[];lineage=[];split_source=[];retained=[]
    # All existing edge points must be represented on both sides of a seam.
    for source_id,ids in polygons:
        expanded=[]
        for a,b in zip(ids,ids[1:]+ids[:1]):
            delta=candidates[b]-candidates[a];length2=delta@delta
            if length2<=1e-20:raise ValueError('Degenerate cut edge')
            t=(candidates-candidates[a])@delta/length2
            distance=np.linalg.norm(candidates-candidates[a]-t[:,None]*delta,axis=1)
            middle=np.flatnonzero((t>1e-9)&(t<1-1e-9)&(distance<=1e-9))
            expanded.extend([a,*middle[np.argsort(t[middle])].tolist()])
        if len(expanded)==3:
            if source_id not in selected:retained.append(len(output))
            output.append(expanded);lineage.append(source_id);continue
        pivot=len(points);points.append(np.asarray(points)[expanded].mean(0))
        for a,b in zip(expanded,expanded[1:]+expanded[:1]):
            output.append([a,b,pivot]);lineage.append(source_id)
        split_source.append(source_id)
    v=np.asarray(points);f=np.asarray(output,dtype=np.int64)
    loops=patch_boundary_loops(f,np.arange(len(f)))
    if len(loops)!=1:raise ValueError('Source cut must have one neck boundary')
    rim=loops[0];xy=(v[rim]-center)@basis
    signed=np.sum(xy[:,0]*np.roll(xy[:,1],-1)-xy[:,1]*np.roll(xy[:,0],-1))
    if signed<0:rim=rim[::-1]
    trace_curve=np.asarray([s['points_mm'][0] for side in selection['trace']['sides'] for s in side['segments']])
    if vertices_to_closed_curve_distance(v[rim],trace_curve).max()>1e-8:
        raise ValueError('Boundary departed from source neck trace')
    mesh=trimesh.Trimesh(vertices=v,faces=f,process=False)
    if not mesh.is_winding_consistent or np.any(mesh.area_faces<=1e-12):
        raise ValueError('Source cut orientation or area invalid')
    for tri,source_id in zip(v[f],lineage):
        source=original[source_faces[source_id]]
        axes=(source[1:]-source[0]).T
        uv=np.linalg.lstsq(axes,(tri-source[0]).T,rcond=None)[0].T
        projected=uv@axes.T+source[0]
        if (np.max(np.linalg.norm(projected-tri,axis=1))>1e-8
                or np.any(uv < -1e-8) or np.any(uv.sum(1)>1+1e-8)):
            raise ValueError('Partition leaves its declared source triangle')
    return v,f,dict(schema='vv-toolbox.source-neck-opening/1',status='CANDIDATE',
        neck_boundary_vertex_ids=rim,trace=selection['trace'],
        source_face_ids=lineage,partitioned_source_face_ids=sorted(selected|set(split_source)),
        retained_output_face_ids=retained,source_triangle_containment='PASS',
        accepted_for_generation=False,closed_lumen=False,
        limitation='Source-face partitions; no dome union, contact or anatomical acceptance.')
