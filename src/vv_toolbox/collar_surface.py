"""Double precision open tube diagnostics; no fused-junction acceptance."""
import numpy as np
import trimesh

from .surface_indexing import exact_vertex_index_copy


def build_sampled_wall(points, radii, *, sides=32):
    points, radii = np.asarray(points, dtype=float), np.asarray(radii, dtype=float)
    if (points.ndim != 2 or points.shape[1] != 3 or len(points) < 2
            or not np.isfinite(points).all() or radii.shape != (len(points),)
            or not np.isfinite(radii).all() or np.any(radii <= 0)
            or type(sides) is not int or not 3 <= sides <= 256):
        raise ValueError("Finite paths, positive radii and bounded side count required")
    tangents = np.gradient(points, axis=0)
    norms = np.linalg.norm(tangents, axis=1)
    if np.any(norms <= 1e-12) or np.any(np.linalg.norm(np.diff(points, axis=0), axis=1) <= 1e-12):
        raise ValueError("Nondegenerate centerline required")
    tangents /= norms[:, None]
    previous = np.eye(3)[np.argmin(np.abs(tangents[0]))]
    rings = []
    angles = np.linspace(0, 2*np.pi, sides, endpoint=False)
    for point, radius, tangent in zip(points, radii, tangents):
        normal = previous - np.dot(previous, tangent)*tangent
        if np.linalg.norm(normal) < 1e-8:
            reference = np.eye(3)[np.argmin(np.abs(tangent))]
            normal = reference-np.dot(reference, tangent)*tangent
        previous = normal/np.linalg.norm(normal)
        binormal = np.cross(tangent, previous)
        rings.append(point + radius*(np.cos(angles)[:, None]*previous +
                                     np.sin(angles)[:, None]*binormal))
    faces = []
    for i in range(len(points)-1):
        for j in range(sides):
            a, b = i*sides+j, i*sides+(j+1) % sides
            faces.extend([(a, b, a+sides), (b, b+sides, a+sides)])
    return trimesh.Trimesh(np.asarray(rings).reshape(-1, 3), faces, process=False)


def inspect_wall_vertices(container, wall, *, tolerance_mm=1e-6):
    """An outside vertex disproves wall containment; inside vertices cannot prove it."""
    if not np.isfinite(tolerance_mm) or tolerance_mm <= 0:
        raise ValueError("Positive finite tolerance required")
    container, indexing = exact_vertex_index_copy(container)
    points = np.asarray(wall.vertices)
    if not len(points) or not np.isfinite(points).all():
        raise ValueError("Finite nonempty wall required")
    report = dict(status="UNKNOWN", method="sampled-wall-vertices/1", vertices=len(points),
                  outside_count=0, boundary_count=0, witnesses=[], tolerance_mm=tolerance_mm,
                  whole_wall_containment="NOT RUN", surface_self_contact="NOT RUN")
    if not indexing["usable_for_sampled_containment"]:
        report["reason"] = "Container is not a closed oriented solid"
        return report
    for start in range(0, len(points), 128):
        query = points[start:start+128]
        inside = container.contains(query)
        _, distances, _ = trimesh.proximity.closest_point(container, query)
        if not np.isfinite(distances).all():
            report["reason"] = "Nonfinite surface distance"
            return report
        boundary = distances <= tolerance_mm
        outside = ~inside & ~boundary
        report["boundary_count"] += int(boundary.sum())
        report["outside_count"] += int(outside.sum())
        for local in np.flatnonzero(outside):
            if len(report["witnesses"]) < 16:
                report["witnesses"].append(dict(vertex_index=start+int(local),
                    position_mm=query[local].tolist(), distance_mm=float(distances[local])))
    report["status"] = "FAIL" if report["outside_count"] else "UNKNOWN"
    report["vertex_inspection"] = "COMPLETE"
    report["reason"] = "Outside wall vertices" if report["outside_count"] else "Triangle interiors not inspected"
    return report
