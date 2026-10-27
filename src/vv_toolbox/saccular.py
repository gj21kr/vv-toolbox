"""Source-bound manual sac specifications, not generated or accepted lumen geometry."""
from copy import deepcopy
import math

import numpy as np

from .case_contract import validate_case
from .case_io import case_digest
from .lesions import REGIONS


def _vector(value, name):
    if (not isinstance(value, (list, tuple)) or len(value) != 3 or
            any(type(x) not in (int, float) or not math.isfinite(x) for x in value)):
        raise ValueError(f'{name}: finite three-vector required')
    return np.asarray(value, dtype=float)


def _positive(value, name):
    if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
        raise ValueError(f'{name}: positive finite value required')


def saccular_spec(case, *, lesion_id, edge_id, region, station_mm,
                  neck_center_mm, outward_normal, width_direction,
                  neck_width_mm, neck_depth_mm, height_perpendicular_mm,
                  dome_width_mm, dome_depth_mm, blending_extent_mm):
    """Describe an explicit elliptical neck and orthogonal local sac frame.

    This is a design input, not a case lesion. No parent surface intersection,
    open lumen, nonoverlap, or clinical size range is inferred from these inputs.
    """
    validate_case(case)
    if not isinstance(lesion_id, str) or not lesion_id.strip():
        raise ValueError('lesion ID required')
    if any(l.get('lesion_id') == lesion_id for l in case.get('lesions', [])):
        raise ValueError('duplicate lesion ID')
    if region not in REGIONS:
        raise ValueError('explicit supported region required')
    for name, value in dict(station_mm=station_mm, neck_width_mm=neck_width_mm,
            neck_depth_mm=neck_depth_mm, height_perpendicular_mm=height_perpendicular_mm,
            dome_width_mm=dome_width_mm, dome_depth_mm=dome_depth_mm,
            blending_extent_mm=blending_extent_mm).items():
        _positive(value, name)
    if dome_width_mm < neck_width_mm or dome_depth_mm < neck_depth_mm:
        raise ValueError('requested maximum dome dimensions cannot be smaller than neck dimensions')
    edge = next((e for e in case['edges'] if e['id'] == edge_id), None)
    if edge is None or edge['centerline_mm'] is None:
        raise ValueError('resolved parent edge required')
    points = np.asarray(edge['centerline_mm'], dtype=float)
    lengths = np.linalg.norm(np.diff(points, axis=0), axis=1)
    stations = np.r_[0., np.cumsum(lengths)]
    if station_mm >= stations[-1]:
        raise ValueError('interior parent station required; bifurcation attachment needs a separate contract')
    index = int(np.searchsorted(stations, station_mm, side='right') - 1)
    fraction = float((station_mm - stations[index]) / lengths[index])
    anchor = points[index] + fraction * (points[index+1] - points[index])
    center = _vector(neck_center_mm, 'neck center')
    normal = _vector(outward_normal, 'outward normal')
    width = _vector(width_direction, 'width direction')
    if not np.isclose(np.linalg.norm(normal), 1., atol=1e-8, rtol=0):
        raise ValueError('unit outward normal required')
    if not np.isclose(np.linalg.norm(width), 1., atol=1e-8, rtol=0):
        raise ValueError('unit width direction required')
    if abs(float(normal @ width)) > 1e-8:
        raise ValueError('width direction must lie in neck plane')
    depth = np.cross(normal, width)
    theta = np.arange(64) * (2*math.pi/64)
    curve = (center + np.cos(theta)[:, None]*width*neck_width_mm/2
             + np.sin(theta)[:, None]*depth*neck_depth_mm/2)
    parameters = dict(lesion_id=lesion_id, edge_id=edge_id, region=region,
        station_mm=station_mm, neck_center_mm=list(neck_center_mm),
        outward_normal=list(outward_normal), width_direction=list(width_direction),
        neck_width_mm=neck_width_mm, neck_depth_mm=neck_depth_mm,
        height_perpendicular_mm=height_perpendicular_mm,
        dome_width_mm=dome_width_mm, dome_depth_mm=dome_depth_mm,
        blending_extent_mm=blending_extent_mm)
    mean_diameter = neck_width_mm/2 + neck_depth_mm/2
    aspect_ratio = height_perpendicular_mm/mean_diameter
    if not np.isfinite(curve).all() or not math.isfinite(aspect_ratio):
        raise ValueError('derived neck geometry or aspect ratio is nonfinite')
    return dict(schema='vv-toolbox.saccular-spec/1', type='saccular',
        mode='manual_synthetic', case_revision=case_digest(case),
        base_model_id=case['base_model_id'], frame=deepcopy(case['frame']),
        parameters=parameters,
        parent_anchor=dict(edge_id=edge_id, interval_index=index, fraction=fraction,
                           position_mm=anchor.tolist()),
        neck=dict(center_mm=center.tolist(), normal=normal.tolist(),
                  width_axis=width.tolist(), depth_axis=depth.tolist(),
                  curve_mm=curve.tolist(), curve_closed=True,
                  curve_convention='64 ordered ellipse samples; last connects to first',
                  average_diameter_mm=mean_diameter,
                  average_diameter_convention='arithmetic mean of declared ellipse axis diameters',
                  max_width_mm=max(neck_width_mm, neck_depth_mm)),
        requested_aspect_ratio_height_over_neck=aspect_ratio,
        geometry_status='NOT GENERATED',
        checks=dict(parent_attachment='UNKNOWN', open_neck_lumen='NOT RUN',
                    nonoverlap='NOT RUN', surface_measurements='NOT RUN',
                    clinical_validity='NOT RUN'),
        parameter_provenance='operator_defined; not a literature preset or population distribution')


def validate_saccular_spec(spec, case):
    """Reject stale source binding and edits to derived coordinates/check states."""
    if not isinstance(spec, dict) or not isinstance(spec.get('parameters'), dict):
        raise ValueError('saccular specification object required')
    try:
        expected = saccular_spec(case, **spec['parameters'])
    except TypeError as error:
        raise ValueError('invalid saccular parameters') from error
    if spec != expected:
        raise ValueError('stale or inconsistent saccular specification')
    return spec
