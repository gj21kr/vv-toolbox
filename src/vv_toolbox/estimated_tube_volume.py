"""Explicit terminal caps for authored neck tubes, never original Atlas repair."""
from copy import deepcopy

import numpy as np
import trimesh

from .surface_indexing import exact_vertex_index_copy
from .mesh_self_contact import inspect_self_contact


def cap_estimated_neck(part, *, max_planarity_mm, cap_method='convex-fan'):
    metadata=part.get('metadata',{})
    if metadata.get('kind')!='estimated-neck-connector' or metadata.get('original_atlas_geometry') is not False:
        raise ValueError('Only explicitly estimated neck connectors may be capped')
    if type(max_planarity_mm) not in (int,float) or not np.isfinite(max_planarity_mm) or max_planarity_mm<=0:
        raise ValueError('Explicit positive planarity tolerance required')
    if cap_method not in ('convex-fan', 'planar-earcut'):
        raise ValueError('Unsupported terminal cap method')
    mesh,index_report=exact_vertex_index_copy(trimesh.Trimesh(part['vertices'],part['faces'],process=False))
    if not mesh.is_winding_consistent or np.any(mesh.area_faces<=0):
        raise ValueError('Consistent nondegenerate source tube required')
    faces=np.asarray(mesh.faces)
    directed=np.concatenate([faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]]])
    _,inverse,counts=np.unique(np.sort(directed,axis=1),axis=0,return_inverse=True,return_counts=True)
    if np.any(counts>2):
        raise ValueError('Nonmanifold tube edges')
    boundary=directed[counts[inverse]==1]
    outgoing={}
    for a,b in boundary:
        if int(a) in outgoing:
            raise ValueError('Boundary is not a simple loop')
        outgoing[int(a)]=int(b)
    if not outgoing or set(outgoing)!=set(outgoing.values()):
        raise ValueError('Closed directed boundary loops required')
    unused=set(outgoing);loops=[]
    while unused:
        start=min(unused);loop=[];current=start
        while current in unused:
            unused.remove(current);loop.append(current);current=outgoing[current]
        if current!=start or len(loop)<3:
            raise ValueError('Invalid boundary loop')
        loops.append(loop)
    if len(loops)!=2:
        raise ValueError('Exactly two terminal boundaries required')
    vertices=mesh.vertices.tolist();caps=[];reports=[]
    for loop in loops:
        points=np.asarray(mesh.vertices)[loop]
        center=points.mean(0)
        _,_,axes=np.linalg.svd(points-center,full_matrices=False)
        planar=float(np.max(np.abs((points-center)@axes[-1])))
        if planar>max_planarity_mm:
            raise ValueError('Terminal boundary exceeds planarity tolerance')
        uv=(points-center)@axes[:2].T
        edges=np.roll(uv,-1,axis=0)-uv
        turns=edges[:,0]*np.roll(edges,-1,axis=0)[:,1]-edges[:,1]*np.roll(edges,-1,axis=0)[:,0]
        if cap_method == 'convex-fan':
            if not (np.all(turns>1e-12) or np.all(turns < -1e-12)):
                raise ValueError('Convex terminal boundary required')
            index=len(vertices);vertices.append(center.tolist())
            caps.extend([outgoing[a],a,index] for a in loop)
            reports.append(dict(boundary_vertices=loop,cap_center_vertex=index,max_planarity_mm=planar))
        else:
            import mapbox_earcut
            triangles=mapbox_earcut.triangulate_float64(
                np.ascontiguousarray(uv), np.array([len(loop)], dtype=np.uint32)).reshape(-1,3)
            # Earcut may emit zero-area ears at collinear source vertices.
            # Remove those ears, then split the remaining edge to retain every
            # source boundary vertex without changing any side triangle.
            valid=[]
            for tri in triangles:
                p,q,r=uv[tri]
                if abs((q[0]-p[0])*(r[1]-p[1])-(q[1]-p[1])*(r[0]-p[0]))>1e-12:
                    valid.append(list(map(int,tri)))
            for index_uv in range(len(loop)):
                if any(index_uv in tri for tri in valid):
                    continue
                inserted=False
                for ti,tri in enumerate(valid):
                    for k in range(3):
                        a,b,c=tri[k],tri[(k+1)%3],tri[(k+2)%3]
                        edge=uv[b]-uv[a];offset=uv[index_uv]-uv[a]
                        fraction=float(offset@edge/(edge@edge))
                        if 0<fraction<1 and np.linalg.norm(offset-fraction*edge)<1e-10:
                            valid[ti]=[a,index_uv,c]
                            valid.append([index_uv,b,c]);inserted=True
                            break
                    if inserted:break
                if not inserted:
                    raise ValueError('Cannot preserve terminal boundary vertex')
            triangles=np.asarray(valid,dtype=int)
            if len(triangles)!=len(loop)-2:
                raise ValueError('Incomplete terminal triangulation')
            area=float(np.sum(uv[:,0]*np.roll(uv[:,1],-1)-uv[:,1]*np.roll(uv[:,0],-1)))
            for triangle in triangles:
                p,q,r=uv[triangle]
                signed=(q[0]-p[0])*(r[1]-p[1])-(q[1]-p[1])*(r[0]-p[0])
                # Caps oppose the directed open surface boundary.
                if signed*area>0:
                    triangle=triangle[::-1]
                caps.append([loop[int(i)] for i in triangle])
            reports.append(dict(boundary_vertices=loop,max_planarity_mm=planar))
    candidate=trimesh.Trimesh(np.asarray(vertices),np.concatenate([faces,np.asarray(caps)]),process=False)
    if not candidate.is_volume or not candidate.is_winding_consistent or np.any(candidate.area_faces<=0):
        raise ValueError('Capped tube is not a positive closed volume')
    contact=inspect_self_contact(candidate.vertices,candidate.faces)
    if contact.get('status')!='NO_CONTACT_DETECTED':
        raise ValueError('Capped tube self-contact check did not pass')
    result=deepcopy(part)
    result['vertices']=np.asarray(candidate.vertices).copy()
    result['faces']=np.asarray(candidate.faces).copy()
    result['metadata']['volume_derivation']=dict(
        method='convex-terminal-fans/1' if cap_method=='convex-fan' else 'planar-terminal-earcut/1',max_planarity_mm=max_planarity_mm,
        boundaries=reports,added_faces=len(caps),source_indexing=index_report,
        self_contact=contact,source_triangles_preserved=True,
        purpose='Separate estimated volume for voxel membership; no source cap removal or lumen union',
        anatomical_connection='NOT RUN')
    return result
