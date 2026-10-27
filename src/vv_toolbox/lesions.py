"""Explicit synthetic concentric stenosis on case radius profiles.

This module does not infer clinical severity, repair source surfaces, or claim
surface/voxel measurements from a centerline radius parameterization.
"""
from copy import deepcopy
from math import ceil, dist, isfinite, sqrt

from .case_contract import validate_case
from .geometry_quality import segment_distance


VERSION = 'concentric-profile-2'
REGIONS = {'femoral', 'iliac', 'abdominal_aorta', 'thoracic_aorta_arch',
           'common_carotid', 'cervical_ica', 'intracranial_ica', 'aca', 'mca'}


def require_profile_lesions(case):
    """Prevent unsupported sac/other records from silently exporting baseline tubes."""
    if any(l.get('type') not in ('concentric_stenosis', 'fusiform_dilation')
           for l in case.get('lesions', [])):
        raise ValueError('unsupported lesion geometry: radius-profile output cannot represent this lesion type')


def _finite(value, name):
    if type(value) not in (int, float) or not isfinite(value):
        raise ValueError(f'{name} must be finite')


def concentric_stenosis(case, *, edge_id, lesion_id, case_id, region,
                       center_mm, length_mm, severity_percent, measurement_method,
                       sample_spacing_mm, seed, min_spacing_mm=0.0):
    """Manually specified concentric narrowing; see the profile contract."""
    return _concentric_profile(case, edge_id=edge_id, lesion_id=lesion_id, case_id=case_id,
        region=region, center_mm=center_mm, length_mm=length_mm, severity_percent=severity_percent,
        measurement_method=measurement_method, sample_spacing_mm=sample_spacing_mm,
        seed=seed, min_spacing_mm=min_spacing_mm)


def fusiform_dilation(case, *, diameter_ratio, **parameters):
    """Manual symmetric dilation, not a clinical diagnosis or literature preset.

    Diameter ratio is relative to the local unmodified profile at the centre.
    Interior support only; junction and saccular operators are separate.
    """
    _finite(diameter_ratio, 'diameter ratio')
    if diameter_ratio <= 1:
        raise ValueError('dilation diameter ratio must exceed one')
    return _concentric_profile(case, severity_percent=0,
                               measurement_method='local_baseline_diameter_ratio',
                               _diameter_ratio=diameter_ratio, **parameters)


def _concentric_profile(case, *, edge_id, lesion_id, case_id, region,
                       center_mm, length_mm, severity_percent, measurement_method,
                       sample_spacing_mm, seed, min_spacing_mm=0.0, _diameter_ratio=None):
    """Create a derivative with one interior, manually specified lesion.

    Arc lengths are measured from the selected edge's start. Local baseline
    percentages refer to the circular radius profile at the lesion centre, not
    a NASCET/WASID reference section. Junction lesions require a separate operator.
    """
    validate_case(case)
    previous_lesions = case.get('lesions', [])
    if any(l.get('lesion_id') == lesion_id for l in previous_lesions):
        raise ValueError('duplicate lesion ID')
    _finite(min_spacing_mm, 'minimum spacing')
    if min_spacing_mm < 0:
        raise ValueError('minimum spacing must be nonnegative')
    if not isinstance(case_id, str) or not case_id.strip() or case_id == case['case_id']:
        raise ValueError('distinct derived case ID required')
    if not isinstance(lesion_id, str) or not lesion_id.strip():
        raise ValueError('lesion ID required')
    if region not in REGIONS:
        raise ValueError('explicit supported region required')
    if type(seed) is not int or not 0 <= seed < 2**64:
        raise ValueError('uint64 seed required')
    for name, value in [('center', center_mm), ('length', length_mm),
                        ('severity', severity_percent), ('spacing', sample_spacing_mm)]:
        _finite(value, name)
    dilation = _diameter_ratio is not None
    if not (length_mm > 0 and sample_spacing_mm > 0 and (dilation or 0 < severity_percent < 100)):
        raise ValueError('positive length/spacing and severity strictly between 0 and 100 required')
    if not dilation and measurement_method not in ('local_baseline_diameter', 'local_baseline_area'):
        raise ValueError('reference-based clinical methods require reviewed reference sections')
    edge = next((e for e in case['edges'] if e['id'] == edge_id), None)
    if edge is None or edge['centerline_mm'] is None:
        raise ValueError('resolved centerline geometry required')
    points, radii = edge['centerline_mm'], edge['radii_mm']
    stations = [0.0]
    for a, b in zip(points, points[1:]):
        stations.append(stations[-1] + dist(a, b))
    start, stop = center_mm - length_mm / 2, center_mm + length_mm / 2
    if not 0 < start < stop < stations[-1]:
        raise ValueError('lesion support must remain strictly inside edge; junctions protected')
    count = ceil(length_mm / sample_spacing_mm)
    if count > 100000:
        raise ValueError('lesion sample budget exceeded')
    samples = sorted(set(stations + [center_mm] + [start + length_mm * i / count for i in range(count + 1)]))
    # Preserve all original vertices and insert only interpolated samples.
    new_points, baseline = [], []
    interval = 0
    for s in samples:
        while interval < len(stations) - 2 and s > stations[interval + 1]:
            interval += 1
        t = (s - stations[interval]) / (stations[interval + 1] - stations[interval])
        if s == stations[interval]:
            p = deepcopy(points[interval])
        elif s == stations[interval + 1]:
            p = deepcopy(points[interval + 1])
        else:
            p = [a + t * (b - a) for a, b in zip(points[interval], points[interval + 1])]
        new_points.append(p)
        baseline.append(radii[interval] + t * (radii[interval + 1] - radii[interval]))
    ratio = _diameter_ratio if dilation else 1 - severity_percent / 100
    if measurement_method == 'local_baseline_area':
        ratio = sqrt(ratio)
    alpha = 1 - ratio
    modified = []
    for s, radius in zip(samples, baseline):
        u = 2 * (s - center_mm) / length_mm
        weight = (1 - u*u)**3 if abs(u) < 1 else 0.0
        modified.append(radius * (1 - alpha * weight))
    if not all(isfinite(r) and r > 0 for r in modified):
        raise ValueError('profile produced invalid radii')
    # The support encloses both baseline and final shape, including expansions.
    capsules = [{'start':new_points[i], 'end':new_points[i+1],
                 'radius_mm':max(baseline[i],baseline[i+1],modified[i],modified[i+1])}
                for i in range(len(samples)-1) if start <= samples[i] and samples[i+1] <= stop]
    spacing_checks = []
    for previous in previous_lesions:
        prior_capsules = previous.get('support_capsules_mm')
        if not prior_capsules:
            raise ValueError('prior lesion has no recorded 3D support; clearance unknown')
        _finite(previous.get('min_spacing_mm'), 'prior minimum spacing')
        if previous['min_spacing_mm'] < 0:
            raise ValueError('invalid prior minimum spacing')
        for capsule in prior_capsules:
            _finite(capsule.get('radius_mm'), 'prior support radius')
            if capsule['radius_mm'] <= 0:
                raise ValueError('positive prior support radius required')
            for key in ('start','end'):
                point = capsule.get(key)
                if not isinstance(point,list) or len(point) != 3:
                    raise ValueError('invalid prior support point')
                for coordinate in point:
                    _finite(coordinate, 'prior support coordinate')
        required = max(min_spacing_mm, previous['min_spacing_mm'])
        if len(capsules)*len(prior_capsules) > 1_000_000:
            raise ValueError('lesion clearance pair budget exceeded')
        clearance = min(segment_distance(a['start'],a['end'],b['start'],b['end'])
                        - a['radius_mm'] - b['radius_mm'] for a in capsules for b in prior_capsules)
        if clearance <= required:
            raise ValueError('lesion support clearance violates nonoverlap or minimum spacing')
        spacing_checks.append({'lesion_id':previous['lesion_id'],
                               'clearance_lower_bound_mm':clearance,'required_spacing_mm':required})
    center_index = samples.index(center_mm)
    actual_ratio = modified[center_index] / baseline[center_index]
    measured = 100 * (1 - (actual_ratio**2 if measurement_method.endswith('area') else actual_ratio))
    operation = dict(lesion_id=lesion_id, type='concentric_stenosis', mode='manual_synthetic',
        region=region, edge_id=edge_id, center_mm=center_mm, length_mm=length_mm,
        measurement_method=measurement_method, requested_percent=severity_percent,
        profile_center_percent=measured, reference_diameter_mm=2*baseline[center_index],
        profile_center_diameter_mm=2*modified[center_index],
        support_interval_mm=[start, stop], sample_spacing_mm=sample_spacing_mm,
        support_capsules_mm=deepcopy(capsules), min_spacing_mm=min_spacing_mm,
        spacing_checks=spacing_checks,
        parameter_provenance='operator_defined; no population distribution',
        generator_version=VERSION, checks={'profile_center_measurement': 'PASS',
            'surface_measurement': 'NOT RUN', 'collision': 'NOT RUN', 'clinical_validity': 'NOT RUN'})
    version = 'fusiform-profile-1' if dilation else VERSION
    if dilation:
        operation.update(type='fusiform_dilation', generator_version=version,
                         requested_diameter_ratio=_diameter_ratio, profile_center_diameter_ratio=actual_ratio)
        operation.pop('requested_percent')
        operation.pop('profile_center_percent')
    result = deepcopy(case)
    result.update(case_id=case_id, model_kind='synthetic',
                  generation={'seed': seed, 'generator_version': version,
                              'config': deepcopy(operation), 'parent_generation': deepcopy(case['generation'])},
                  lesions=deepcopy(previous_lesions)+[operation])
    changed = next(e for e in result['edges'] if e['id'] == edge_id)
    changed.update(centerline_mm=new_points, radii_mm=modified,
                   geometry_kind='estimated', evidence_status='synthetic_estimate')
    changed['lesion_ids'] = list(changed.get('lesion_ids', [])) + [lesion_id]
    result.setdefault('history', []).append({'operation': version, 'parent_case_id': case['case_id'],
                                            'lesion': deepcopy(operation)})
    validate_case(result)
    return result
