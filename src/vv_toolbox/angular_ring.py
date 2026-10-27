"""Use a shared geometric polar coordinate without reordering mesh edges."""
import numpy as np


def angular_ring(ids, vertices, center, basis):
    ids = np.asarray(ids, dtype=np.int64)
    xy = ((np.asarray(vertices)[ids]-center)@basis)[:, :2]
    area = np.sum(xy[:, 0]*np.roll(xy[:, 1], -1)-xy[:, 1]*np.roll(xy[:, 0], -1))
    if area < 0:
        ids, xy = ids[::-1], xy[::-1]
    polar = np.mod(np.arctan2(xy[:, 1], xy[:, 0]), 2*np.pi)
    start = int(np.argmin(polar))
    ids, polar = np.roll(ids, -start), np.roll(polar, -start)
    if np.any(np.diff(polar) <= 1e-12):
        raise ValueError('ring is not strictly star-shaped in shared neck projection')
    if np.any(np.linalg.norm(xy, axis=1) <= 1e-12):
        raise ValueError('ring crosses polar origin')
    # Keep the actual phase: interpolation uses periodic wrap on both sides.
    return ids, polar


def stitch_polar_rings(a, ta, b, tb):
    """Triangulate rings with unequal geometric seam phases in [0, 2*pi)."""
    for ids, angles in ((a, ta), (b, tb)):
        if (len(ids) < 3 or len(ids) != len(angles) or
                not np.isfinite(angles).all() or np.any(np.diff(angles) <= 0)
                or angles[0] < 0 or angles[-1] >= 2*np.pi):
            raise ValueError('ordered periodic ring required')
    if len(set(a) | set(b)) != len(a)+len(b):
        raise ValueError('unique disjoint ring IDs required')
    events = sorted([(float(t), 0, int(i)) for i, t in zip(a, ta)] +
                    [(float(t), 1, int(i)) for i, t in zip(b, tb)])
    ai, bi = int(a[-1]), int(b[-1])
    faces = []
    for _, side, index in events:
        if side == 0:
            faces.append([ai, index, bi])
            ai = index
        else:
            faces.append([ai, index, bi])
            bi = index
    return np.asarray(faces, dtype=np.int64)
