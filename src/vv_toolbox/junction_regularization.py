"""Bounded two-sided smoothing across a declared degree-two synthetic node."""
from copy import deepcopy
import math

import numpy as np
from scipy.ndimage import gaussian_filter1d

from .case_contract import validate_case
from .case_io import case_digest


def smooth_continuation_node(case, node_id, *, sigma_mm, support_mm, sample_spacing_mm,
                             max_displacement_mm, max_radius_change_mm, case_id):
    validate_case(case)
    if case['model_kind'] != 'synthetic' or not isinstance(case_id, str) or not case_id.strip() or case_id == case['case_id']:
        raise ValueError('distinct synthetic output case required')
    for value in (sigma_mm, support_mm, sample_spacing_mm, max_displacement_mm, max_radius_change_mm):
        if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
            raise ValueError('positive finite smoothing parameters required')
    if support_mm < 3*sigma_mm or sample_spacing_mm > sigma_mm/2:
        raise ValueError('support must cover 3 sigma and sampling at most sigma/2')
    incident = [e for e in case['edges'] if node_id in (e['start'], e['end'])]
    if node_id not in case['nodes'] or len(incident) != 2:
        raise ValueError('explicit degree-two node required')
    ids = [e['id'] for e in incident]
    if any(l['edge_id'] in ids for l in case.get('lesions', [])):
        raise ValueError('cannot smooth a lesion-bearing junction')
    if set(ids) & set(case.get('synthetic_route_inspection', {}).get('bridge_ids', [])):
        raise ValueError('declared bridge smoothing requires separate attachment lineage handling')
    oriented = []
    for i, edge in enumerate(incident):
        if edge['centerline_mm'] is None or edge['start'] == edge['end'] or len(edge['centerline_mm']) < 3:
            raise ValueError('open paths with at least three points required')
        reverse = (edge['start'] == node_id) if i == 0 else (edge['end'] == node_id)
        p, r = np.array(edge['centerline_mm']), np.array(edge['radii_mm'])
        oriented.append((p[::-1] if reverse else p, r[::-1] if reverse else r, reverse))
    p0, r0, _ = oriented[0]; p1, r1, _ = oriented[1]
    if not np.array_equal(p0[-1], p1[0]):
        raise ValueError('shared node geometry must coincide exactly')
    points = np.concatenate([p0, p1[1:]])
    radii = np.r_[r0[:-1], (r0[-1]+r1[0])/2, r1[1:]]
    join = len(p0)-1
    arc = np.r_[0., np.cumsum(np.linalg.norm(np.diff(points, axis=0), axis=1))]
    if support_mm >= min(arc[join]-arc[1], arc[-2]-arc[join]):
        raise ValueError('support must preserve both outer endpoint chords')
    count = int(math.ceil(arc[-1]/sample_spacing_mm))+1
    if count > 1_000_000:
        raise ValueError('resampling budget exceeded')
    grid = np.linspace(0., arc[-1], count)
    sigma = sigma_mm/(grid[1]-grid[0])
    if sigma > 250_000:
        raise ValueError('smoothing kernel budget exceeded')
    sampled = np.column_stack([np.interp(grid, arc, points[:, k]) for k in range(3)])
    filtered = gaussian_filter1d(sampled, sigma=sigma, axis=0, mode='nearest')
    smoothed = np.column_stack([np.interp(arc, grid, filtered[:, k]) for k in range(3)])
    smooth_r = np.interp(arc, grid, gaussian_filter1d(np.interp(grid, arc, radii), sigma=sigma, mode='nearest'))
    t = np.clip(np.abs(arc-arc[join])/support_mm, 0., 1.)
    weight = 1-t*t*(3-2*t)
    changed = points+weight[:, None]*(smoothed-points)
    changed_r = radii+weight*(smooth_r-radii)
    displacement = float(np.linalg.norm(changed-points, axis=1).max())
    radius_delta = max(float(np.abs(changed_r[:join+1]-r0).max()), float(np.abs(changed_r[join:]-r1).max()))
    if displacement > max_displacement_mm or radius_delta > max_radius_change_mm:
        raise ValueError('junction smoothing exceeds declared geometry bounds')
    if np.any(np.linalg.norm(np.diff(changed, axis=0), axis=1) <= 1e-12):
        raise ValueError('smoothing produced degenerate intervals')
    result = deepcopy(case)
    for i, edge in enumerate(incident):
        output = next(e for e in result['edges'] if e['id'] == edge['id'])
        p, r = (changed[:join+1], changed_r[:join+1]) if i == 0 else (changed[join:], changed_r[join:])
        if oriented[i][2]: p, r = p[::-1], r[::-1]
        output.update(centerline_mm=p.tolist(), radii_mm=r.tolist(), geometry_kind='estimated', evidence_status='synthetic_estimate')
    result['nodes'][node_id].update(position_mm=changed[join].tolist(), evidence_status='synthetic_estimate')
    params = dict(node_id=node_id, sigma_mm=sigma_mm, support_mm=support_mm, sample_spacing_mm=sample_spacing_mm,
                  max_displacement_mm=max_displacement_mm, max_radius_change_mm=max_radius_change_mm)
    result.update(case_id=case_id, generation=dict(seed=case['generation']['seed'], generator_version='degree-two-junction-gaussian-1',
                  config=dict(parent_case_revision=case_digest(case), parent_generation=deepcopy(case['generation']), **params)))
    archived = {k: result.pop(k) for k in ('quality', 'geometry_quality', 'surface_quality', 'route_inspection', 'access_route_inspection') if k in result}
    for key in ('centerline_regularization', 'radius_regularization', 'synthetic_junctions'):
        if key in result: result[key]['geometry_quality'] = 'NOT RUN'
    if 'synthetic_route_inspection' in result:
        result['synthetic_route_inspection'].update(source_nodes_preserved=False, source_edges_preserved=False,
            collision_check='NOT RUN', surface_junction_check='NOT RUN', anatomical_connectivity='UNKNOWN')
    result.setdefault('junction_regularization_history', []).append(dict(parameters=params,
        parent_case_revision=case_digest(case), original_edges=deepcopy(incident), original_node=deepcopy(case['nodes'][node_id]),
        measured_max_displacement_mm=displacement, measured_max_radius_change_mm=radius_delta,
        parent_quality_not_applicable=archived, anatomical_acceptance='UNKNOWN'))
    validate_case(result)
    return result
