"""Bind editable source paths to the exact case behind a union candidate."""
import numpy as np


def bind_source_centerlines(case, revision, expected_revision, source_names):
    """Ambiguous paths remain unavailable; never choose a path by length."""
    if revision != expected_revision:
        raise ValueError('Candidate centerline case revision mismatch')
    parts = case['surface_parts']
    edges = case['edges']
    metadata = case.get('inspection', {}).get('atlas_scene_capture', {}).get('estimated_metadata', {})
    paths, unavailable = {}, {}
    for name in source_names:
        matches = [part for part in parts if part['part_id'] == name]
        if len(matches) != 1:
            unavailable[name] = 'Unique source part required'
            continue
        ids = matches[0]['edge_ids']
        if len(ids) != 1:
            unavailable[name] = 'Select an explicit branch path before editing'
            continue
        matches = [edge for edge in edges if edge['id'] == ids[0]]
        if len(matches) != 1:
            unavailable[name] = 'Unique source edge required'
            continue
        declared = metadata.get(name, {}).get('centerline')
        points = np.asarray(declared if declared is not None else matches[0]['centerline_mm'], dtype=float)
        if (points.ndim != 2 or points.shape[1] != 3 or len(points) < 2
                or not np.isfinite(points).all()
                or np.any(np.linalg.norm(np.diff(points, axis=0), axis=1) <= 1e-12)):
            unavailable[name] = 'Finite distinct centerline stations required'
            continue
        paths[name] = dict(points_mm=points.copy(), edge_id=ids[0],
                           provenance='declared-estimate' if declared is not None else 'case-source-path',
                           case_revision=revision)
    return paths, unavailable
