"""Open lateral surface candidates from explicit noncircular section profiles."""
import numpy as np
import trimesh


def loft_source_profiles(profiles, *, samples=64):
    """Resample closed perimeters and align cyclic indices between adjacent rings.

    This is a piecewise-linear candidate, not a smoothness or collision approval.
    No unknown section is skipped and no end caps or junctions are invented.
    """
    if type(samples) is not int or not 8<=samples<=512:
        raise ValueError('8–512 perimeter samples required')
    if not isinstance(profiles,list) or not 2<=len(profiles)<=10000:
        raise ValueError('At least two bounded consecutive profiles required')
    rings=[];shifts=[]
    for j,profile in enumerate(profiles):
        if profile.get('status')!='MEASURED' or (j and profile['index']!=profiles[j-1]['index']+1):
            raise ValueError('All profiles must be measured and consecutive')
        xyz=np.asarray(profile['contour_xyz_mm'],dtype=float)
        normal=np.asarray(profile['normal'],dtype=float)
        if (xyz.ndim!=2 or xyz.shape[1]!=3 or len(xyz)<4 or not np.isfinite(xyz).all()
                or normal.shape!=(3,) or not np.isfinite(normal).all()
                or abs(np.linalg.norm(normal)-1)>1e-6
                or np.linalg.norm(xyz[0]-xyz[-1])>1e-6):
            raise ValueError('Finite closed contour and unit normal required')
        xyz=xyz.copy();xyz[-1]=xyz[0]
        oriented_area=np.cross(xyz[:-1]-xyz[0],xyz[1:]-xyz[0]).sum(axis=0)
        direction=float(oriented_area@normal)
        if abs(direction)<=1e-12:raise ValueError('Nondegenerate oriented contour required')
        if direction<0:xyz=xyz[::-1].copy()
        lengths=np.linalg.norm(np.diff(xyz,axis=0),axis=1)
        if np.any(lengths<=1e-12):raise ValueError('Degenerate contour edges')
        arc=np.r_[0,np.cumsum(lengths)]
        grid=np.arange(samples)*arc[-1]/samples
        ring=np.column_stack([np.interp(grid,arc,xyz[:,k]) for k in range(3)])
        shift=0
        if rings:
            costs=[np.sum((np.roll(ring,k,axis=0)-rings[-1])**2) for k in range(samples)]
            shift=int(np.argmin(costs));ring=np.roll(ring,shift,axis=0)
        rings.append(ring);shifts.append(shift)
    vertices=np.concatenate(rings);faces=[]
    for j in range(len(rings)-1):
        for k in range(samples):
            nxt=(k+1)%samples;a=j*samples+k;b=j*samples+nxt
            c=(j+1)*samples+k;d=(j+1)*samples+nxt
            faces.extend([[a,b,d],[a,d,c]])
    mesh=trimesh.Trimesh(vertices,np.asarray(faces),process=False)
    if np.any(mesh.area_faces<=1e-12):raise ValueError('Degenerate loft triangles')
    counts=np.bincount(mesh.edges_unique_inverse)
    if np.any(counts>2) or int((counts==1).sum())!=2*samples or not mesh.is_winding_consistent:
        raise ValueError('Loft does not have the expected open-cylinder topology')
    return mesh,dict(method='perimeter-cyclic-open-loft/1',status='CANDIDATE',
        profiles=len(profiles),samples_per_profile=samples,cyclic_shifts=shifts,
        boundary_edges=int((counts==1).sum()),watertight=bool(mesh.is_watertight),
        winding_consistent=bool(mesh.is_winding_consistent),
        endpoints='open at first and last supplied measured sections',
        self_intersection='NOT RUN',junctions='NOT RUN',smoothness_acceptance='NOT RUN',
        anatomical_validation='NOT RUN')
