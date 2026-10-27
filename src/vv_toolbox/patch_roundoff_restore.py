"""Restore exact protected coordinates only after bijective oriented topology checks."""
import numpy as np
from scipy.spatial import cKDTree


def restore_patch_coordinates(vertices,faces,selected_faces,patch,*,max_roundoff_mm):
    v,f,s=np.asarray(vertices,dtype=float),np.asarray(faces),np.asarray(selected_faces)
    if (v.ndim!=2 or v.shape[1]!=3 or not np.isfinite(v).all() or f.ndim!=2 or f.shape[1]!=3
            or not np.issubdtype(f.dtype,np.integer) or not len(f) or f.min()<0 or f.max()>=len(v)
            or s.ndim!=1 or not len(s) or not np.issubdtype(s.dtype,np.integer)
            or s.min()<0 or s.max()>=len(f) or len(np.unique(s))!=len(s)
            or type(max_roundoff_mm) not in (int,float) or not np.isfinite(max_roundoff_mm)
            or not 0<max_roundoff_mm<=1e-6):
        raise ValueError('Valid surface and explicit small roundoff bound required')
    old=np.asarray(patch['vertices'],dtype=float);old_faces=np.asarray(patch['faces'])
    ids,inverse=np.unique(f[s],return_inverse=True)
    if len(ids)!=len(old):raise ValueError('Protected vertex count changed')
    distances,mapping=cKDTree(old).query(v[ids])
    if distances.max()>max_roundoff_mm or len(np.unique(mapping))!=len(old):
        raise ValueError('No bounded bijective protected vertex match')
    def canonical(face):
        a,b,c=map(int,face)
        return min((a,b,c),(b,c,a),(c,a,b))
    mapped=mapping[inverse.reshape(-1,3)]
    if sorted(map(canonical,mapped))!=sorted(map(canonical,old_faces)):
        raise ValueError('Protected triangle topology or winding changed')
    restored=v.copy();restored[ids]=old[mapping]
    if not np.array_equal(restored[f[s]],old[mapped]):
        raise ValueError('Exact restoration failed')
    return restored,dict(status='PASS',protected_vertices=len(ids),protected_faces=len(s),
        maximum_restoration_mm=float(distances.max()),roundoff_bound_mm=max_roundoff_mm,
        oriented_topology_bijection=True,protected_positions_exact=True,
        source_modified=False,self_contact='NOT RUN')
