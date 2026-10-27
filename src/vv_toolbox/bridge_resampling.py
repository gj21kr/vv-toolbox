"""Resample only interior bridge rings, preserving complete endpoint collars."""
import numpy as np
import trimesh

from .quality_stitch import quality_stitch


def resample_bridge_interior(rings, *, samples=64, preserved_rings=2):
    rings=np.asarray(rings,dtype=float)
    if (rings.ndim!=3 or rings.shape[2]!=3 or not np.isfinite(rings).all()
            or type(samples) is not int or not 8<=samples<=512
            or type(preserved_rings) is not int or preserved_rings<1
            or len(rings)<=2*preserved_rings or rings.shape[1]<3):
        raise ValueError('Finite ring sequence and interior resampling settings required')
    output=[];ids=[];offset=0
    for i,ring in enumerate(rings):
        if i<preserved_rings or i>=len(rings)-preserved_rings:
            row=ring.copy()
        else:
            closed=np.vstack([ring,ring[0]])
            lengths=np.linalg.norm(np.diff(closed,axis=0),axis=1)
            if np.any(lengths<=1e-12):raise ValueError('Degenerate ring perimeter')
            arc=np.r_[0,np.cumsum(lengths)]
            stations=np.arange(samples)*arc[-1]/samples
            row=np.column_stack([np.interp(stations,arc,closed[:,k]) for k in range(3)])
        ids.append(np.arange(offset,offset+len(row)));offset+=len(row);output.append(row)
    vertices=np.concatenate(output);faces=[]
    for first,second in zip(ids,ids[1:]):
        if len(first)!=len(second):
            faces.extend(quality_stitch(vertices,first,second).tolist())
        else:
            for k in range(len(first)):
                j=(k+1)%len(first)
                faces.extend([[first[k],first[j],second[j]],[first[k],second[j],second[k]]])
    mesh=trimesh.Trimesh(vertices,np.asarray(faces),process=False)
    if np.any(mesh.area_faces<=1e-12) or not mesh.is_winding_consistent:
        raise ValueError('Invalid remeshed wall')
    return mesh,dict(status='CANDIDATE',method='interior-perimeter-resampling/1',
        stations=len(rings),interior_samples=samples,preserved_rings_each_end=preserved_rings,
        endpoint_collars_exact=all(np.array_equal(output[i],rings[i]) for i in
            list(range(preserved_rings))+list(range(len(rings)-preserved_rings,len(rings)))),
        ring_vertex_ids=[x.tolist() for x in ids],
        self_contact='NOT RUN',source_union='NOT RUN',geometry_deviation='NOT RUN')
