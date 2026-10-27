"""Surface intersection screening; absence of intersection is not no containment."""
import numpy as np
from scipy.spatial import cKDTree
from .triangle_contact import triangle_contacts


def inspect_pair_contact(first, second, *, tolerance_mm=1e-8, max_pairs=2_000_000):
    """Input two (N,3,3) triangle arrays in the same millimetre frame."""
    a,b=np.asarray(first,dtype=float),np.asarray(second,dtype=float)
    if (any(t.ndim!=3 or t.shape[1:]!=(3,3) or not len(t) or not np.isfinite(t).all() for t in (a,b)) or
            not np.isfinite(tolerance_mm) or tolerance_mm<=0 or type(max_pairs) is not int or max_pairs<1):
        raise ValueError('Finite triangle arrays and positive limits required')
    contact=[];checked=0;complete=True;degenerate=False
    alo,ahi=a.min(axis=1),a.max(axis=1);blo,bhi=b.min(axis=1),b.max(axis=1)
    centers=b.mean(axis=1);radii=np.linalg.norm(b-centers[:,None],axis=2).max(axis=1)
    tree=cKDTree(centers);maximum=float(radii.max())
    an=np.linalg.norm(np.cross(a[:,1]-a[:,0],a[:,2]-a[:,0]),axis=1)
    bn=np.linalg.norm(np.cross(b[:,1]-b[:,0],b[:,2]-b[:,0]),axis=1)
    # Any triangle pair that survives the existing per-pair AABB test must
    # also intersect the second surface's overall bounds. Preserve index order.
    active=np.flatnonzero(np.all(alo<=bhi.max(axis=0)+tolerance_mm,axis=1)&
                          np.all(ahi>=blo.min(axis=0)-tolerance_mm,axis=1))
    for i in active:
        triangle=a[i]
        center=triangle.mean(axis=0)
        radius=float(np.linalg.norm(triangle-center,axis=1).max())
        ids=np.asarray(tree.query_ball_point(center,radius+maximum+tolerance_mm),dtype=int)
        ids=ids[np.all(blo[ids]<=ahi[i]+tolerance_mm,axis=1)&
                np.all(bhi[ids]>=alo[i]-tolerance_mm,axis=1)]
        if checked+len(ids)>max_pairs:
            complete=False
            break
        valid=(bn[ids]>1e-14)&(an[i]>1e-14)
        degenerate=degenerate or not bool(np.all(valid))
        ids=ids[valid]
        if len(ids):
            hit=triangle_contacts(np.broadcast_to(triangle,(len(ids),3,3)),b[ids],tolerance_mm)
            contact.extend([int(i),int(j)] for j in ids[hit])
            checked+=len(ids)
    complete=complete and not degenerate
    return dict(status='CONTACT_DETECTED' if contact else 'NO_SURFACE_CONTACT_DETECTED' if complete else 'UNKNOWN',
                complete=complete,checked_pairs=checked,contact_pairs=contact,
                degenerate_candidates=degenerate,tolerance_mm=tolerance_mm,max_pairs=max_pairs,
                containment='NOT RUN',
                scope='Surface intersections only; fully contained disjoint surfaces can overlap in volume.')
