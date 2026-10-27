"""Radius candidates for a source selection, with fixed union interfaces."""
import numpy as np
import trimesh
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra

from .union_selection import select_union_source
from .mesh_self_contact import inspect_self_contact


def scale_selected_radius(mesh,lineage,source_name,centerline,*,scale,transition_mm,max_displacement_mm,
                          _validation_cache=None, protect_interface_faces=False, protected_face_ids=None):
    if type(protect_interface_faces) is not bool:
        raise ValueError('protect_interface_faces must be boolean')
    values=np.asarray([scale,transition_mm,max_displacement_mm],float)
    if not np.isfinite(values).all() or np.any(values<=0):
        raise ValueError('Positive finite radius scale, transition and displacement bound required')
    points=np.asarray(centerline,float)
    if points.ndim!=2 or points.shape[1]!=3 or len(points)<2 or not np.isfinite(points).all():
        raise ValueError('Explicit finite centerline required')
    delta=np.diff(points,axis=0);lengths=np.linalg.norm(delta,axis=1)
    if np.any(lengths<=1e-12):raise ValueError('Distinct consecutive centerline points required')
    selection=select_union_source(mesh.vertices,mesh.faces,lineage,source_name)
    shared=np.asarray(selection['shared_interface_vertex_ids'],int)
    active=np.asarray(selection['exclusive_vertex_ids'],int)
    if not len(shared) or not len(active):raise ValueError('Nonempty interior and fixed interface required')
    interface_faces=np.flatnonzero(np.any(np.isin(mesh.faces,shared),axis=1))
    fixed_collar=shared
    if protect_interface_faces:
        fixed_collar=np.unique(mesh.faces[interface_faces])
    protected=np.array([],dtype=int)
    if protected_face_ids is not None:
        protected=np.asarray(protected_face_ids)
        if (protected.ndim!=1 or not np.issubdtype(protected.dtype,np.integer)
                or len(np.unique(protected))!=len(protected)
                or np.any(protected<0) or np.any(protected>=len(mesh.faces))):
            raise ValueError('Unique valid integer protected face IDs required')
        fixed_collar=np.union1d(fixed_collar,np.unique(mesh.faces[protected]))
    if protect_interface_faces or len(protected):
        active=np.setdiff1d(active,fixed_collar)
        if not len(active):raise ValueError('No editable vertices remain beyond fixed interface faces')
    if not mesh.is_volume:raise ValueError('Closed positive union required')
    vertices=np.asarray(mesh.vertices)
    edges=mesh.edges_unique;edge_lengths=np.linalg.norm(vertices[edges[:,1]]-vertices[edges[:,0]],axis=1)
    graph=coo_matrix((np.r_[edge_lengths,edge_lengths],
        (np.r_[edges[:,0],edges[:,1]],np.r_[edges[:,1],edges[:,0]])),
        shape=(len(vertices),len(vertices))).tocsr()
    distance=dijkstra(graph,directed=False,indices=fixed_collar,min_only=True)
    if not np.isfinite(distance[active]).all():
        raise ValueError('Selection has vertices disconnected from fixed interface')
    arc=np.r_[0.,np.cumsum(lengths)]
    projected=[];along=[];tangents=[]
    for start in range(0,len(active),256):
        query=vertices[active[start:start+256]]
        fraction=np.clip(np.einsum('nsi,si->ns',query[:,None]-points[:-1],delta)/(lengths**2),0,1)
        locations=points[:-1]+fraction[:,:,None]*delta
        nearest=np.argmin(np.sum((query[:,None]-locations)**2,axis=2),axis=1)
        ids=np.arange(len(query))
        projected.extend(locations[ids,nearest])
        along.extend(arc[nearest]+fraction[ids,nearest]*lengths[nearest])
        tangents.extend(delta[nearest]/lengths[nearest,None])
    projected=np.asarray(projected);along=np.asarray(along);tangents=np.asarray(tangents)
    radius=vertices[active]-projected
    radius-=np.einsum('ij,ij->i',radius,tangents)[:,None]*tangents
    weight=np.clip(np.minimum(distance[active],np.minimum(along,arc[-1]-along))/transition_mm,0,1)
    weight=weight*weight*(3-2*weight)
    output=vertices.copy()
    output[active]+=(scale-1)*weight[:,None]*radius
    displacement=np.linalg.norm(output-vertices,axis=1)
    if displacement.max()>max_displacement_mm:raise ValueError('Radius change exceeds displacement bound')
    triangles=output[mesh.faces];old=vertices[mesh.faces]
    normals=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0])
    original=np.cross(old[:,1]-old[:,0],old[:,2]-old[:,0])
    if np.any(np.linalg.norm(normals,axis=1)<=1e-12) or np.any(np.sum(normals*original,axis=1)<=0):
        raise ValueError('Radius change degenerates or reverses triangles')
    result=trimesh.Trimesh(output,mesh.faces.copy(),process=False)
    if not result.is_volume:raise ValueError('Radius change loses closed positive volume')
    contact=(inspect_self_contact(result.vertices,result.faces) if _validation_cache is None
             else _validation_cache.self_contact_check(result))
    if contact['status']!='NO_CONTACT_DETECTED':raise ValueError('Radius change self-contact not cleared')
    return result,dict(status='CANDIDATE',source_name=source_name,scale=float(scale),
        transition_mm=float(transition_mm),maximum_displacement_mm=float(displacement.max()),
        displacement_bound_mm=float(max_displacement_mm),moved_vertices=int((displacement>1e-12).sum()),
        shared_vertices_fixed=bool(np.array_equal(output[shared],vertices[shared])),
        protect_interface_faces=protect_interface_faces,
        interface_faces_fixed=bool(np.array_equal(output[mesh.faces[interface_faces]],vertices[mesh.faces[interface_faces]])),
        fixed_collar_vertices=len(fixed_collar),
        protected_face_ids=protected.tolist(),
        protected_faces_fixed=bool(np.array_equal(output[mesh.faces[protected]],vertices[mesh.faces[protected]])),
        other_source_vertices_fixed=bool(np.array_equal(output[np.setdiff1d(np.arange(len(vertices)),active)],
                                                       vertices[np.setdiff1d(np.arange(len(vertices)),active)])),
        faces_unchanged=True,self_contact=contact,neighbor_contact='NOT RUN',
        scope='Radial displacement about supplied polyline, tapered at source interfaces and path ends',
        anatomical_validation='NOT RUN')
