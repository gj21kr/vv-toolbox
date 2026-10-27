"""Materialize reviewed cerebral boundaries on explicitly addressed centerlines."""
from copy import deepcopy
from math import dist, isfinite

from .atlas_annotations import validate_annotations
from .case_contract import validate_case


def materialize_segments(case, annotations, assignments, *, tolerance_mm):
    """Split paths at reviewed positions; never snap a region or guess a branch.

    Each assignment contains edge_id, cuts and labels. A cut contains boundary_id,
    interval_index and fraction on that original polyline interval. Labels follow
    edge point order; source direction is not assumed proximal-to-distal.
    The tolerance is an explicit numerical mapping tolerance, not a clinical one.
    """
    validate_case(case)
    validate_annotations(annotations)
    if type(tolerance_mm) not in (int, float) or not isfinite(tolerance_mm) or tolerance_mm < 0:
        raise ValueError('finite nonnegative tolerance_mm required')
    frame = annotations['coordinate_frame']
    if (frame['id'] != case['frame']['id'] or frame['units'] != 'mm'
            or not frame['frame_confirmed'] or not frame['units_confirmed']):
        raise ValueError('confirmed matching mm frame required')
    if not any(s['id'] == annotations['source']['id'] and
               s['sha256'].lower() == annotations['source']['sha256'].lower() for s in case['sources']):
        raise ValueError('annotation source fingerprint mismatch')
    if annotations['model_kind'] != case['model_kind']:
        raise ValueError('annotation model kind mismatch')
    if not isinstance(assignments, list) or not assignments:
        raise ValueError('explicit segment assignments required')
    original = {e['id']: e for e in case['edges']}
    boundaries = {b['boundary_id']: b for b in annotations['boundaries']}
    result = deepcopy(case)
    used_edges, used_boundaries = set(), set()
    replacements = {}
    for assignment in assignments:
        ident = assignment['edge_id']
        if ident not in original or ident in used_edges:
            raise ValueError('unknown or duplicate assigned edge')
        used_edges.add(ident)
        edge = original[ident]
        points, radii = edge['centerline_mm'], edge['radii_mm']
        cuts, labels = assignment['cuts'], assignment['labels']
        refs = assignment.get('extent_review_refs')
        if not isinstance(refs, list) or not refs or not all(isinstance(r, str) and r.strip() for r in refs):
            raise ValueError('review of full assigned edge extent required')
        if points is None or not cuts or len(labels) != len(cuts) + 1:
            raise ValueError('geometry, cuts and one label per resulting interval required')
        prepared = []
        for cut in cuts:
            boundary_id = cut['boundary_id']
            if boundary_id not in boundaries or boundary_id in used_boundaries:
                raise ValueError('unknown or reused branch boundary')
            used_boundaries.add(boundary_id)
            b = boundaries[boundary_id]
            if (b['evidence_status'] not in ('source_annotation', 'landmark_reviewed')
                    or b['position'] is None or b.get('localization_scope', 'point') != 'point'):
                raise ValueError('reviewed point boundary required')
            if (b['branch_id'] != edge['anatomy']['branch_id'] or
                    b['artery'] != edge['anatomy']['artery'] or b['side'] != edge['anatomy']['side']):
                raise ValueError('boundary branch/artery/side mismatch')
            i, fraction = cut['interval_index'], cut['fraction']
            if (type(i) is not int or not 0 <= i < len(points) - 1 or
                    type(fraction) not in (int, float) or not isfinite(fraction) or not 0 <= fraction < 1):
                raise ValueError('invalid original interval address')
            address = i + fraction
            if address <= 0 or (prepared and address <= prepared[-1][0]):
                raise ValueError('cuts must be strictly ordered and internal')
            point = [a + fraction * (z - a) for a, z in zip(points[i], points[i + 1])]
            if dist(point, b['position']) > tolerance_mm:
                raise ValueError('boundary does not map within declared tolerance')
            radius = radii[i] + fraction * (radii[i + 1] - radii[i])
            node_id = f'{ident}:boundary:{boundary_id}'
            if node_id in result['nodes']:
                raise ValueError('generated node ID collision')
            result['nodes'][node_id] = {'kind': 'segment_boundary', 'position_mm': point,
                'evidence_status': b['evidence_status'], 'boundary_id': boundary_id,
                'reviewed_position_mm': deepcopy(b['position']), 'source_refs': deepcopy(b['source_refs']),
                'mapping_residual_mm': dist(point, b['position'])}
            prepared.append((address, point, radius, node_id, b))
        for index, (_, _, _, _, b) in enumerate(prepared):
            if labels[index:index + 2] not in [b['transition'].split('_'), b['transition'].split('_')[::-1]]:
                raise ValueError('labels do not match reviewed transition')
        anchors = [(0, points[0], radii[0], edge['start'], None)] + prepared + [
            (len(points)-1, points[-1], radii[-1], edge['end'], None)]
        pieces = []
        for index, (left, right) in enumerate(zip(anchors, anchors[1:])):
            new_id = f'{ident}:segment:{index}'
            if new_id in original:
                raise ValueError('generated edge ID collision')
            interior = [j for j in range(len(points)) if left[0] < j < right[0]]
            piece = deepcopy(edge)
            piece.update(id=new_id, start=left[3], end=right[3],
                centerline_mm=[deepcopy(left[1])] + [deepcopy(points[j]) for j in interior] + [deepcopy(right[1])],
                radii_mm=[left[2]] + [radii[j] for j in interior] + [right[2]])
            piece['anatomy']['segment'] = labels[index]
            piece['segment_assignment'] = {'original_edge_id': ident,
                'interval_address': [left[0], right[0]], 'tolerance_mm': tolerance_mm,
                'boundary_ids': [a[4]['boundary_id'] for a in (left, right) if a[4]],
                'extent_review_refs': deepcopy(refs),
                'scope': 'centerline_only; surface and mask labels not materialized'}
            pieces.append(piece)
        replacements[ident] = pieces
    result['edges'] = [piece for edge in case['edges'] for piece in replacements.get(edge['id'], [deepcopy(edge)])]
    result.setdefault('history', []).append({'operation': 'materialize_segments',
        'assignments': deepcopy(assignments), 'tolerance_mm': tolerance_mm,
        'annotation_source': deepcopy(annotations['source'])})
    validate_case(result)
    return result
