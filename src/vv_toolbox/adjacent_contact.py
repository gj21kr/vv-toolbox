"""Check contact beyond explicitly shared vertex/edge topology."""
import numpy as np


def overlap_beyond_shared(first, second, shared, tolerance_mm=1e-8):
    """Geometric overlap beyond shared topology; not a clearance-distance test."""
    a, b, shared = (np.asarray(x, dtype=float) for x in (first, second, shared))
    if (a.shape != (3, 3) or b.shape != (3, 3) or shared.shape not in ((1, 3), (2, 3))
            or not all(np.isfinite(x).all() for x in (a, b, shared))
            or not np.isfinite(tolerance_mm) or tolerance_mm <= 0):
        raise ValueError('finite triangles and one or two shared positions required')
    for p in shared:
        if not np.any(np.linalg.norm(a-p, axis=1) <= tolerance_mm) or not np.any(np.linalg.norm(b-p, axis=1) <= tolerance_mm):
            raise ValueError('declared shared point absent from triangle')
    origin = shared[0].copy()
    a, b, shared = a-origin, b-origin, shared-origin
    na = np.cross(a[1]-a[0], a[2]-a[0])
    nb = np.cross(b[1]-b[0], b[2]-b[0])
    if min(np.linalg.norm(na), np.linalg.norm(nb)) <= 1e-14:
        raise ValueError('degenerate adjacent triangle')
    na, nb = na/np.linalg.norm(na), nb/np.linalg.norm(nb)
    axis = np.cross(na, nb)
    if np.linalg.norm(axis) > 1e-10:
        # Distinct planes with a shared edge intersect only along that edge.
        if len(shared) == 2:
            return False
        axis /= np.linalg.norm(axis)

        def interval(triangle, normal):
            signed = triangle@normal
            # Shared origin is exactly on both planes. Treating every point
            # within the distance tolerance as on-plane expands a near-coplanar
            # triangle into a false intersection interval.
            points = [p for p, d in zip(triangle, signed) if d == 0.]
            for i, j in ((0, 1), (1, 2), (2, 0)):
                if signed[i]*signed[j] < 0:
                    t = signed[i]/(signed[i]-signed[j])
                    points.append(triangle[i]+t*(triangle[j]-triangle[i]))
            projected = np.asarray(points)@axis
            return projected.min(), projected.max()

        alo, ahi = interval(a, nb)
        blo, bhi = interval(b, na)
        lo, hi = max(alo, blo), min(ahi, bhi)
        return bool(lo <= hi+tolerance_mm and (lo < -tolerance_mm or hi > tolerance_mm))
    # Coplanar: clip in a stable 2D projection, then compare the complete
    # intersection polygon with the allowed shared point or segment.
    drop = int(np.argmax(np.abs(na)))
    keep = [i for i in range(3) if i != drop]
    pa, pb, ps = a[:, keep], b[:, keep], shared[:, keep]
    cross2 = lambda x, y: x[0]*y[1]-x[1]*y[0]
    if cross2(pb[1]-pb[0], pb[2]-pb[0]) < 0:
        pb = pb[::-1]
    polygon = list(pa)
    for x, y in zip(pb, np.roll(pb, -1, axis=0)):
        edge = y-x
        scale = np.linalg.norm(edge)
        output = []
        if not polygon:
            return False
        previous = polygon[-1]
        dp = cross2(edge, previous-x)/scale
        for current in polygon:
            dc = cross2(edge, current-x)/scale
            # Clip the geometric half-plane, not a tolerance-expanded polygon.
            # Expansion around a shared vertex creates spurious overlap whose
            # distance can exceed tolerance at an acute corner.
            inp, inc = dp >= 0., dc >= 0.
            if inp != inc and abs(dp-dc) > 1e-15:
                output.append(previous+np.clip(dp/(dp-dc), 0, 1)*(current-previous))
            if inc:
                output.append(current)
            previous, dp = current, dc
        polygon = output
    if not polygon:
        return False
    projected = np.asarray(polygon)
    # Dropping a coordinate shortens distances on a tilted plane. Lift the
    # clipped polygon back to that plane before applying the millimetre limit.
    points = np.zeros((len(projected), 3))
    points[:, keep] = projected
    points[:, drop] = -(projected@na[keep])/na[drop]
    if len(shared) == 1:
        distances = np.linalg.norm(points-shared[0], axis=1)
    else:
        delta = shared[1]-shared[0]
        squared = delta@delta
        if squared <= 1e-24:
            raise ValueError('degenerate shared edge')
        t = np.clip((points-shared[0])@delta/squared, 0, 1)
        distances = np.linalg.norm(points-shared[0]-t[:, None]*delta, axis=1)
    return bool(np.any(distances > tolerance_mm))
