"""Source-surface junction candidates bounded by explicit branch port planes."""
import numpy as np
import trimesh

from .patch_boundary import patch_boundary_loops


def clip_source_junction(mesh, origins_mm, outward_normals, junction_mm):
    """Keep each plane's inner halfspace, with exactly one boundary per port.

    This does not choose anatomical port locations or attach replacement arms.
    Faces are partitions of source triangles, never a new bridging surface.
    """
    origins = np.asarray(origins_mm, float)
    normals = np.asarray(outward_normals, float)
    junction = np.asarray(junction_mm, float)
    if (origins.ndim != 2 or origins.shape[1] != 3 or not 3 <= len(origins) <= 8
            or normals.shape != origins.shape or junction.shape != (3,)
            or not all(np.isfinite(a).all() for a in (origins, normals, junction))
            or np.any(np.abs(np.linalg.norm(normals, axis=1)-1) > 1e-8)):
        raise ValueError('Three to eight finite port planes with unit normals required')
    if np.any(np.einsum('ij,ij->i', junction-origins, normals) >= -1e-8):
        raise ValueError('Junction must be strictly inside every port plane')
    if not mesh.is_watertight or not mesh.is_winding_consistent or mesh.volume <= 0:
        raise ValueError('Closed consistently oriented positive source required')
    if not np.isfinite(mesh.vertices).all() or np.any(mesh.area_faces <= 1e-12):
        raise ValueError('Nondegenerate finite source required')
    vertices = []
    faces = []
    source_ids = []
    for face_id, triangle in enumerate(mesh.triangles):
        polygon = list(triangle.copy())
        for origin, normal in zip(origins, normals):
            clipped = []
            for a, b in zip(polygon, polygon[1:]+polygon[:1]):
                da, db = float((a-origin)@normal), float((b-origin)@normal)
                if da <= 0:
                    clipped.append(a)
                if (da < 0 < db) or (db < 0 < da):
                    clipped.append(a + da/(da-db)*(b-a))
            polygon = clipped
            if len(polygon) < 3:
                break
        if len(polygon) < 3:
            continue
        for k in range(1, len(polygon)-1):
            tri = np.asarray([polygon[0], polygon[k], polygon[k+1]])
            if np.linalg.norm(np.cross(tri[1]-tri[0], tri[2]-tri[0])) <= 2e-12:
                continue
            faces.append(list(range(len(vertices), len(vertices)+3)))
            vertices.extend(tri)
            source_ids.append(face_id)
    if not faces:
        raise ValueError('No source surface remains')
    patch = trimesh.Trimesh(vertices, faces, process=False)
    # Merge numerical copies at shared clipped edges; retain actual coordinates.
    patch.merge_vertices(digits_vertex=9)
    source_ids = np.asarray(source_ids, dtype=np.int64)
    if np.any(patch.area_faces <= 1e-12) or not patch.is_winding_consistent:
        raise ValueError('Clipped patch contains degenerate or inconsistent faces')
    original = mesh.triangles[source_ids]
    for corner in range(3):
        points = patch.triangles[:, corner]
        bary = trimesh.triangles.points_to_barycentric(original, points)
        reconstructed = np.einsum('ij,ijk->ik', bary, original)
        if (not np.isfinite(bary).all() or np.min(bary) < -1e-8
                or np.max(bary) > 1+1e-8
                or np.max(np.linalg.norm(points-reconstructed, axis=1)) > 1e-8):
            raise ValueError('Source triangle partition identity failed')
    if len(patch.split(only_watertight=False)) != 1:
        raise ValueError('Port planes leave disconnected surface components')
    loops = patch_boundary_loops(patch.faces, np.arange(len(patch.faces)))
    ports = {}
    for loop in loops:
        points = patch.vertices[loop]
        matches = [i for i, (o, n) in enumerate(zip(origins, normals))
                   if np.max(np.abs((points-o)@n)) <= 1e-8]
        if len(matches) != 1 or matches[0] in ports:
            raise ValueError('Boundary is mixed, ambiguous, or duplicated across ports')
        ports[matches[0]] = loop
    if set(ports) != set(range(len(origins))):
        raise ValueError('Every branch port must have exactly one boundary loop')
    return patch, source_ids, dict(status='CANDIDATE', method='source-halfspace-junction/1',
        source_partition_identity='PASS', components=1,
        port_boundary_vertex_ids=[ports[i] for i in range(len(origins))],
        self_contact='NOT RUN', arm_attachment='NOT RUN', anatomical_validation='NOT RUN',
        accepted_for_generation=False)
