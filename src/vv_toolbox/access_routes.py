"""Evidence-aware simple paths through ordered mandatory vessel edges.

This checks graph connectivity only, not catheter passage or clinical validity.
"""
from collections import deque

from .case_contract import validate_case


def inspect_route(case, start, end, required_edges, *, max_states=100000):
    """Find a non-retracing path, preferring resolved source connectivity.

    Required edges are ordered, explicit instance IDs, including the selected
    carotid instance. A side label alone is not a waypoint. Search exhaustion
    yields UNKNOWN rather than a false disconnection claim.
    """
    incidence = validate_case(case)
    edges = {edge['id']: edge for edge in case['edges']}
    if start not in incidence or end not in incidence or start == end:
        raise ValueError('distinct known start/end nodes required')
    if (not isinstance(required_edges, list) or not required_edges
            or not all(isinstance(e, str) and e in edges for e in required_edges)
            or len(set(required_edges)) != len(required_edges)):
        raise ValueError('unique ordered required edge IDs required')
    if type(max_states) is not int or max_states < 1:
        raise ValueError('positive search budget required')

    def level(edge):
        nodes = [case['nodes'][edge[key]] for key in ('start', 'end')]
        if (edge['evidence_status'] == 'unresolved' or edge['centerline_mm'] is None
                or any(n['evidence_status'] == 'unresolved' for n in nodes)):
            return 2
        if (edge['geometry_kind'] == 'estimated'
                or any(n['evidence_status'] == 'synthetic_estimate' for n in nodes)):
            return 1
        return 0

    levels = {key: level(edge) for key, edge in edges.items()}
    required_index = {edge: index for index, edge in enumerate(required_edges)}
    examined = 0
    for allowed in range(3):
        queue = deque([(start, 0, [start], [])])
        while queue:
            if examined >= max_states:
                return {'status': 'UNKNOWN', 'reason': 'search_budget_exhausted',
                        'nodes': [], 'edges': [], 'states_examined': examined}
            node, progress, path_nodes, path_edges = queue.popleft()
            examined += 1
            if node == end:
                if progress == len(required_edges):
                    return {'status': 'UNKNOWN' if allowed == 2 else 'PASS',
                            'scope': ('source_graph', 'synthetic_graph', 'unresolved_graph')[allowed],
                            'nodes': path_nodes, 'edges': path_edges,
                            'unresolved_edges': [e for e in path_edges if levels[e] == 2],
                            'estimated_edges': [e for e in path_edges if levels[e] == 1],
                            'states_examined': examined}
                continue
            for edge_id in sorted(incidence[node]):
                if levels[edge_id] > allowed:
                    continue
                edge = edges[edge_id]
                other = edge['end'] if edge['start'] == node else edge['start']
                if other in path_nodes:
                    continue
                next_progress = progress
                if edge_id in required_index:
                    if required_index[edge_id] != progress:
                        continue
                    next_progress += 1
                queue.append((other, next_progress, path_nodes + [other], path_edges + [edge_id]))
    return {'status': 'FAIL', 'reason': 'no_simple_path_through_required_edges',
            'nodes': [], 'edges': [], 'states_examined': examined}
