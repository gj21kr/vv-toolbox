"""Conservative sac-support clearance against every nonincident path."""
import numpy as np

from .bifurcation_saccular import validate_bifurcation_saccular_spec


def _segment_box_distance(a, b, lower, upper):
    """Minimum distance over the whole segment, not just its endpoints."""
    a,b,lower,upper=map(lambda v:np.asarray(v,dtype=float),(a,b,lower,upper))
    direction=b-a
    cuts=[0.,1.]
    for axis in range(3):
        if direction[axis]!=0:
            cuts.extend(float(t) for t in ((lower[axis]-a[axis])/direction[axis],
                                           (upper[axis]-a[axis])/direction[axis]) if 0<t<1)
    cuts=sorted(set(cuts));best=float('inf')
    for left,right in zip(cuts,cuts[1:]):
        middle=a+(left+right)*.5*direction
        active=(middle<lower)|(middle>upper)
        boundary=np.where(middle<lower,lower,upper)
        offset=(a-boundary)[active];slope=direction[active]
        denominator=float(slope@slope)
        t=float(np.clip(-(offset@slope)/denominator,left,right)) if denominator else left
        point=a+t*direction
        delta=np.maximum(np.maximum(lower-point,point-upper),0)
        best=min(best,float(delta@delta))
    return float(np.sqrt(best))


def inspect_bifurcation_clearance(case,spec,*,margin_mm):
    validate_bifurcation_saccular_spec(case,spec)
    if type(margin_mm) not in (int,float) or not np.isfinite(margin_mm) or margin_mm<0:
        raise ValueError('Finite nonnegative clearance margin required')
    p,neck=spec['parameters'],spec['neck']
    basis=np.column_stack([neck['width_axis'],neck['depth_axis'],neck['normal']])
    blend=p['blending_extent_mm']
    lower=np.array([-p['dome_width_mm']/2,-p['dome_depth_mm']/2,-blend])-blend
    upper=np.array([p['dome_width_mm']/2,p['dome_depth_mm']/2,p['height_perpendicular_mm']])+blend
    incident={b['edge_id'] for b in spec['branch_constraints']}
    checks=[]
    for edge in sorted(case['edges'],key=lambda e:e['id']):
        if edge['id'] in incident:continue
        if edge['centerline_mm'] is None:
            checks.append(dict(edge_id=edge['id'],status='UNKNOWN',reason='unresolved centerline',
                               clearance_lower_bound_mm=None));continue
        points=(np.asarray(edge['centerline_mm'])-neck['center_mm'])@basis
        radii=edge['radii_mm']
        bound=min(_segment_box_distance(a,b,lower,upper)-max(r,s)
                  for a,b,r,s in zip(points,points[1:],radii,radii[1:]))
        checks.append(dict(edge_id=edge['id'],status='PASS' if bound>margin_mm else 'UNKNOWN',
                           reason='conservative support clearance',clearance_lower_bound_mm=float(bound)))
    return dict(schema='vv-toolbox.bifurcation-clearance/1',case_revision=spec['case_revision'],
        status=('PASS' if all(c['status']=='PASS' for c in checks) else 'UNKNOWN') if checks else 'NOT RUN',
        margin_mm=float(margin_mm),checked_edge_count=len(checks),edges=checks,
        support_bounds_neck_frame_mm=[lower.tolist(),upper.tolist()],
        scope='Sac and blend support versus all nonincident centerline-radius envelopes',
        limitation='Not atlas mesh collision detection or whole-case nonoverlap. UNKNOWN does not prove collision.')
