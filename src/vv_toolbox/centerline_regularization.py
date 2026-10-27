"""Bounded arc-length smoothing in a separate synthetic case."""
from copy import deepcopy
import math

import numpy as np
from scipy.ndimage import gaussian_filter1d

from .case_contract import validate_case
from .case_io import case_digest


def smooth_synthetic_centerlines(case, edge_ids, *, sigma_mm, sample_spacing_mm,
                                 max_displacement_mm, case_id):
    """Preserve node positions, endpoint chords and radius station identities.

    Gaussian xyz filtering uses a uniform physical arc grid, then evaluates at
    original stations. The first two and last two points remain byte-for-value
    identical; the displacement tapers over 3 sigma from those frozen regions.
    Geometry/clinical validity is not inferred from this numerical transform.
    """
    validate_case(case)
    if case['model_kind'] != 'synthetic':
        raise ValueError('separate synthetic case required')
    if not isinstance(case_id, str) or not case_id.strip() or case_id == case['case_id']:
        raise ValueError('distinct derived case ID required')
    edges = {edge['id']: edge for edge in case['edges']}
    if (not isinstance(edge_ids, list) or not edge_ids or
            not all(isinstance(i, str) and i in edges for i in edge_ids) or
            len(set(edge_ids)) != len(edge_ids)):
        raise ValueError('explicit unique known edges required')
    for value in (sigma_mm, sample_spacing_mm, max_displacement_mm):
        if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
            raise ValueError('positive finite physical smoothing parameters required')
    if sample_spacing_mm > sigma_mm/2:
        raise ValueError('sample spacing must be at most half sigma')
    if any(lesion['edge_id'] in edge_ids for lesion in case.get('lesions', [])):
        raise ValueError('cannot smooth an existing lesion edge')
    revision = case_digest(case)
    result = deepcopy(case)
    metrics = []
    for edge in result['edges']:
        if edge['id'] not in edge_ids:
            continue
        if (edge['centerline_mm'] is None or edge['start'] == edge['end'] or
                len(edge['centerline_mm']) < 5):
            raise ValueError('open centerline with at least five points required')
        points = np.asarray(edge['centerline_mm'], dtype=float)
        arc = np.r_[0., np.cumsum(np.linalg.norm(np.diff(points, axis=0), axis=1))]
        count = int(math.ceil(arc[-1]/sample_spacing_mm))+1
        if count > 1_000_000:
            raise ValueError('centerline resampling budget exceeded')
        grid = np.linspace(0., arc[-1], count)
        sigma = sigma_mm/(grid[1]-grid[0])
        if sigma > 250_000:
            raise ValueError('centerline smoothing kernel budget exceeded')
        sampled = np.column_stack([np.interp(grid, arc, points[:, j]) for j in range(3)])
        filtered = gaussian_filter1d(sampled, sigma=sigma, axis=0, mode='nearest')
        smoothed = np.column_stack([np.interp(arc, grid, filtered[:, j]) for j in range(3)])
        weight = np.clip(np.minimum(arc-arc[1], arc[-2]-arc)/(3*sigma_mm), 0., 1.)
        weight = weight*weight*(3-2*weight)
        changed = points+weight[:, None]*(smoothed-points)
        changed[[0, 1, -2, -1]] = points[[0, 1, -2, -1]]
        displacement = float(np.max(np.linalg.norm(changed-points, axis=1)))
        if displacement > max_displacement_mm:
            raise ValueError('centerline displacement exceeds declared bound: '+edge['id'])
        if np.any(np.linalg.norm(np.diff(changed, axis=0), axis=1) <= 1e-12):
            raise ValueError('smoothing produced a degenerate centerline interval')
        edge['centerline_mm'] = changed.tolist()
        # Preserve the original numeric values at the frozen indices exactly.
        for index in (0, 1, -2, -1):
            edge['centerline_mm'][index] = deepcopy(edges[edge['id']]['centerline_mm'][index])
        edge['geometry_kind'] = 'estimated'
        edge['evidence_status'] = 'synthetic_estimate'
        edge.setdefault('centerline_transform_history', []).append({
            'operator': 'arc-gaussian-frozen-chords-1', 'parent_case_revision': revision,
            'sigma_mm': sigma_mm, 'sample_spacing_mm': sample_spacing_mm,
            'max_displacement_mm': max_displacement_mm,
            'measured_max_displacement_mm': displacement,
            'frozen_point_indices': [0, 1, len(points)-2, len(points)-1],
            'radius_policy': 'unchanged values at original station indices',
            'anatomical_acceptance': 'UNKNOWN'})
        metrics.append({'edge_id': edge['id'], 'max_displacement_mm': displacement,
                        'original_length_mm': float(arc[-1]),
                        'modified_length_mm': float(np.linalg.norm(np.diff(changed, axis=0), axis=1).sum()),
                        'endpoint_chords_unchanged': True, 'radii_unchanged': True})
    result['case_id'] = case_id
    result['generation'] = {'seed': case['generation']['seed'],
        'generator_version': 'arc-gaussian-frozen-chords-1',
        'config': {'parent_case_revision': revision, 'parent_generation': deepcopy(case['generation']),
                   'edge_ids': list(edge_ids), 'sigma_mm': sigma_mm,
                   'sample_spacing_mm': sample_spacing_mm, 'max_displacement_mm': max_displacement_mm}}
    previous = result.pop('synthetic_route_inspection', None)
    if previous is not None:
        result['synthetic_route_inspection'] = {
            'bridge_ids': deepcopy(previous['bridge_ids']),
            'source_case_sha256': previous['source_case_sha256'],
            'source_nodes_preserved': previous.get('source_nodes_preserved', False), 'source_edges_preserved': False,
            'collision_check': 'NOT RUN', 'surface_junction_check': 'NOT RUN',
            'anatomical_connectivity': 'UNKNOWN'}
    archived = {key: result.pop(key) for key in ('quality', 'geometry_quality', 'surface_quality') if key in result}
    if 'radius_regularization' in result:
        result['radius_regularization']['geometry_quality'] = 'NOT RUN'
    result['centerline_regularization'] = {
        'metrics': metrics, 'geometry_quality': 'NOT RUN', 'anatomical_acceptance': 'UNKNOWN',
        'parent_quality_not_applicable': archived}
    if result.get('surface_parts'):
        # The wall is unchanged: explicitly check the changed paths before
        # binding the same triangles to the new centerline stations.
        import trimesh
        from .centerline_containment import inspect_centerline_containment
        from .case_source_surfaces import attach_surfaces
        parts = result.pop('surface_parts')
        checked = []
        for part in parts:
            changed_ids = set(part['edge_ids']) & set(edge_ids)
            if not changed_ids:
                continue
            mesh = trimesh.Trimesh(part['vertices_mm'], part['faces'], process=False)
            for edge in result['edges']:
                if edge['id'] not in changed_ids:
                    continue
                report = inspect_centerline_containment(mesh, edge['centerline_mm'])
                if report['status'] != 'PASS':
                    raise ValueError('Changed centerline is not proven inside registered surface: '+edge['id'])
                checked.append(dict(edge_id=edge['id'], part_id=part['part_id'],
                                    geometry_sha256=part['geometry_sha256'], containment=report))
        if {r['edge_id'] for r in checked} != set(edge_ids):
            raise ValueError('Every edited edge requires a registered surface')
        result.setdefault('inspection', {})['centerline_edit'] = dict(
            parent_case_revision=revision, checked_paths=checked,
            scope='Changed centerlines only; registered triangles unchanged',
            radius_surface_consistency='NOT RUN', anatomical_acceptance='UNKNOWN',
            accepted_for_generation=False,
            inherited_inspections_role='Historical parent evidence; not revalidation of edited paths')
        result = attach_surfaces(result, parts)
    validate_case(result)
    return result
