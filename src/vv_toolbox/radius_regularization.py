"""Explicit bounded radius smoothing on separate synthetic cases."""
from copy import deepcopy
import math

import numpy as np
from scipy.ndimage import gaussian_filter1d

from .case_contract import validate_case
from .case_io import case_digest


def smooth_synthetic_radii(case, edge_ids, *, sigma_mm, sample_spacing_mm,
                           max_change_mm, case_id):
    """Smooth in physical arc length, taper at ends, reject excess displacement.

    Source points and endpoint radii stay exact. This is an operator-defined
    synthetic transformation, never a correction certified against anatomy.
    Existing lesion profiles cannot be changed with this operator.
    """
    validate_case(case)
    if case['model_kind'] != 'synthetic':
        raise ValueError('separate synthetic case required')
    if not isinstance(case_id,str) or not case_id.strip() or case_id == case['case_id']:
        raise ValueError('distinct derived case ID required')
    edges = {e['id']:e for e in case['edges']}
    if (not isinstance(edge_ids,list) or not edge_ids or
            not all(isinstance(e,str) and e in edges for e in edge_ids) or
            len(set(edge_ids)) != len(edge_ids)):
        raise ValueError('explicit unique known edges required')
    for value in (sigma_mm, sample_spacing_mm, max_change_mm):
        if type(value) not in (int,float) or not math.isfinite(value) or value <= 0:
            raise ValueError('positive finite physical smoothing parameters required')
    if sample_spacing_mm > sigma_mm/2:
        raise ValueError('sample spacing must be at most half sigma')
    if any(lesion['edge_id'] in edge_ids for lesion in case.get('lesions',[])):
        raise ValueError('cannot smooth an existing lesion profile')
    revision = case_digest(case)
    result = deepcopy(case)
    metrics = []
    for edge in result['edges']:
        if edge['id'] not in edge_ids:
            continue
        if edge['centerline_mm'] is None or edge['start'] == edge['end']:
            raise ValueError('open centerline geometry required')
        p, r = np.asarray(edge['centerline_mm']), np.asarray(edge['radii_mm'],dtype=float)
        arc = np.r_[0., np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))]
        count = int(math.ceil(arc[-1]/sample_spacing_mm))+1
        if count > 1_000_000:
            raise ValueError('radius resampling budget exceeded')
        grid = np.linspace(0,arc[-1],count)
        if sigma_mm/(grid[1]-grid[0]) > 250_000:
            raise ValueError('radius smoothing kernel budget exceeded')
        sampled = np.interp(grid,arc,r)
        filtered = gaussian_filter1d(sampled,sigma=sigma_mm/(grid[1]-grid[0]),mode='nearest')
        smoothed = np.interp(arc,grid,filtered)
        weight = np.clip(np.minimum(arc,arc[-1]-arc)/(3*sigma_mm),0,1)
        weight = weight*weight*(3-2*weight)
        modified = r+weight*(smoothed-r)
        modified[0], modified[-1] = r[0], r[-1]
        delta = float(np.max(np.abs(modified-r)))
        if delta > max_change_mm:
            raise ValueError('radius change exceeds declared bound: '+edge['id'])
        edge['radii_mm'] = modified.tolist()
        edge['geometry_kind'] = 'estimated'
        edge['evidence_status'] = 'synthetic_estimate'
        edge.setdefault('radius_transform_history',[]).append({
            'operator':'arc-gaussian-taper-1','parent_case_revision':revision,
            'sigma_mm':sigma_mm,'sample_spacing_mm':sample_spacing_mm,
            'max_change_mm':max_change_mm,'measured_max_change_mm':delta,
            'anatomical_acceptance':'UNKNOWN'})
        metrics.append({'edge_id':edge['id'],'max_change_mm':delta,
                        'endpoint_radius_change_mm':[0.,0.]})
    result['case_id'] = case_id
    result['generation'] = {'seed':case['generation']['seed'],
        'generator_version':'arc-gaussian-taper-1',
        'config':{'parent_case_revision':revision,'parent_generation':deepcopy(case['generation']),
                  'edge_ids':list(edge_ids),'sigma_mm':sigma_mm,
                  'sample_spacing_mm':sample_spacing_mm,'max_change_mm':max_change_mm}}
    # Prior derived quality results cannot certify the changed geometry.
    previous = result.pop('synthetic_route_inspection',None)
    if previous is not None:
        result['synthetic_route_inspection'] = {
            'bridge_ids':deepcopy(previous['bridge_ids']),
            'source_case_sha256':previous['source_case_sha256'],
            'source_nodes_preserved':previous.get('source_nodes_preserved',False),'source_edges_preserved':False,
            'collision_check':'NOT RUN','surface_junction_check':'NOT RUN',
            'anatomical_connectivity':'UNKNOWN'}
    result['radius_regularization'] = {'metrics':metrics,'geometry_quality':'NOT RUN',
                                      'anatomical_acceptance':'UNKNOWN'}
    archived = {key:result.pop(key) for key in ('quality','geometry_quality','surface_quality') if key in result}
    if archived:
        result['radius_regularization']['parent_quality_not_applicable'] = archived
    if 'centerline_regularization' in result:
        result['centerline_regularization']['geometry_quality'] = 'NOT RUN'
    validate_case(result)
    return result
