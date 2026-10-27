"""Sampled design-rim conformity to actual triangles, not neck identification."""
import numpy as np
import trimesh


def inspect_neck_conformity(vertices,faces,curve,center,basis,*,distance_limit_mm):
    vertices=np.asarray(vertices,dtype=float);faces=np.asarray(faces)
    curve=np.asarray(curve,dtype=float);center=np.asarray(center,dtype=float)
    basis=np.asarray(basis,dtype=float)
    if (vertices.ndim!=2 or vertices.shape[1]!=3 or not len(vertices)
            or faces.ndim!=2 or faces.shape[1]!=3 or not len(faces)
            or not np.issubdtype(faces.dtype,np.integer) or faces.min()<0 or faces.max()>=len(vertices)
            or curve.ndim!=2 or curve.shape[1]!=3 or len(curve)<3
            or center.shape!=(3,) or basis.shape!=(3,3)
            or not all(np.isfinite(a).all() for a in (vertices,curve,center,basis))
            or not np.allclose(basis.T@basis,np.eye(3),atol=1e-8,rtol=0)
            or not np.isfinite(distance_limit_mm) or distance_limit_mm<=0):
        raise ValueError('finite surface, rim, orthonormal basis and positive limit required')
    mesh=trimesh.Trimesh(vertices=vertices,faces=faces,process=False)
    if np.any(mesh.area_faces<=1e-15):
        raise ValueError('degenerate triangle')
    nearest=[];distances=[];triangle_ids=[]
    for start in range(0,len(curve),4):
        points,dist,ids=trimesh.proximity.closest_point_naive(mesh,curve[start:start+4])
        nearest.extend(points.tolist());distances.extend(dist.tolist());triangle_ids.extend(ids.tolist())
    nearest=np.array(nearest);distances=np.array(distances)
    original_local=(curve-center)@basis
    mapped_local=(nearest-center)@basis
    maximum=float(distances.max())
    return dict(schema='vv-toolbox.neck-conformity/1',
        sampled_distance_status='PASS' if maximum<=distance_limit_mm else 'FAIL',
        distance_limit_mm=distance_limit_mm,max_distance_mm=maximum,
        mean_distance_mm=float(distances.mean()),sample_count=len(curve),
        design_projected_width_depth_mm=np.ptp(original_local[:,:2],axis=0).tolist(),
        mapped_projected_width_depth_mm=np.ptp(mapped_local[:,:2],axis=0).tolist(),
        projected_span_change_mm=(np.ptp(mapped_local[:,:2],axis=0)-np.ptp(original_local[:,:2],axis=0)).tolist(),
        mapped_points_mm=nearest.tolist(),triangle_indices=triangle_ids,
        sampled_distances_mm=distances.tolist(),
        anatomical_neck_dimensions='UNKNOWN',
        continuous_rim_conformity='NOT RUN',
        limitation='Nearest triangles need not form the true neck boundary or a continuous contour; sampled conformity only.')
