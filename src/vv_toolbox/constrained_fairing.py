"""Local squared-Laplacian fairing with exactly fixed vertices."""
import numpy as np
import trimesh
from scipy.sparse import coo_matrix,eye
from scipy.sparse.linalg import spsolve


def fair_surface(vertices,faces,free_vertices,*,strength,max_displacement_mm,max_volume_change_fraction):
    original=np.asarray(vertices,dtype=float);faces=np.asarray(faces);free=np.asarray(free_vertices)
    if (original.ndim!=2 or original.shape[1]!=3 or not np.isfinite(original).all()
            or faces.ndim!=2 or faces.shape[1]!=3 or not len(faces)
            or not np.issubdtype(faces.dtype,np.integer) or faces.min()<0 or faces.max()>=len(original)
            or free.ndim!=1 or not len(free) or not np.issubdtype(free.dtype,np.integer)
            or free.min()<0 or free.max()>=len(original) or len(set(free.tolist()))!=len(free)
            or any(not np.isfinite(v) or v<=0 for v in
                   (strength,max_displacement_mm,max_volume_change_fraction))):
        raise ValueError('valid surface, explicit free vertices and positive limits required')
    mesh=trimesh.Trimesh(vertices=original,faces=faces,process=False)
    if not mesh.is_volume or len(mesh.split(only_watertight=False))!=1:
        raise ValueError('one closed positive volume required')
    edges=mesh.edges_unique
    row=np.r_[edges[:,0],edges[:,1]];col=np.r_[edges[:,1],edges[:,0]]
    degree=np.bincount(row,minlength=len(original))
    if np.any(degree==0):raise ValueError('unused vertices')
    average=coo_matrix((1/degree[row],(row,col)),shape=(len(original),)*2).tocsr()
    lap=eye(len(original),format='csr')-average
    matrix=eye(len(original),format='csr')+strength*(lap.T@lap)
    origin=original.mean(axis=0);local=original-origin
    # Solve for free displacement, avoiding subtraction of large world positions.
    rhs=-strength*(lap.T@(lap@local))
    displacement=spsolve(matrix[free][:,free].tocsc(),rhs[free])
    moved=original.copy();moved[free]+=displacement
    maximum=float(np.linalg.norm(displacement,axis=1).max())
    if not np.isfinite(moved).all() or maximum>max_displacement_mm:
        raise ValueError(f'fairing displacement limit exceeded: {maximum}')
    result=trimesh.Trimesh(vertices=moved,faces=faces,process=False)
    if not result.is_volume or np.any(result.area_faces<=1e-12):
        raise ValueError('fairing invalidated surface')
    volume_change=abs(float(result.volume/mesh.volume)-1)
    if volume_change>max_volume_change_fraction:
        raise ValueError(f'fairing volume limit exceeded: {volume_change}')
    return moved,dict(status='CANDIDATE',method='fixed-vertex squared uniform Laplacian',
        strength=strength,free_vertices=len(free),max_displacement_mm=maximum,
        displacement_limit_mm=max_displacement_mm,volume_change_fraction=volume_change,
        volume_change_limit_fraction=max_volume_change_fraction,
        fixed_vertices_exact=True,closed_volume='PASS',self_intersection='NOT RUN')
