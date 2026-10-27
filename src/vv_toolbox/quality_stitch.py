"""Geometry-aware monotone annulus triangulation with fixed boundary IDs."""
import numpy as np


def quality_stitch(vertices, first, second, reference_normals=None):
    """Minimize summed inverse triangle quality over a bounded zipper path.

    The seam and cyclic order are supplied by the caller. This is a mesh
    construction objective, not a self-intersection or smoothness certificate.
    """
    v = np.asarray(vertices, dtype=float)
    a, b = np.asarray(first), np.asarray(second)
    if (v.ndim != 2 or v.shape[1] != 3 or not np.isfinite(v).all()
            or any(x.ndim != 1 or len(x) < 3 or not np.issubdtype(x.dtype, np.integer)
                   or np.any(x < 0) or np.any(x >= len(v)) for x in (a, b))
            or len(set(a.tolist()) | set(b.tolist())) != len(a)+len(b)):
        raise ValueError('finite vertices and unique disjoint ordered boundary IDs required')
    n, m = len(a), len(b)
    normals = None if reference_normals is None else np.asarray(reference_normals, dtype=float)
    if normals is not None and (normals.shape != v.shape or not np.isfinite(normals).all()):
        raise ValueError('finite per-vertex reference normals required')

    def cost(ids):
        p = v[ids]
        cross = np.cross(p[1]-p[0], p[2]-p[0])
        twice_area = np.linalg.norm(cross)
        if normals is not None and np.dot(cross, normals[ids].sum(axis=0)) <= 0:
            return np.inf
        squared = np.sum((np.roll(p, -1, axis=0)-p)**2)
        quality = 2*np.sqrt(3)*twice_area/squared if squared > 0 else 0
        return 1/quality if quality > 1e-8 else np.inf

    distance = np.full((n+1, m+1), np.inf)
    previous = np.zeros((n+1, m+1), dtype=np.int8)
    distance[0, 0] = 0.
    for i in range(n+1):
        for j in range(m+1):
            # Avoid a complete circuit of one ring before advancing the other.
            # This window is a fixed construction restriction, not a fit gate.
            if abs(i/n-j/m) > .25:
                continue
            if i:
                value = distance[i-1, j]+cost([a[(i-1) % n], a[i % n], b[j % m]])
                if value < distance[i, j]:
                    distance[i, j], previous[i, j] = value, 1
            if j:
                value = distance[i, j-1]+cost([a[i % n], b[j % m], b[(j-1) % m]])
                if value < distance[i, j]:
                    distance[i, j], previous[i, j] = value, 2
    if not np.isfinite(distance[n, m]):
        raise ValueError('no nondegenerate bounded triangulation path')
    i, j, faces = n, m, []
    while i or j:
        if previous[i, j] == 1:
            faces.append([a[(i-1) % n], a[i % n], b[j % m]])
            i -= 1
        elif previous[i, j] == 2:
            faces.append([a[i % n], b[j % m], b[(j-1) % m]])
            j -= 1
        else:
            raise ValueError('incomplete triangulation path')
    return np.asarray(faces[::-1], dtype=np.int64)
