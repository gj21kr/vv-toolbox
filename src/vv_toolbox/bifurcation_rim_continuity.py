"""Bound the capsule-field residual along every chord of a closed rim."""
import numpy as np
from .bifurcation_rim import project_bifurcation_rim
from .saccular_surface import _parent_field


def inspect_projected_rim(case,spec,projection,*,tolerance_mm,max_samples=200000):
    if type(tolerance_mm) not in (int,float) or not np.isfinite(tolerance_mm) or tolerance_mm<=0:
        raise ValueError('Positive finite field tolerance required')
    if type(max_samples) is not int or not 1<=max_samples<=2000000:
        raise ValueError('Explicit sample budget between 1 and 2000000 required')
    lower,upper=projection['projection_bounds_mm']
    expected=project_bifurcation_rim(case,spec,lower_mm=lower,upper_mm=upper,step_mm=projection['step_mm'])
    if projection!=expected:raise ValueError('Projected rim differs from source-bound reconstruction')
    if projection['curve_mm'] is None:raise ValueError('Complete projected rim required')
    curve=np.asarray(projection['curve_mm']);next_points=np.roll(curve,-1,axis=0)
    lengths=np.linalg.norm(next_points-curve,axis=1)
    if np.any(lengths<=1e-9):raise ValueError('Distinct adjacent rim points required')
    ids={b['edge_id'] for b in spec['branch_constraints']}
    paths=[(np.asarray(e['centerline_mm']),np.asarray(e['radii_mm'])) for e in case['edges'] if e['id'] in ids]
    # Each finite-segment distance is 1-Lipschitz. Its clipped linear radius
    # has slope |dr|/length. Min over segments/branches retains the max bound.
    lipschitz=max(float(np.max(1+np.abs(np.diff(r))/np.linalg.norm(np.diff(p,axis=0),axis=1))) for p,r in paths)
    subdivisions=np.maximum(1,np.ceil(lipschitz*lengths/tolerance_mm))
    if not np.isfinite(subdivisions).all() or np.sum(subdivisions+1)>max_samples:
        raise ValueError('Rim continuity sample budget exceeded')
    rows=[]
    for index,(a,b,length,subdivisions_count) in enumerate(zip(curve,next_points,lengths,subdivisions)):
        count=int(subdivisions_count)
        points=a+np.linspace(0,1,count+1)[:,None]*(b-a)
        field=np.minimum.reduce([_parent_field(points,*p) for p in paths])
        sampled=float(np.max(np.abs(field)))
        bound=sampled+lipschitz*float(length)/(2*count)
        rows.append(dict(chord_index=index,length_mm=float(length),sample_count=count+1,
            maximum_sampled_absolute_field_mm=sampled,continuous_absolute_field_upper_bound_mm=bound,
            status='PASS' if bound<=tolerance_mm else 'FAIL'))
    return dict(schema='vv-toolbox.bifurcation-rim-continuity/1',case_revision=spec['case_revision'],
        status='PASS' if all(r['status']=='PASS' for r in rows) else 'FAIL',closed_chord_count=len(rows),
        tolerance_mm=float(tolerance_mm),field_lipschitz_bound=lipschitz,
        total_sample_count=sum(r['sample_count'] for r in rows),chords=rows,
        maximum_continuous_absolute_field_bound_mm=max(r['continuous_absolute_field_upper_bound_mm'] for r in rows),
        accepted_for_generation=False,
        scope='All straight chords including last-to-first; capsule scalar-field residual bound',
        limitation='Not exact Euclidean distance to a tapered union surface, smoothness, ray completeness, '
                   'atlas mesh attachment, or a generated lumen. Floating-point arithmetic is not interval certified.')
