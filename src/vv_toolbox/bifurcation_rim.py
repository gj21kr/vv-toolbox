"""Projected neck-rim samples on a branch envelope; separate from planar spec."""
import numpy as np
from scipy.optimize import brentq
from .bifurcation_saccular import validate_bifurcation_saccular_spec
from .saccular_surface import _parent_field


def project_bifurcation_rim(case,spec,*,lower_mm,upper_mm,step_mm):
    validate_bifurcation_saccular_spec(case,spec)
    if any(type(v) not in (int,float) or not np.isfinite(v) for v in (lower_mm,upper_mm,step_mm)):
        raise ValueError('Finite explicit projection bounds and step required')
    if lower_mm>=upper_mm or step_mm<=0:raise ValueError('Increasing projection bounds and positive step required')
    count=int(np.ceil((upper_mm-lower_mm)/step_mm))
    if count>10000:raise ValueError('Projection sampling budget exceeded')
    ids={b['edge_id'] for b in spec['branch_constraints']}
    paths=[(np.asarray(e['centerline_mm']),np.asarray(e['radii_mm'])) for e in case['edges'] if e['id'] in ids]
    def field(points):return np.minimum.reduce([_parent_field(np.atleast_2d(points),*p) for p in paths])
    normal=np.asarray(spec['neck']['normal']);rim=np.asarray(spec['neck']['curve_mm'])
    offsets=np.linspace(lower_mm,upper_mm,count+1);rows=[]
    for index,point in enumerate(rim):
        values=field(point+offsets[:,None]*normal)
        exits=np.flatnonzero((values[:-1]<0)&(values[1:]>=0))
        roots=[float(brentq(lambda t:float(field(point+t*normal)[0]),offsets[i],offsets[i+1],xtol=1e-10)) for i in exits]
        rows.append(dict(sample_index=index,status='PASS' if len(roots)==1 else 'UNKNOWN',
            sampled_exit_offsets_mm=roots,
            point_mm=(point+roots[0]*normal).tolist() if len(roots)==1 else None))
    complete=all(row['status']=='PASS' for row in rows)
    curve=[row['point_mm'] for row in rows] if complete else None
    return dict(schema='vv-toolbox.bifurcation-projected-rim/1',case_revision=spec['case_revision'],
        status='CANDIDATE' if complete else 'UNKNOWN',projection_bounds_mm=[float(lower_mm),float(upper_mm)],
        step_mm=float(step_mm),sample_count=len(rows),resolved_sample_count=sum(r['status']=='PASS' for r in rows),
        samples=rows,curve_mm=curve,accepted_for_generation=False,
        dimensional_convention='Original planar ellipse preserved in projection; actual 3D contour is distinct',
        continuous_attachment='NOT RUN',geometry_generation='NOT RUN',
        limitation='Finite ray sampling may miss crossings. Missing or multiple sampled exits are unresolved. '
                   'No interpolated curve, lumen, surface or anatomical acceptance is implied.')
