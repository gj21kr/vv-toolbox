"""Separate synthetic solid unions; never rewrite their input Atlas surfaces."""
import hashlib
from importlib.metadata import version

import numpy as np
import trimesh

from .mesh_self_contact import inspect_self_contact
from .surface_indexing import exact_vertex_index_copy


def build_solid_union(meshes, *, diagnostic_callback=None, precision='float64'):
    if not isinstance(meshes, dict) or len(meshes)<2:
        raise ValueError("At least two named solid surfaces required")
    if precision not in ('float32','float64'):
        raise ValueError("Unsupported coordinate precision")
    prepared=[];records={}
    for name,source in sorted(meshes.items()):
        surface,indexing=exact_vertex_index_copy(source)
        if not surface.is_volume or np.any(surface.area_faces<=0):
            raise ValueError(f"{name}: positive closed nondegenerate solid required")
        contact=inspect_self_contact(surface.vertices,surface.faces)
        if contact['status']!='NO_CONTACT_DETECTED':
            raise ValueError(f"{name}: source self-contact not cleared")
        digest=hashlib.sha256()
        digest.update(np.asarray(source.vertices,dtype='<f8').tobytes())
        digest.update(np.asarray(source.faces,dtype='<i8').tobytes())
        records[name]=dict(geometry_sha256=digest.hexdigest(),indexing=indexing,
                           self_contact=contact,volume_mm3=float(surface.volume))
        prepared.append(surface)
    # Keep the float32 adapter as a reproducible comparison; use Mesh64 by
    # default. Localize either path without claiming exact source fidelity.
    origin=np.concatenate([m.vertices for m in prepared]).mean(axis=0)
    local=[trimesh.Trimesh(m.vertices-origin,m.faces.copy(),process=False) for m in prepared]
    lineage=None
    if precision=='float32':
        merged=trimesh.boolean.union(local,engine='manifold',check_volume=True)
    else:
        from manifold3d import Manifold, Mesh64, Error
        solids=[]
        first_id=Manifold.reserve_ids(len(local))
        source_names=sorted(meshes)
        for index,mesh in enumerate(local):
            solid=Manifold(Mesh64(np.ascontiguousarray(mesh.vertices,dtype=np.float64),
                                  np.ascontiguousarray(mesh.faces,dtype=np.uint64),
                                  run_index=np.array([0,len(mesh.faces)*3],dtype=np.uint64),
                                  run_original_id=np.array([first_id+index],dtype=np.uint32),
                                  face_id=np.arange(len(mesh.faces),dtype=np.uint64)))
            if solid.status()!=Error.NoError:
                raise ValueError(f"Manifold input rejected: {solid.status()}")
            solids.append(solid)
        combined=solids[0]
        for solid in solids[1:]:
            combined=combined+solid
        if combined.status()!=Error.NoError:
            raise ValueError(f"Manifold union rejected: {combined.status()}")
        output=combined.to_mesh64()
        merged=trimesh.Trimesh(output.vert_properties,output.tri_verts,process=False)
        owners=np.full(len(merged.faces),-1,dtype=np.int64)
        for lo,hi,original_id in zip(output.run_index[:-1],output.run_index[1:],output.run_original_id):
            if lo%3 or hi%3 or not first_id<=original_id<first_id+len(local):
                raise ValueError("Invalid union triangle provenance")
            owners[int(lo)//3:int(hi)//3]=int(original_id)-first_id
        source_faces=np.asarray(output.face_id,dtype=np.int64)
        if len(source_faces)!=len(owners) or np.any(owners<0):
            raise ValueError("Incomplete union triangle provenance")
        for index,mesh in enumerate(local):
            ids=source_faces[owners==index]
            if np.any(ids<0) or np.any(ids>=len(mesh.faces)):
                raise ValueError("Invalid original face index")
        lineage=dict(method='manifold-original-id-and-face-id/1',
                     source_names=source_names,face_source_indices=owners.tolist(),
                     source_face_indices=source_faces.tolist(),
                     anatomical_labels='NOT ASSIGNED')
    merged.apply_translation(origin)
    if diagnostic_callback is not None:
        diagnostic_callback(merged.copy(),dict(
            precision=precision,vertices=len(merged.vertices),faces=len(merged.faces),
            watertight=bool(merged.is_watertight),
            winding_consistent=bool(merged.is_winding_consistent),
            is_volume=bool(merged.is_volume),volume_mm3=float(merged.volume),
            zero_area_faces=int(np.count_nonzero(merged.area_faces<=0)),
            minimum_face_area_mm2=float(merged.area_faces.min()) if len(merged.faces) else None,
            local_origin_mm=origin.tolist(),input_surfaces=records,
            manifold_version=version('manifold3d'),trimesh_version=trimesh.__version__))
    if not merged.is_volume or np.any(merged.area_faces<=0):
        raise ValueError("Union is not a positive closed nondegenerate solid")
    components=trimesh.graph.connected_components(merged.face_adjacency,
                                                  nodes=np.arange(len(merged.faces)),min_len=1)
    if len(components)!=1:
        raise ValueError(f"Union has {len(components)} disconnected boundary components")
    contact=inspect_self_contact(merged.vertices,merged.faces)
    if contact['status']!='NO_CONTACT_DETECTED':
        raise ValueError("Union self-contact not cleared")
    return merged,dict(status='CANDIDATE',method='manifold-solid-union/2',
        manifold_version=version('manifold3d'),trimesh_version=trimesh.__version__,
        input_surfaces=records,local_origin_mm=origin.tolist(),boundary_components=1,
        volume_mm3=float(merged.volume),self_contact=contact,source_modified=False,
        precision=precision,source_fidelity='NOT RUN',face_lineage=lineage,
        anatomical_validation='NOT RUN',neighbor_contact='NOT RUN',smoothness='NOT RUN')
