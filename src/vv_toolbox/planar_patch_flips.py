"""Quality-improving near-coplanar flips inside an explicit face selection."""
import numpy as np


def improve_planar_patch(vertices, faces, selected_faces, *, plane_tolerance_mm=1e-8, sweeps=3):
    v,f,s=np.asarray(vertices,dtype=float),np.asarray(faces),np.asarray(selected_faces)
    if (v.ndim!=2 or v.shape[1]!=3 or not np.isfinite(v).all()
            or f.ndim!=2 or f.shape[1]!=3 or not len(f) or not np.issubdtype(f.dtype,np.integer)
            or f.min()<0 or f.max()>=len(v) or s.ndim!=1 or not len(s)
            or not np.issubdtype(s.dtype,np.integer) or s.min()<0 or s.max()>=len(f)
            or len(np.unique(s))!=len(s) or type(sweeps) is not int or not 1<=sweeps<=20
            or not np.isfinite(plane_tolerance_mm) or plane_tolerance_mm<=0):
        raise ValueError('Valid mesh, selected faces and bounded settings required')
    output=f.copy();chosen=set(s.tolist());history=[]

    def quality(triangles):
        p=v[triangles]
        area2=np.linalg.norm(np.cross(p[:,1]-p[:,0],p[:,2]-p[:,0]),axis=1)
        denominator=np.sum((np.roll(p,-1,axis=1)-p)**2,axis=(1,2))
        return 2*np.sqrt(3)*area2/np.maximum(denominator,1e-30)

    if np.any(quality(f)<=0):
        raise ValueError('Nondegenerate source triangles required')
    for sweep in range(sweeps):
        adjacency={}
        for i,face in enumerate(output):
            for a,b in zip(face,np.roll(face,-1)):
                adjacency.setdefault(tuple(sorted((int(a),int(b)))),[]).append(i)
        touched=set();count=0
        for edge,pair in list(adjacency.items()):
            if len(pair)!=2 or not set(pair)<=chosen or touched.intersection(pair):continue
            i,j=pair;a,b=edge
            c=next(int(x) for x in output[i] if x not in edge)
            d=next(int(x) for x in output[j] if x not in edge)
            if c==d or tuple(sorted((c,d))) in adjacency:continue
            old=output[[i,j]];p=v[old]
            normal=np.cross(p[0,1]-p[0,0],p[0,2]-p[0,0]);normal/=np.linalg.norm(normal)
            offset=float(abs((v[d]-v[a])@normal))
            if offset>plane_tolerance_mm:continue
            # Convexity in the old triangle plane.
            sa=np.cross(v[d]-v[c],v[a]-v[c])@normal
            sb=np.cross(v[d]-v[c],v[b]-v[c])@normal
            if sa*sb>=0:continue
            proposed=np.array([[c,d,a],[d,c,b]])
            for k in range(2):
                q=v[proposed[k]]
                if np.cross(q[1]-q[0],q[2]-q[0])@normal<0:proposed[k]=proposed[k,::-1]
            if np.min(quality(proposed))<=np.min(quality(old))+1e-12:continue
            # A consistently oriented source is required locally.
            if np.cross(p[1,1]-p[1,0],p[1,2]-p[1,0])@normal<=0:continue
            output[[i,j]]=proposed;touched.update(pair);count+=1
            adjacency[tuple(sorted((c,d)))]=pair
            history.append(dict(sweep=sweep,face_ids=pair,old_faces=old.tolist(),
                new_faces=proposed.tolist(),plane_offset_mm=offset))
        if not count:break
    return output,dict(status='CANDIDATE',method='selected-near-planar-min-quality-flips/1',
        flips=len(history),history=history,plane_tolerance_mm=plane_tolerance_mm,
        vertices_unchanged=True,unselected_faces_unchanged=bool(np.array_equal(output[np.setdiff1d(np.arange(len(f)),s)],f[np.setdiff1d(np.arange(len(f)),s)])),
        minimum_quality_before=float(quality(f[s]).min()),minimum_quality_after=float(quality(output[s]).min()),
        self_contact='NOT RUN',anatomical_validation='NOT RUN')
