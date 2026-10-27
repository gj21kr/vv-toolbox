"""Conservative finite-precision contact test for triangle pairs."""
import numpy as np


def triangle_contacts(first, second, tolerance_mm=1e-8):
    """SAT contact including coplanar pairs; touching within tolerance is contact."""
    a, b = np.asarray(first, dtype=float), np.asarray(second, dtype=float)
    if (a.ndim != 3 or a.shape[1:] != (3, 3) or b.shape != a.shape
            or not np.isfinite(a).all() or not np.isfinite(b).all()
            or not np.isfinite(tolerance_mm) or tolerance_mm < 0):
        raise ValueError('finite matched triangle batches and nonnegative tolerance required')
    b, a = b-a[:, :1], a-a[:, :1]
    ea, eb = np.roll(a, -1, axis=1)-a, np.roll(b, -1, axis=1)-b
    na = np.cross(ea[:, 0], ea[:, 1])
    nb = np.cross(eb[:, 0], eb[:, 1])
    if np.any(np.linalg.norm(na, axis=1) <= 1e-14) or np.any(np.linalg.norm(nb, axis=1) <= 1e-14):
        raise ValueError('degenerate triangle')
    axes = np.concatenate([na[:, None], nb[:, None],
                           np.cross(ea[:, :, None], eb[:, None]).reshape(-1, 9, 3),
                           np.cross(na[:, None], ea), np.cross(nb[:, None], eb)], axis=1)
    lengths = np.linalg.norm(axes, axis=2)
    valid = lengths > 1e-14
    axes = axes/np.where(valid, lengths, 1)[:, :, None]
    pa = np.einsum('nac,nvc->nav', axes, a)
    pb = np.einsum('nac,nvc->nav', axes, b)
    separated = ((pa.max(axis=2) < pb.min(axis=2)-tolerance_mm) |
                 (pb.max(axis=2) < pa.min(axis=2)-tolerance_mm)) & valid
    return ~separated.any(axis=1)
