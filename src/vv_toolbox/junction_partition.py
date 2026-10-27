"""Conforming source partitions for a junction and all its unmodified arms."""
import numpy as np
import trimesh

from .junction_source_patch import clip_source_junction
from .patch_boundary import patch_boundary_loops


def partition_source_junction(mesh, origins_mm, outward_normals, junction_mm):
    """Split all faces by all port planes; preserve both sides of every cut.

    The result is the original surface with shared seam indices, not a smoothed
    or edited vessel. Port selection is explicit and remains unvalidated.
    """
    clip_source_junction(mesh, origins_mm, outward_normals, junction_mm)
    origins, normals = np.asarray(origins_mm, float), np.asarray(outward_normals, float)
    vertices, faces, lineage, masks = [], [], [], []
    for source_id, triangle in enumerate(mesh.triangles):
        pieces = [(list(triangle.copy()), 0)]
        for plane_id, (origin, normal) in enumerate(zip(origins, normals)):
            split = []
            for polygon, mask in pieces:
                distances = [float((p-origin)@normal) for p in polygon]
                if max(distances) <= 0:
                    split.append((polygon, mask))
                    continue
                if min(distances) >= 0:
                    split.append((polygon, mask | (1 << plane_id)))
                    continue
                inside, outside = [], []
                for k, a in enumerate(polygon):
                    b = polygon[(k+1) % len(polygon)]
                    da, db = distances[k], distances[(k+1) % len(polygon)]
                    if da <= 0:
                        inside.append(a)
                    if da >= 0:
                        outside.append(a)
                    if (da < 0 < db) or (db < 0 < da):
                        crossing = a + da/(da-db)*(b-a)
                        inside.append(crossing)
                        outside.append(crossing)
                split.extend([(inside, mask), (outside, mask | (1 << plane_id))])
            pieces = split
        for polygon, mask in pieces:
            if len(polygon) < 3:
                raise ValueError('Degenerate source partition polygon')
            for k in range(1, len(polygon)-1):
                tri = np.asarray([polygon[0], polygon[k], polygon[k+1]])
                if np.linalg.norm(np.cross(tri[1]-tri[0], tri[2]-tri[0])) <= 2e-12:
                    continue
                faces.append(list(range(len(vertices), len(vertices)+3)))
                vertices.extend(tri)
                lineage.append(source_id)
                masks.append(mask)
    result = trimesh.Trimesh(vertices, faces, process=False)
    result.merge_vertices(digits_vertex=9)
    lineage, masks = np.asarray(lineage, np.int64), np.asarray(masks, np.int64)
    if (not result.is_watertight or not result.is_winding_consistent
            or np.any(result.area_faces <= 1e-12) or result.volume <= 0):
        raise ValueError('Partition reassembly is not a closed oriented surface')
    original = mesh.triangles[lineage]
    for corner in range(3):
        points = result.triangles[:, corner]
        bary = trimesh.triangles.points_to_barycentric(original, points)
        reconstructed = np.einsum('ij,ijk->ik', bary, original)
        if (not np.isfinite(bary).all() or bary.min() < -1e-8 or bary.max() > 1+1e-8
                or np.max(np.linalg.norm(points-reconstructed, axis=1)) > 1e-8):
            raise ValueError('Source triangle partition correspondence failed')
    areas = np.bincount(lineage, weights=result.area_faces, minlength=len(mesh.faces))
    if not np.allclose(areas, mesh.area_faces, rtol=1e-8, atol=1e-10):
        raise ValueError('Source face coverage mismatch')
    selected = np.flatnonzero(masks == 0)
    loops = patch_boundary_loops(result.faces, selected)
    adjacency = result.face_adjacency
    outer = np.flatnonzero(masks != 0)
    outer_adjacency = adjacency[np.all(masks[adjacency] != 0, axis=1)]
    components = trimesh.graph.connected_components(outer_adjacency, nodes=outer)
    if len(components) != len(origins):
        raise ValueError('Expected one connected source arm per port')
    junction_adjacency = adjacency[np.all(masks[adjacency] == 0, axis=1)]
    if len(trimesh.graph.connected_components(junction_adjacency, nodes=selected)) != 1:
        raise ValueError('Junction patch is disconnected')
    labels = np.zeros(len(result.faces), np.int64)
    ports = {}
    for loop in loops:
        matches = [i for i, (o, n) in enumerate(zip(origins, normals))
                   if np.max(np.abs((result.vertices[loop]-o)@n)) <= 1e-8]
        if len(matches) != 1 or matches[0] in ports:
            raise ValueError('Ambiguous or duplicate port boundary')
        ports[matches[0]] = loop
    if set(ports) != set(range(len(origins))):
        raise ValueError('Missing port boundary')
    mapped = set()
    for component in components:
        arm_loops = patch_boundary_loops(result.faces, np.asarray(component))
        matches = [i for i, loop in ports.items()
                   if len(arm_loops) == 1 and set(arm_loops[0]) == set(loop)]
        if len(matches) != 1 or matches[0] in mapped:
            raise ValueError('Arm does not share exactly its junction boundary')
        mapped.add(matches[0])
        labels[component] = matches[0]+1
    return result, lineage, labels, dict(status='CANDIDATE', method='conforming-source-junction-partition/1',
        source_partition_identity='PASS', source_face_coverage='PASS',
        maximum_source_face_area_error_mm2=float(np.max(np.abs(areas-mesh.area_faces))),
        shared_seam_indices='PASS', watertight=True, winding_consistent=True,
        port_boundary_vertex_ids=[ports[i] for i in range(len(origins))],
        region_face_counts=[int(np.sum(labels == i)) for i in range(len(origins)+1)],
        region_labels='0 junction; 1..N arms in supplied port order',
        self_contact='NOT RUN', modification='NOT RUN', anatomical_validation='NOT RUN',
        accepted_for_generation=False)
