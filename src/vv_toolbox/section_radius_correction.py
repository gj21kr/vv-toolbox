"""Experimental measured-section correction; no collision validity guarantee."""
import numpy as np


def correct_radially(vertices, centerline, gains, weights):
    """Apply interpolated positive gains about a single fixed polyline.

    Weights are frozen source-coordinate protection weights in [0,1].
    No segments between distinct paths are inferred.
    """
    vertices = np.asarray(vertices, dtype=float)
    path = np.asarray(centerline, dtype=float)
    gains = np.asarray(gains, dtype=float)
    weights = np.asarray(weights, dtype=float)
    if (vertices.ndim != 2 or vertices.shape[1] != 3 or path.ndim != 2
            or path.shape[1] != 3 or len(path) < 2 or gains.shape != (len(path),)
            or weights.shape != (len(vertices),)
            or not all(np.isfinite(a).all() for a in (vertices,path,gains,weights))
            or np.any(gains <= 0) or np.any((weights < 0) | (weights > 1))):
        raise ValueError('Finite geometry, positive path gains and bounded weights required')
    nearest = np.zeros_like(vertices)
    log_gain = np.zeros(len(vertices))
    best = np.full(len(vertices), np.inf)
    for index, (start, end) in enumerate(zip(path[:-1], path[1:])):
        axis = end - start
        length2 = axis @ axis
        if length2 <= 1e-24:
            continue
        t = np.clip((vertices-start) @ axis / length2, 0., 1.)
        projection = start + t[:,None]*axis
        distance2 = np.sum((vertices-projection)**2, axis=1)
        replace = distance2 < best
        nearest[replace] = projection[replace]
        log_gain[replace] = ((1-t)*np.log(gains[index])+t*np.log(gains[index+1]))[replace]
        best[replace] = distance2[replace]
    if not np.isfinite(best).all():
        raise ValueError('No nonzero centerline segments')
    factor = np.expm1(weights*log_gain)
    return vertices + (vertices-nearest)*factor[:,None]
