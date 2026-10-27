"""Exact triangle subsets with explicit source indices and boundary interfaces."""
import hashlib

import numpy as np
import trimesh

from .patch_boundary import patch_boundary_loops


def extract_source_patch(vertices, faces, selected_faces):
    vertices, faces, selected = np.asarray(vertices, dtype=float), np.asarray(faces), np.asarray(selected_faces)
    if (vertices.ndim != 2 or vertices.shape[1] != 3 or not np.isfinite(vertices).all()
            or faces.ndim != 2 or faces.shape[1] != 3 or not np.issubdtype(faces.dtype, np.integer)
            or not len(faces) or faces.min() < 0 or faces.max() >= len(vertices)
            or selected.ndim != 1 or not len(selected) or not np.issubdtype(selected.dtype, np.integer)
            or selected.min() < 0 or selected.max() >= len(faces)
            or len(np.unique(selected)) != len(selected)):
        raise ValueError('Finite mesh and unique valid selected faces required')
    ids, inverse = np.unique(faces[selected], return_inverse=True)
    local_faces = inverse.reshape(-1, 3)
    local_vertices = vertices[ids].copy()
    before = vertices[faces[selected]].astype('<f8').tobytes()
    if before != local_vertices[local_faces].astype('<f8').tobytes():
        raise ValueError('Source triangle coordinates changed')
    mesh = trimesh.Trimesh(local_vertices, local_faces, process=False)
    report = dict(status='EXTRACTED', source_triangle_identity='PASS',
        triangle_sha256=hashlib.sha256(before).hexdigest(),
        source_modified=False, faces=len(local_faces), vertices=len(local_vertices),
        components=len(mesh.split(only_watertight=False)), anatomical_validation='NOT RUN',
        boundary_compatibility='NOT RUN')
    try:
        loops = patch_boundary_loops(local_faces, np.arange(len(local_faces)))
        report.update(boundary_topology='SIMPLE_LOOPS', boundary_loops_source_vertex_ids=[ids[loop].tolist() for loop in loops])
    except ValueError as error:
        report.update(boundary_topology='UNKNOWN', boundary_reason=str(error), boundary_loops_source_vertex_ids=[])
    return dict(vertices=local_vertices, faces=local_faces, source_vertex_ids=ids,
                source_face_ids=selected.copy(), report=report)
