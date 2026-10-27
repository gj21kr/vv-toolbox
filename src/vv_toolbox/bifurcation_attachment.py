"""Necessary attachment checks for an explicit multi-branch sac design."""
import numpy as np

from .bifurcation_saccular import validate_bifurcation_saccular_spec
from .saccular_surface import _parent_field


def inspect_bifurcation_attachment(case, spec, *, burial_margin_mm):
    """Inspect sampled attachment and conservative outlet support separation.

    PASS here is not a generated surface, a patent lumen, or anatomy approval.
    The parent is the union of centerline/radius capsules, not the atlas mesh.
    """
    validate_bifurcation_saccular_spec(case, spec)
    if (type(burial_margin_mm) not in (int, float)
            or not np.isfinite(burial_margin_mm) or burial_margin_mm <= 0):
        raise ValueError('Explicit positive finite burial margin required')
    p, neck = spec['parameters'], spec['neck']
    ids = {b['edge_id'] for b in spec['branch_constraints']}
    branches = [e for e in case['edges'] if e['id'] in ids]
    rim = np.asarray(neck['curve_mm'])
    normal = np.asarray(neck['normal'])
    buried = rim-normal*p['blending_extent_mm']

    def union(points):
        return np.minimum.reduce([
            _parent_field(points, np.asarray(e['centerline_mm']), np.asarray(e['radii_mm']))
            for e in branches])

    rim_values, buried_values = union(rim), union(buried)
    invaded = np.flatnonzero(rim_values < -1e-6).tolist()
    unburied = np.flatnonzero(buried_values > -burial_margin_mm).tolist()
    # Bound the complete loft and blend expansion in the declared neck frame.
    # A sphere enclosing each outlet disk gives a conservative separation test.
    basis = np.column_stack([neck['width_axis'], neck['depth_axis'], normal])
    blend = p['blending_extent_mm']
    lower = np.array([-p['dome_width_mm']/2, -p['dome_depth_mm']/2, -blend])-blend
    upper = np.array([p['dome_width_mm']/2, p['dome_depth_mm']/2,
                      p['height_perpendicular_mm']])+blend
    outlets = []
    for branch in spec['branch_constraints']:
        local = (np.asarray(branch['outlet_center_mm'])-neck['center_mm']) @ basis
        distance = np.linalg.norm(np.maximum(np.maximum(lower-local, local-upper), 0))
        clearance = float(distance-branch['outlet_radius_mm'])
        outlets.append(dict(edge_id=branch['edge_id'], clearance_lower_bound_mm=clearance,
                            status='PASS' if clearance > 0 else 'UNKNOWN'))
    status = 'FAIL' if invaded or unburied else (
        'PASS' if all(o['status']=='PASS' for o in outlets) else 'UNKNOWN')
    return dict(schema='vv-toolbox.bifurcation-attachment/1', status=status,
        case_revision=spec['case_revision'], specification=spec,
        parent_representation='union of incident centerline-radius capsules',
        rim=dict(sample_count=len(rim), interior_indices=invaded,
                 field_values_mm=rim_values.tolist(), tolerance_mm=1e-6),
        buried_rim=dict(sample_count=len(buried), insufficient_burial_indices=unburied,
                        field_values_mm=buried_values.tolist(), margin_mm=float(burial_margin_mm)),
        outlets=outlets, geometry_status='NOT GENERATED', accepted_for_generation=False,
        checks=dict(continuous_attachment='NOT RUN', branch_patency='NOT RUN',
                    nonincident_clearance='NOT RUN', anatomical_acceptance='NOT RUN'),
        limitation='Sampled necessary conditions only. Outlet UNKNOWN is conservative support overlap, '
                   'not a proven intersection. Atlas surface attachment is not inspected.')
