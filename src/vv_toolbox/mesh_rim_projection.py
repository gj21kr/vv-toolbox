"""Neck-rim rays onto an explicitly supplied closed source surface."""
import hashlib
import numpy as np
import trimesh


def project_rim_to_mesh(vertices,faces,rim,normal,*,lower_mm,upper_mm):
    vertices=np.asarray(vertices,dtype=float);faces=np.asarray(faces);rim=np.asarray(rim,dtype=float)
    normal=np.asarray(normal,dtype=float)
    if (vertices.ndim!=2 or vertices.shape[1]!=3 or not np.isfinite(vertices).all()
            or faces.ndim!=2 or faces.shape[1]!=3 or not len(faces)
            or not np.issubdtype(faces.dtype,np.integer) or faces.min()<0 or faces.max()>=len(vertices)
            or rim.ndim!=2 or rim.shape[1]!=3 or len(rim)<3 or not np.isfinite(rim).all()
            or normal.shape!=(3,) or not np.isfinite(normal).all() or not np.isclose(np.linalg.norm(normal),1,atol=1e-8,rtol=0)):
        raise ValueError('Finite mesh, rim and unit ray direction required')
    if any(type(v) not in (int,float) or not np.isfinite(v) for v in (lower_mm,upper_mm)) or lower_mm>=upper_mm:
        raise ValueError('Finite increasing projection bounds required')
    unique,inverse=np.unique(vertices,axis=0,return_inverse=True)
    normalized_faces=inverse[faces]
    mesh=trimesh.Trimesh(vertices=unique,faces=normalized_faces,process=False)
    if not mesh.is_volume:raise ValueError('Consistently oriented closed source volume required')
    origins=rim+lower_mm*normal
    locations,rays,triangles=mesh.ray.intersects_location(origins,np.tile(normal,(len(rim),1)),multiple_hits=True)
    locations=np.asarray(locations,dtype=float).reshape(-1,3)
    rays=np.asarray(rays,dtype=np.int64);triangles=np.asarray(triangles,dtype=np.int64)
    offsets=np.sum((locations-rim[rays])*normal,axis=1)
    orientation=mesh.face_normals[triangles]@normal
    rows=[]
    for index in range(len(rim)):
        within=(rays==index)&(offsets>=lower_mm-1e-8)&(offsets<=upper_mm+1e-8)
        outgoing=np.flatnonzero(within&(orientation>1e-8))
        grazing=bool(np.any(within&(np.abs(orientation)<=1e-8)))
        valid=len(outgoing)==1 and not grazing
        hit=int(outgoing[0]) if valid else None
        rows.append(dict(sample_index=index,status='PASS' if valid else 'UNKNOWN',
            exit_count=len(outgoing),grazing_hit=grazing,
            source_face_index=int(triangles[hit]) if valid else None,
            offset_mm=float(offsets[hit]) if valid else None,
            point_mm=locations[hit].tolist() if valid else None))
    complete=all(r['status']=='PASS' for r in rows)
    geometry_hash=hashlib.sha256(vertices.astype('<f8').tobytes()+faces.astype('<i8').tobytes()).hexdigest()
    return dict(schema='vv-toolbox.mesh-rim-projection/1',status='CANDIDATE' if complete else 'UNKNOWN',
        source_geometry_sha256=geometry_hash,projection_bounds_mm=[float(lower_mm),float(upper_mm)],
        normal=normal.tolist(),sample_count=len(rows),resolved_sample_count=sum(r['status']=='PASS' for r in rows),
        samples=rows,curve_mm=[r['point_mm'] for r in rows] if complete else None,
        normalization='Exact duplicate coordinates welded; original triangle order and positions preserved',
        accepted_for_generation=False,continuous_boundary='NOT RUN',
        limitation='Finite-precision triangle ray hits; between-sample attachment and tangent continuity unverified. '
                   'Multiple or grazing exits are unresolved. No surface trimming or lumen union.')
