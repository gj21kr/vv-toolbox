"""Delaunay candidate with exact boundary and planar area verification."""
import numpy as np
from scipy.spatial import Delaunay

from vv_toolbox.patch_boundary import patch_boundary_loops


def contains(polygon, points):
    inside = np.zeros(len(points), dtype=bool)
    for a, b in zip(polygon, np.roll(polygon, -1, axis=0)):
        if a[1] == b[1]:
            continue
        crossing = ((a[1] > points[:, 1]) != (b[1] > points[:, 1]))
        x = a[0]+(points[:, 1]-a[1])*(b[0]-a[0])/(b[1]-a[1])
        inside ^= crossing & (points[:, 0] < x)
    return inside


def improve_interior_edges(vertices, faces, center, basis, max_sweeps=20):
    """Flip only convex projected internal diagonals when 3D quality improves."""
    faces = np.asarray(faces).copy()
    v = np.asarray(vertices)
    xy = ((v-center)@basis)[:, :2]

    def signed(triangle):
        a, b, c = xy[triangle]
        return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])

    def cost(pair):
        p = v[pair]
        twice_area = np.linalg.norm(np.cross(p[:, 1]-p[:, 0], p[:, 2]-p[:, 0]), axis=1)
        if np.any(twice_area <= 1e-14):
            return np.inf
        return float(np.sum(np.sum((np.roll(p, -1, axis=1)-p)**2, axis=(1, 2))/twice_area))

    for i, triangle in enumerate(faces):
        if signed(triangle) < 0:
            faces[i] = triangle[::-1]
    for _ in range(max_sweeps):
        adjacency = {}
        for i, triangle in enumerate(faces):
            for a, b in zip(triangle, np.roll(triangle, -1)):
                adjacency.setdefault(tuple(sorted((int(a), int(b)))), []).append(i)
        touched = set()
        flips = 0
        for (a, b), pair in adjacency.items():
            if len(pair) != 2 or touched.intersection(pair):
                continue
            i, j = pair
            c = next(int(x) for x in faces[i] if x not in (a, b))
            d = next(int(x) for x in faces[j] if x not in (a, b))
            if c == d or tuple(sorted((c, d))) in adjacency:
                continue
            # Both old endpoints must lie on opposite sides of the new edge.
            if signed([c, d, a])*signed([c, d, b]) >= -1e-20:
                continue
            proposed = np.array([[c, d, a], [d, c, b]])
            for k in range(2):
                if signed(proposed[k]) < 0:
                    proposed[k] = proposed[k, ::-1]
            if cost(proposed) < cost(faces[[i, j]])*(1-1e-10):
                faces[[i, j]] = proposed
                touched.update(pair)
                flips += 1
        if not flips:
            break
    return faces


def triangulate_annulus(vertices, inner, outer, center, basis, *, engine='delaunay', improve=False):
    """Reject any triangulation which cannot preserve both supplied polygons."""
    ids = np.r_[inner, outer].astype(int)
    if len(set(ids.tolist())) != len(ids):
        raise ValueError('annulus boundaries must be disjoint and unique')
    xy = ((np.asarray(vertices)[ids]-center)@basis)[:, :2]
    n = len(inner)
    if n < 3 or len(outer) < 3 or not np.isfinite(xy).all():
        raise ValueError('finite polygon rings required')
    inner_xy, outer_xy = xy[:n], xy[n:]
    if engine == 'earcut':
        import mapbox_earcut
        order = np.r_[np.arange(n, len(ids)), np.arange(n)]
        triangles = order[mapbox_earcut.triangulate_float64(
            np.ascontiguousarray(xy[order]), np.array([len(outer), len(ids)], dtype=np.uint32)).reshape(-1, 3)]
    elif engine == 'delaunay':
        triangles = Delaunay(xy).simplices
        centroids = xy[triangles].mean(axis=1)
        keep = contains(outer_xy, centroids) & ~contains(inner_xy, centroids)
        triangles = triangles[keep]
    else:
        raise ValueError('unknown triangulation engine')
    if not len(triangles):
        raise ValueError('empty projected annulus')
    faces = ids[triangles]
    loops = patch_boundary_loops(faces, np.arange(len(faces)))

    def edges(ring):
        return {tuple(sorted((int(a), int(b)))) for a, b in
                zip(ring, np.roll(ring, -1))}

    actual = set().union(*(edges(loop) for loop in loops))
    if len(loops) != 2 or actual != edges(inner) | edges(outer):
        raise ValueError('triangulation candidate does not preserve exact polygon boundaries')

    def area(p):
        return .5*abs(np.sum(p[:, 0]*np.roll(p[:, 1], -1)-p[:, 1]*np.roll(p[:, 0], -1)))

    p = xy[triangles]
    cross = ((p[:, 1, 0]-p[:, 0, 0])*(p[:, 2, 1]-p[:, 0, 1]) -
             (p[:, 1, 1]-p[:, 0, 1])*(p[:, 2, 0]-p[:, 0, 0]))
    expected = area(outer_xy)-area(inner_xy)
    if expected <= 0 or not np.isclose(.5*np.abs(cross).sum(), expected, atol=1e-10, rtol=1e-9):
        raise ValueError('projected annulus area mismatch')
    if improve:
        faces = improve_interior_edges(vertices, faces, center, basis)
        loops = patch_boundary_loops(faces, np.arange(len(faces)))
        if set().union(*(edges(loop) for loop in loops)) != edges(inner) | edges(outer):
            raise ValueError('edge improvement changed boundary')
    return faces
