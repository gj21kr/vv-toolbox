"""Explicit synthetic union surfaces from case radius profiles."""
import math

import numpy as np
import trimesh

from .case_contract import validate_case
from .case_io import case_digest
from .model import Segment, VesselGraph
from .surface import network_mesh
from .geometry_quality import screen_nonincident_clearance, screen_junction_clearance, screen_self_clearance


def build_case_surface(case, edge_ids, *, spacing_mm, max_grid_voxels=20_000_000,
                       junction_regions=None):
    validate_case(case)
    if 'surface_parts' in case:
        if junction_regions is not None or case.get('lesions'):
            raise ValueError('Registered surfaces require explicit lesion/junction materialization')
        from .case_source_surfaces import selected_surface
        return selected_surface(case, edge_ids)
    from .lesions import require_profile_lesions
    require_profile_lesions(case)
    if case['model_kind'] != 'synthetic':
        raise ValueError('surface reconstruction requires an explicitly synthetic case')
    if (not isinstance(edge_ids, list) or not edge_ids or
            not all(isinstance(e, str) for e in edge_ids) or len(set(edge_ids)) != len(edge_ids)):
        raise ValueError('explicit unique edge IDs required')
    if type(spacing_mm) not in (int, float) or not math.isfinite(spacing_mm) or spacing_mm <= 0:
        raise ValueError('positive finite spacing required')
    if type(max_grid_voxels) is not int or max_grid_voxels <= 0:
        raise ValueError('positive grid budget required')
    by_id = {e['id']: e for e in case['edges']}
    if any(ident not in by_id for ident in edge_ids):
        raise ValueError('unknown edge ID')
    selected = [by_id[ident] for ident in edge_ids]
    if any(e['centerline_mm'] is None or e['start'] == e['end'] for e in selected):
        raise ValueError('surface generator requires open resolved centerline paths')
    points = np.concatenate([e['centerline_mm'] for e in selected])
    radius = max(max(e['radii_mm']) for e in selected)
    # Includes conservative radius and terminal/grid padding, before field allocation.
    shape = np.ceil((np.ptp(points, axis=0) + 2*radius + 12*spacing_mm)/spacing_mm).astype(object) + 1
    estimate = math.prod(int(n) for n in shape)
    if estimate > max_grid_voxels:
        raise ValueError('surface grid budget exceeded; choose an explicit ROI/resolution')
    incidence = {}
    for edge in selected:
        for node, index in ((edge['start'], 0), (edge['end'], -1)):
            incidence.setdefault(node, []).append(edge['radii_mm'][index])
    # Explicit synthesis policy, not a clinically measured junction extent.
    collars = {node: 3*max(radii)+2*spacing_mm for node, radii in incidence.items() if len(radii)>1}
    if junction_regions is None:
        clearance = screen_nonincident_clearance(case, edge_ids, margin_mm=2*spacing_mm)
        if clearance['status'] != 'PASS':
            raise ValueError('nonincident vessel clearance unresolved; surface union blocked')
        junction_clearance = screen_junction_clearance(case, edge_ids, collars_mm=collars,
                                                      margin_mm=2*spacing_mm)
        if junction_clearance['status'] != 'PASS':
            raise ValueError('shared-junction vessel clearance unresolved; surface union blocked')
    else:
        from .junction_regions import inspect_junction_regions
        junction_clearance = inspect_junction_regions(case, edge_ids, junction_regions,
                                                      margin_mm=2*spacing_mm)
        if junction_clearance['status'] != 'PASS':
            raise ValueError('explicit junction-region clearance unresolved; surface union blocked')
        clearance = {'status': 'COVERED_BY_JUNCTION_REGION_SCREEN',
                     'scope': 'All selected cross-edge pairs, including nonincident pairs'}
    self_clearance = screen_self_clearance(case, edge_ids,
        local_windows_mm={e['id']:4*max(e['radii_mm'])+2*spacing_mm for e in selected},
        margin_mm=2*spacing_mm)
    if self_clearance['status'] != 'PASS':
        raise ValueError('within-vessel clearance unresolved; surface union blocked')
    node_ids = {n for e in selected for n in (e['start'], e['end'])}
    adjacency = {n:set() for n in node_ids}
    for edge in selected:
        adjacency[edge['start']].add(edge['end'])
        adjacency[edge['end']].add(edge['start'])
    remaining, components = set(node_ids), []
    while remaining:
        frontier, visited = [min(remaining)], set()
        while frontier:
            node = frontier.pop()
            if node in visited: continue
            visited.add(node)
            frontier.extend(adjacency[node]-visited)
        remaining -= visited
        components.append(visited)
    vertex_blocks, face_blocks, component_records, offset = [], [], [], 0
    for nodes in components:
        edges = [e for e in selected if e['start'] in nodes]
        graph = VesselGraph({n: np.asarray(case['nodes'][n]['position_mm'], dtype=float) for n in sorted(nodes)},
            [Segment('case-edge:' + e['id'], e['start'], e['end'], np.asarray(e['centerline_mm']),
                     float(e['radii_mm'][0]), np.asarray(e['radii_mm'])) for e in edges],
            {'radius_scale': 1.0}, provenance={'kind': 'synthetic-case-profile'})
        v, f = network_mesh(graph, spacing=spacing_mm)
        component_mesh = trimesh.Trimesh(vertices=v,faces=f,process=False)
        if not component_mesh.is_watertight or not component_mesh.is_winding_consistent:
            raise ValueError('generated component failed closed/oriented topology check')
        reverse = bool(component_mesh.volume < 0)
        if reverse: f = f[:,::-1].copy()
        if not trimesh.Trimesh(vertices=v,faces=f,process=False).is_volume:
            raise ValueError('generated component has no positive closed volume')
        vertex_blocks.append(v); face_blocks.append(f+offset); offset += len(v)
        component_records.append(dict(edge_ids=[e['id'] for e in edges],winding_reversed=reverse))
    vertices, faces = np.concatenate(vertex_blocks), np.concatenate(face_blocks)
    mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
    if not mesh.is_watertight or not mesh.is_winding_consistent:
        raise ValueError('generated surface failed closed/oriented topology check')
    # Marching cubes may use inward orientation. Record explicit generated-surface
    # orientation normalization; this never changes the source atlas.
    reversed_winding = bool(mesh.volume < 0)
    if reversed_winding:
        faces = faces[:, ::-1].copy()
        mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
    if not mesh.is_volume:
        raise ValueError('generated surface has no positive closed volume')
    metadata = {'schema': 'vv-toolbox.case-surface/1', 'case_id': case['case_id'],
        'case_revision': case_digest(case), 'frame': case['frame'].copy(),
        'edge_ids': list(edge_ids), 'provenance': 'estimated',
        'method': 'implicit-radius-profile-union', 'spacing_mm': spacing_mm,
        'grid_voxel_bound': estimate, 'winding_reversed': reversed_winding,
        'graph_components': component_records,
        'graph_component_count': len(components),
        'component_policy': 'Separate graph components remain separate; no inferred connecting geometry',
        'nonincident_clearance_screen': clearance,
        'junction_clearance_screen': junction_clearance,
        'self_clearance_screen': self_clearance,
        'self_clearance_local_window_policy': '4 * maximum edge radius + 2 * grid spacing; arc length mm',
        'junction_collar_policy': ('explicit case-bound junction regions' if junction_regions is not None else
                                  '3 * maximum incident endpoint radius + 2 * grid spacing; arc length mm'),
        'terminal_policy': 'closed caps; not anatomical terminal assertion',
        'checks': {'watertight': 'PASS', 'oriented_positive_volume': 'PASS',
                   'anatomical_connectivity': 'UNKNOWN', 'self_intersection': 'NOT RUN',
                   'clinical_validity': 'NOT RUN'},
        'limitations': 'Selected edge subset only; nearby swept paths may merge. No automatic segment or lesion face labels.'}
    return vertices, faces, metadata
