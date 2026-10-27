"""Triangulate two explicitly ordered rings using a shared angular parameter."""
import numpy as np


def stitch_rings(first_ids,first_angles,second_ids,second_angles):
    """Return an annular strip; geometry validity is a separate check.

    Angles must start at the same angular seam (zero), increase strictly and
    remain below 2*pi. IDs refer to the caller's original vertex array.
    """
    rings=[]
    for ids,angles in ((first_ids,first_angles),(second_ids,second_angles)):
        ids=np.asarray(ids);angles=np.asarray(angles,dtype=float)
        if (ids.ndim!=1 or len(ids)<3 or not np.issubdtype(ids.dtype,np.integer)
                or np.any(ids<0) or len(set(ids.tolist()))!=len(ids)
                or angles.shape!=ids.shape or not np.isfinite(angles).all()
                or abs(angles[0])>1e-12 or np.any(np.diff(angles)<=0)
                or angles[-1]>=2*np.pi):
            raise ValueError('unique ring IDs and strictly ordered angles from zero required')
        rings.append((ids,angles))
    a,ta=rings[0];b,tb=rings[1]
    if set(a.tolist())&set(b.tolist()):
        raise ValueError('rings must have disjoint vertex IDs')
    i=j=0;faces=[]
    while i<len(a) or j<len(b):
        next_a=ta[i+1] if i+1<len(a) else 2*np.pi if i<len(a) else np.inf
        next_b=tb[j+1] if j+1<len(b) else 2*np.pi if j<len(b) else np.inf
        ai,bj=int(a[i%len(a)]),int(b[j%len(b)])
        if next_a<=next_b:
            faces.append([ai,int(a[(i+1)%len(a)]),bj]);i+=1
        else:
            faces.append([ai,int(b[(j+1)%len(b)]),bj]);j+=1
    return np.array(faces,dtype=np.int64)
