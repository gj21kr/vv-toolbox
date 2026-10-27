"""Hermite transition rings with explicit endpoint derivatives.

Correspondence must be supplied by the caller. This constructs geometry, not
an anatomical correspondence or a self-intersection certificate.
"""
import numpy as np


def hermite_rings(start, end, start_derivative, end_derivative, stations):
    """Sample matched periodic rings and their derivatives in parameter u.

    Derivatives are displacement per unit u (not unit vectors). Their magnitude
    controls the transition. Endpoints are returned byte-exact when requested.
    The caller must check the triangulated patch and both outside joins.
    """
    arrays = [np.asarray(a, dtype=float) for a in
              (start, end, start_derivative, end_derivative)]
    a, b, da, db = arrays
    if (a.ndim != 2 or a.shape[1] != 3 or len(a) < 3
            or any(x.shape != a.shape or not np.isfinite(x).all() for x in arrays)):
        raise ValueError("matched finite N-by-3 rings and derivatives required")
    u = np.asarray(stations, dtype=float)
    if (u.ndim != 1 or len(u) < 2 or not np.isfinite(u).all()
            or u[0] != 0 or u[-1] != 1 or np.any(np.diff(u) <= 0)):
        raise ValueError("strictly increasing stations from zero to one required")
    if any(np.any(np.linalg.norm(d, axis=1) <= 1e-12) for d in (da, db)):
        raise ValueError("nonzero endpoint derivatives required")
    # Work relative to the start ring for translation stability.
    delta = b - a
    t = u[:, None, None]
    rings = a + (-2*t**3 + 3*t**2)*delta + (t**3-2*t**2+t)*da + (t**3-t**2)*db
    derivatives = (-6*t**2+6*t)*delta + (3*t**2-4*t+1)*da + (3*t**2-2*t)*db
    rings[0], rings[-1] = a, b
    derivatives[0], derivatives[-1] = da, db
    if not np.isfinite(rings).all() or not np.isfinite(derivatives).all():
        raise ValueError("nonfinite transition geometry")
    return rings, derivatives
