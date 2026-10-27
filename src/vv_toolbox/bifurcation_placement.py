"""Explicit bounded engineering placement scan, never anatomical inference."""
from copy import deepcopy
import numpy as np
from .bifurcation_saccular import validate_bifurcation_saccular_spec
from .saccular_surface import _parent_field


def scan_bifurcation_placement(case,spec,*,offsets_mm,burial_margin_mm):
    validate_bifurcation_saccular_spec(case,spec)
    if type(burial_margin_mm) not in (int,float) or not np.isfinite(burial_margin_mm) or burial_margin_mm<=0:
        raise ValueError('Positive finite burial margin required')
    if not isinstance(offsets_mm,list) or not 1<=len(offsets_mm)<=1001 or any(
            type(v) not in (int,float) or not np.isfinite(v) for v in offsets_mm):
        raise ValueError('Explicit list of 1 to 1001 finite offsets required')
    if any(b<=a for a,b in zip(offsets_mm,offsets_mm[1:])):
        raise ValueError('Strictly increasing offsets required')
    ids={b['edge_id'] for b in spec['branch_constraints']}
    paths=[(np.asarray(e['centerline_mm']),np.asarray(e['radii_mm'])) for e in case['edges'] if e['id'] in ids]
    normal=np.asarray(spec['neck']['normal']);rim=np.asarray(spec['neck']['curve_mm'])
    center=np.asarray(spec['neck']['center_mm']);blend=spec['parameters']['blending_extent_mm']
    rows=[]
    for offset in offsets_mm:
        shifted=rim+normal*offset
        points=np.vstack([shifted,shifted-normal*blend])
        field=np.minimum.reduce([_parent_field(points,*path) for path in paths])
        outside,inside=field[:len(rim)],field[len(rim):]
        invaded=int(np.count_nonzero(outside < -1e-6))
        unburied=int(np.count_nonzero(inside > -burial_margin_mm))
        rows.append(dict(offset_mm=float(offset),neck_center_mm=(center+normal*offset).tolist(),
            status='PASS' if not invaded and not unburied else 'FAIL',
            interior_rim_samples=invaded,insufficient_burial_samples=unburied,
            minimum_rim_field_mm=float(outside.min()),maximum_buried_field_mm=float(inside.max())))
    return dict(schema='vv-toolbox.bifurcation-placement-scan/1',case_revision=spec['case_revision'],
        source_specification=deepcopy(spec),burial_margin_mm=float(burial_margin_mm),
        tested_count=len(rows),passing_offsets_mm=[r['offset_mm'] for r in rows if r['status']=='PASS'],
        samples=rows,accepted_for_generation=False,geometry_status='NOT GENERATED',
        limitation='Discrete sampled attachment only, not a continuous feasible interval. '
                   'Direction and dimensions unchanged. Outlet and surrounding clearance must be rechecked. '
                   'No anatomical placement or automatic application.')
