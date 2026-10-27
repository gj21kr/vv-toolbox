"""Source-bound noncircular lumen profiles without moving the original surface."""
import numpy as np

from .projected_annulus import contains
from .surface_indexing import exact_vertex_index_copy


def extract_source_sections(mesh, points, *, tangent_half_window_mm=None, include_all_contours=False, include_endpoints=False):
    """Retain complete unique enclosing contours in local chord-normal planes.

    Endpoints are optional: source caps may coincide with those planes.
    These profiles are measurements, not an accepted connected surface model.
    """
    if type(include_all_contours) is not bool or type(include_endpoints) is not bool:
        raise ValueError('Explicit boolean contour inventory option required')
    points=np.asarray(points,dtype=float)
    if points.ndim!=2 or points.shape[1]!=3 or len(points)<3 or not np.isfinite(points).all():
        raise ValueError('Finite path with at least three points required')
    arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(points,axis=0),axis=1))]
    if np.any(np.diff(arc)<=0):
        raise ValueError('Distinct consecutive path stations required')
    if tangent_half_window_mm is not None and (
            type(tangent_half_window_mm) not in (float,int)
            or not np.isfinite(tangent_half_window_mm) or tangent_half_window_mm<=0):
        raise ValueError('Positive finite tangent half-window required')
    surface,indexing=exact_vertex_index_copy(mesh)
    output=dict(schema='vv-toolbox.source-sections/1',indexing=indexing,
                coordinate_units='mm',plane_definition='previous-to-next station chord',
                profiles=[],endpoint_sections='ATTEMPTED' if include_endpoints else 'NOT RUN',loft_surface='NOT RUN',
                anatomical_validation='NOT RUN')
    if tangent_half_window_mm is not None:
        output.update(plane_definition='physical arclength window chord, clipped at path ends',
                      tangent_half_window_mm=tangent_half_window_mm)
    if include_endpoints:output['endpoint_plane_definition']='one-sided adjacent chord; physical window if requested'
    for i in (range(len(points)) if include_endpoints else range(1,len(points)-1)):
        row=dict(index=i,status='UNKNOWN',origin_mm=points[i].tolist())
        normal=points[min(i+1,len(points)-1)]-points[max(i-1,0)]
        if tangent_half_window_mm is not None:
            lo=max(0.,arc[i]-tangent_half_window_mm)
            hi=min(arc[-1],arc[i]+tangent_half_window_mm)
            normal=np.array([np.interp(hi,arc,points[:,k])-np.interp(lo,arc,points[:,k]) for k in range(3)])
        length=np.linalg.norm(normal)
        if length<=1e-12:
            row['reason']='zero local chord tangent';output['profiles'].append(row);continue
        normal/=length
        u=np.cross(normal,np.eye(3)[np.argmin(abs(normal))]);u/=np.linalg.norm(u)
        v=np.cross(normal,u)
        section=surface.section(plane_origin=points[i],plane_normal=normal)
        paths=[] if section is None else section.discrete
        candidates=[]
        inventory=[]
        for contour_index,path in enumerate(paths):
            closed=len(path)>=4 and np.linalg.norm(path[0]-path[-1])<=1e-6
            if not closed:
                if include_all_contours:
                    inventory.append(dict(index=contour_index,closed=False,
                        contains_origin=None,points_mm=path.tolist()))
                continue
            xy=(path-points[i])@np.array([u,v]).T
            encloses=bool(contains(xy,np.zeros((1,2)))[0])
            if encloses:candidates.append(xy)
            if include_all_contours:
                cross=xy[:-1,0]*xy[1:,1]-xy[1:,0]*xy[:-1,1]
                inventory.append(dict(index=contour_index,closed=True,
                    contains_origin=encloses,area_mm2=float(abs(cross.sum()/2)),
                    points_mm=path.tolist(),anatomical_branch_identity='UNKNOWN'))
        if include_all_contours:
            row['all_contours']=inventory
        row.update(contour_count=len(paths),enclosing_contour_count=len(candidates),
                   normal=normal.tolist(),u=u.tolist(),v=v.tolist())
        if len(candidates)!=1:
            row['reason']='unique enclosing closed contour required'
        else:
            xy=candidates[0]
            a,b=xy[:-1],xy[1:]
            delta=b-a;norm2=np.sum(delta*delta,axis=1)
            cross=a[:,0]*b[:,1]-b[:,0]*a[:,1]
            signed_area=float(cross.sum()/2)
            if np.any(norm2<=1e-24) or abs(signed_area)<=1e-12:
                row['reason']='degenerate contour'
            else:
                centroid=((a+b)*cross[:,None]).sum(axis=0)/(6*signed_area)
                fractions=np.clip(-np.sum(a*delta,axis=1)/norm2,0,1)
                nearest=np.linalg.norm(a+fractions[:,None]*delta,axis=1).min()
                restored=points[i]+xy[:,0,None]*u+xy[:,1,None]*v
                row.update(status='MEASURED',contour_uv_mm=xy.tolist(),
                    contour_xyz_mm=restored.tolist(),area_mm2=abs(signed_area),
                    area_equivalent_radius_mm=float(np.sqrt(abs(signed_area)/np.pi)),
                    centroid_uv_mm=centroid.tolist(),
                    centroid_xyz_mm=(points[i]+centroid[0]*u+centroid[1]*v).tolist(),
                    center_boundary_distance_mm=float(nearest))
        output['profiles'].append(row)
    output['counts']={s:sum(p['status']==s for p in output['profiles'])
                      for s in ('MEASURED','UNKNOWN')}
    return output
