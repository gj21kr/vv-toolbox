"""Measure stored circular profiles in local normal planes of original surfaces."""
import numpy as np
import trimesh

from .surface_indexing import exact_vertex_index_copy


def inspect_radius_sections(mesh, points, radii, *, samples=64, tolerance_mm=1e-6):
    """Check finite ring samples; never infer continuous tube-wall containment."""
    points=np.asarray(points,dtype=float)
    radii=np.asarray(radii,dtype=float)
    if (points.ndim!=2 or points.shape[1]!=3 or len(points)<3
            or radii.shape!=(len(points),) or not np.isfinite(points).all()
            or not np.isfinite(radii).all() or np.any(radii<=0)
            or type(samples) is not int or not 8<=samples<=1024
            or not np.isfinite(tolerance_mm) or tolerance_mm<=0):
        raise ValueError('Finite path, positive radii, tolerance and 8–1024 ring samples required')
    surface,indexing=exact_vertex_index_copy(mesh)
    report=dict(status='UNKNOWN',method='normal-plane-radius-rings/1',
                scope='Finite circular-profile samples at non-endpoint centerline stations',
                samples_per_ring=samples,tolerance_mm=float(tolerance_mm),
                indexing=indexing,rows=[],continuous_tube_wall='NOT RUN',
                anatomical_validation='NOT RUN',surface_self_intersection='NOT RUN')
    if not indexing['usable_for_sampled_containment']:
        return dict(report,reason='Closed consistently oriented nondegenerate surface required')
    angles=np.arange(samples)*2*np.pi/samples
    for i in range(1,len(points)-1):
        tangent=points[i+1]-points[i-1]
        norm=np.linalg.norm(tangent)
        row=dict(index=i,radius_mm=float(radii[i]),status='UNKNOWN')
        if norm<=1e-12:
            row['reason']='Zero local chord tangent'
        else:
            tangent/=norm
            u=np.cross(tangent,np.eye(3)[np.argmin(abs(tangent))]);u/=np.linalg.norm(u)
            v=np.cross(tangent,u)
            ring=points[i]+radii[i]*(np.cos(angles)[:,None]*u+np.sin(angles)[:,None]*v)
            _,distance,_=trimesh.proximity.closest_point(surface,ring)
            inside=surface.contains(ring)
            reliable=np.isfinite(distance)&(distance>tolerance_mm)
            outside=reliable&~inside
            witnesses=np.flatnonzero(outside)
            row.update(status='FAIL' if len(witnesses) else 'UNKNOWN' if not reliable.all() else 'PASS',
                       inside_samples=int((inside&reliable).sum()),
                       outside_samples=int(outside.sum()),ambiguous_samples=int((~reliable).sum()),
                       normal=tangent.tolist(),center_mm=points[i].tolist(),
                       outside_witnesses=[dict(sample=int(k),position_mm=ring[k].tolist(),
                           distance_to_surface_mm=float(distance[k])) for k in witnesses])
        report['rows'].append(row)
    states=[r['status'] for r in report['rows']]
    report['status']='FAIL' if 'FAIL' in states else 'UNKNOWN' if 'UNKNOWN' in states else 'PASS'
    report['counts']={s:states.count(s) for s in ('PASS','FAIL','UNKNOWN')}
    return report
