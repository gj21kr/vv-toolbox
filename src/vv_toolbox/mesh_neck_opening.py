"""Separate source-derived neck opening with an explicitly retriangulated collar."""
import numpy as np
import trimesh
from .mesh_rim_trace import trace_mesh_rim
from .patch_boundary import patch_boundary_loops
from .projected_annulus import contains,triangulate_annulus


def _repair_collinear_collar(vertices,faces,normal):
    faces=faces.copy();repairs=0
    for _ in range(len(faces)):
        triangles=vertices[faces]
        area=np.linalg.norm(np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0]),axis=1)
        small=np.flatnonzero(area<=1e-12)
        if not len(small):return faces,repairs
        i=int(small[0]);ids=faces[i]
        pairs=[(int(ids[a]),int(ids[b])) for a,b in ((0,1),(1,2),(2,0))]
        a,b=max(pairs,key=lambda p:np.linalg.norm(vertices[p[1]]-vertices[p[0]]))
        c=next(int(v) for v in ids if v not in (a,b))
        adjacent=[j for j,f in enumerate(faces) if j!=i and a in f and b in f]
        if len(adjacent)!=1:raise ValueError('Cannot repair collinear collar without changing boundary')
        j=adjacent[0];d=next(int(v) for v in faces[j] if v not in (a,b))
        proposed=np.array([[a,c,d],[c,b,d]])
        for k in range(2):
            p=vertices[proposed[k]]
            if np.cross(p[1]-p[0],p[2]-p[0])@normal<0:proposed[k]=proposed[k,::-1]
        faces[[i,j]]=proposed;repairs+=1
    raise ValueError('Collinear collar repair did not converge')


def build_neck_opening(vertices,faces,polygon,normal):
    original=np.asarray(vertices,float);faces=np.asarray(faces)
    vertices,inverse=np.unique(original,axis=0,return_inverse=True);faces=inverse[faces]
    mesh=trimesh.Trimesh(vertices=vertices,faces=faces,process=False)
    if not mesh.is_volume:raise ValueError('Closed consistently oriented source required')
    polygon=np.asarray(polygon,float);normal=np.asarray(normal,float)
    trace=trace_mesh_rim(vertices,faces,polygon,normal)
    if trace['status']!='CANDIDATE':raise ValueError('Complete unique source rim trace required')
    center=polygon.mean(axis=0);width=polygon[1]-polygon[0]
    width-=normal*(width@normal);width/=np.linalg.norm(width)
    basis=np.column_stack([width,np.cross(normal,width),normal])
    xy=((polygon-center)@basis)[:,:2]
    inside=contains(xy,((mesh.triangles_center-center)@basis)[:,:2])
    selected=set(np.flatnonzero(inside&(mesh.face_normals@normal>1e-8)).tolist())
    chain=[segment for side in trace['sides'] for segment in side['segments']]
    selected.update(segment['source_face_index'] for segment in chain)
    selected=np.array(sorted(selected),dtype=int)
    loops=patch_boundary_loops(faces,selected)
    if len(loops)!=1:raise ValueError('Selected source region must have one outer boundary')
    rim=np.asarray([s['points_mm'][0] for s in chain])
    outer=np.asarray(loops[0],dtype=int)
    if not contains(((vertices[outer]-center)@basis)[:,:2],((rim-center)@basis)[:,:2]).all():
        raise ValueError('Source region does not strictly enclose neck boundary')
    inner=np.arange(len(vertices),len(vertices)+len(rim))
    combined=np.vstack([vertices,rim])
    collar=triangulate_annulus(combined,inner,outer,center,basis,engine='earcut')
    collar,repairs=_repair_collinear_collar(combined,collar,normal)
    retained=np.setdiff1d(np.arange(len(faces)),selected)
    output_faces=np.vstack([faces[retained],collar])
    opened=trimesh.Trimesh(vertices=combined,faces=output_faces,process=False)
    boundary=patch_boundary_loops(output_faces,np.arange(len(output_faces)))
    if len(boundary)!=1 or set(boundary[0])!=set(inner) or not opened.is_winding_consistent:
        raise ValueError('Reconstructed opening must have exactly the declared rim and consistent orientation')
    return combined,output_faces,dict(schema='vv-toolbox.mesh-neck-opening/1',status='CANDIDATE',
        removed_source_face_ids=selected.tolist(),retained_source_face_ids=retained.tolist(),
        new_collar_face_count=len(collar),neck_boundary_vertex_ids=inner.tolist(),trace=trace,
        collinear_collar_repairs=repairs,
        source_face_ids=np.r_[retained,np.full(len(collar),-1)].tolist(),
        retained_triangle_identity=bool(np.array_equal(combined[output_faces[:len(retained)]],vertices[faces[retained]])),
        accepted_for_generation=False,closed_lumen=False,
        limitation='Source input unchanged. Cut region is replaced by a triangulated collar; collar interiors '
                   'are not guaranteed to coincide with original triangles. Deviation, self-contact and union unverified.')
