"""Compare contact face sets on one unchanged reference surface."""
import numpy as np


def compare_contact_footprints(reference_triangles, before, after):
    """Measure supporting reference facets, not intersection area or lumen opening."""
    triangles=np.asarray(reference_triangles,dtype=float)
    if (triangles.ndim!=3 or triangles.shape[1:]!=(3,3) or not len(triangles)
            or not np.isfinite(triangles).all()):
        raise ValueError('Finite reference triangles required')
    sets=[]
    for values in (before,after):
        if not isinstance(values,list) or any(type(i) is not int or not 0<=i<len(triangles) for i in values):
            raise ValueError('Known integer reference face IDs required')
        sets.append(set(values))
    old,new=sets
    areas=np.linalg.norm(np.cross(triangles[:,1]-triangles[:,0],
                                 triangles[:,2]-triangles[:,0]),axis=1)/2
    if any(areas[i]<=1e-12 for i in old|new):
        raise ValueError('Degenerate contact support faces')
    centers=triangles.mean(axis=1)
    def measure(indices):
        ids=sorted(indices)
        area=float(areas[ids].sum())
        center=(centers[ids]*areas[ids,None]).sum(axis=0)/area if ids else None
        return dict(face_ids=ids,face_count=len(ids),support_area_mm2=area,
                    support_centroid_mm=None if center is None else center.tolist())
    a,b=measure(old),measure(new)
    return dict(before=a,after=b,retained=measure(old&new),lost=measure(old-new),
                gained=measure(new-old),face_jaccard=len(old&new)/len(old|new) if old|new else None,
                support_centroid_shift_mm=float(np.linalg.norm(np.array(a['support_centroid_mm'])-
                    np.array(b['support_centroid_mm']))) if old and new else None,
                scope='Supporting original facets, not actual contact area or anatomical opening',
                anatomical_junction_acceptance='NOT RUN')
