"""Snapshot a displayed access candidate without treating it as accepted anatomy."""
from copy import deepcopy
import hashlib
from pathlib import Path

import numpy as np

from .case_io import case_digest, load_case
from .case_source_surfaces import attach_surfaces


def displayed_candidate_snapshot(candidate, root):
    """Resolve a registered graph, then verify it matches the displayed candidate."""
    relative = ('exports/access-shape-edit-bend/graph.snapshot.json'
                if candidate['summary'].get('id') == 'access-femoral-bend-inspection'
                else 'exports/femoral-anterior-graph/case.snapshot.json')
    graph, _ = load_case(Path(root)/relative)
    return candidate_snapshot(candidate, graph)


def candidate_case(candidate, graph):
    summary = candidate['summary']
    revision = case_digest(graph)
    if revision != summary['access_graph']['revision'] or graph['edges'] != candidate['edges']:
        raise ValueError('Complete candidate graph identity mismatch')
    if graph['frame']['axes'] != 'LPS' or graph['frame']['units'] != 'mm':
        raise ValueError('Candidate requires LPS millimetres')
    vertices = np.asarray(candidate['vertices_mm'], dtype='<f8')
    if not np.issubdtype(np.asarray(candidate['faces']).dtype, np.integer):
        raise ValueError('Integer candidate faces required')
    faces = np.asarray(candidate['faces'], dtype='<i8')
    digest = hashlib.sha256(vertices.tobytes()+faces.tobytes()).hexdigest()
    if summary.get('geometry_sha256') and summary['geometry_sha256'] != digest:
        raise ValueError('Candidate edited geometry hash mismatch')
    result = deepcopy(graph)
    result.update(case_id='access-inspection-'+digest[:16], model_kind='synthetic')
    result['generation'] = dict(seed=0, generator_version='registered-access-inspection/1',
        config=dict(parent_graph_revision=revision, parent_generation=deepcopy(graph['generation']),
                    source_case_revision=summary['revision'], geometry_sha256=digest))
    result['candidate_surface_reference'] = dict(geometry_sha256=digest,
        parent_surface_sha256=summary.get('parent_surface_sha256', summary.get('surface_sha256')),
        role='inspection snapshot; not accepted for generation')
    result.setdefault('inspection', {})['access_candidate'] = dict(
        summary=deepcopy(summary), context=deepcopy(candidate.get('geometry_context', candidate.get('radius_context'))),
        anatomical_segment_coverage='UNKNOWN', radius_surface_consistency='NOT RUN',
        graph_radii_role='Preserved source graph radii; not measured from edited surface',
        accepted_for_generation=False)
    return attach_surfaces(result, [dict(part_id='access-union',
        edge_ids=[edge['id'] for edge in graph['edges']], frame_id=graph['frame']['id'],
        provenance='estimated', source_ids=[s['id'] for s in graph['sources']],
        vertices_mm=vertices.tolist(), faces=faces.tolist(),
        face_lineage=deepcopy(candidate['face_lineage']),
        lineage_scope='Inherited source ownership; not reviewed anatomical labels or original-coordinate validation')])


def candidate_snapshot(candidate, graph):
    case = candidate_case(candidate, graph)
    return dict(schema='vv-toolbox.case-snapshot/1', revision=case_digest(case), case=case)
