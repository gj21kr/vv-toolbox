"""Measured endpoint continuity of declared synthetic bridges on sampled paths."""
import math

import numpy as np

from .case_contract import validate_case


def inspect_bridge_continuity(case, *, max_angle_deg, max_radius_jump_mm):
    """Check both attachments without claiming surface or anatomical validation.

    Angles use the first/last sampled chord, not the analytic generator tangent.
    Thresholds are explicit numerical acceptance criteria supplied by the caller.
    """
    validate_case(case)
    for value in (max_angle_deg, max_radius_jump_mm):
        if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
            raise ValueError('finite nonnegative continuity tolerances required')
    if max_angle_deg > 180:
        raise ValueError('angle tolerance must not exceed 180 degrees')
    record = case.get('synthetic_route_inspection', {})
    ids = record.get('bridge_ids')
    if not isinstance(ids, list) or not ids or len(set(ids)) != len(ids):
        raise ValueError('explicit unique bridge IDs required')
    edges = {e['id']: e for e in case['edges']}
    results = []
    for ident in ids:
        bridge = edges.get(ident)
        if bridge is None or bridge['geometry_kind'] != 'estimated' or bridge['centerline_mm'] is None:
            raise ValueError('estimated bridge geometry required')
        anchors = bridge.get('derivation', {}).get('anchors')
        if not isinstance(anchors, list) or len(anchors) != 2:
            raise ValueError('two original endpoint anchors required')
        for index, anchor in enumerate(anchors):
            if not isinstance(anchor, dict) or anchor.get('endpoint') not in ('start', 'end'):
                raise ValueError('explicit source endpoint anchor required')
            source = edges.get(anchor.get('edge_id'))
            if source is None or source['centerline_mm'] is None or source['id'] == ident:
                raise ValueError('original anchor geometry required')
            branch_start = index == 0 and bridge['derivation'].get('attachment_mode') == 'side_branch'
            if source['id'] in ids and not branch_start:
                lineage, sibling = bridge.get('bridge_split', {}), source.get('bridge_split', {})
                endpoint_name = 'start' if index == 0 else 'end'
                if not (lineage and sibling and lineage.get('sibling_edge_id') == source['id']
                        and sibling.get('sibling_edge_id') == ident
                        and lineage.get('internal_endpoint') == endpoint_name
                        and sibling.get('internal_endpoint') == anchor['endpoint']
                        and lineage.get('parent_bridge_id') == sibling.get('parent_bridge_id')
                        and lineage.get('parent_case_revision') == sibling.get('parent_case_revision')):
                    raise ValueError('bridge anchor requires reciprocal split lineage')
            endpoint = anchor['endpoint']
            a, b = (0, 1) if endpoint == 'start' else (-1, -2)
            c, d = (0, 1) if index == 0 else (-1, -2)
            source_points = np.asarray(source['centerline_mm'])
            bridge_points = np.asarray(bridge['centerline_mm'])
            # Source points outward; bridge points inward from its attachment.
            u = source_points[a]-source_points[b]
            v = bridge_points[d]-bridge_points[c]
            expected_radius = source['radii_mm'][a]
            if branch_start:
                u = np.asarray(bridge['derivation']['from_direction_xyz'],dtype=float)
                expected_radius = bridge['derivation']['from_radius_mm']
            angle = math.degrees(math.acos(float(np.clip(np.dot(u,v)/(np.linalg.norm(u)*np.linalg.norm(v)), -1, 1))))
            gap = float(np.linalg.norm(source_points[a]-bridge_points[c]))
            jump = abs(expected_radius-bridge['radii_mm'][c])
            same_node = source[endpoint] == bridge['start' if index == 0 else 'end']
            results.append(dict(bridge_id=ident, attachment='start' if index == 0 else 'end',
                source_edge_id=source['id'], source_endpoint=endpoint,
                reference='declared side-branch direction/radius' if branch_start else 'parent endpoint chord/radius',
                parent_radius_difference_mm=abs(source['radii_mm'][a]-bridge['radii_mm'][c]),
                shared_node=same_node, position_gap_mm=gap, radius_jump_mm=jump,
                sampled_tangent_angle_deg=angle,
                status='PASS' if same_node and gap == 0 and jump <= max_radius_jump_mm and angle <= max_angle_deg else 'FAIL'))
    return dict(status='PASS' if all(r['status']=='PASS' for r in results) else 'FAIL',
        scope='sampled centerline endpoint position, tangent and radius continuity',
        max_angle_deg=max_angle_deg, max_radius_jump_mm=max_radius_jump_mm,
        attachments=results, surface_smoothness='NOT RUN', anatomical_connection='UNKNOWN')
