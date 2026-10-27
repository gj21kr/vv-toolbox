"""Explicit centerline-anchored scaling of measured noncircular sections."""
from copy import deepcopy

import numpy as np

from .projected_annulus import contains


def scale_profile_interval(profiles, *, start_mm, end_mm, factor,
                           protected_indices=()):
    """Scale an arclength interval with a C2 quintic bump and fixed boundaries.

    Arclength starts at the first supplied section origin, not the vessel inlet.
    Protected indices refer to section IDs. No section is silently skipped.
    """
    values = (start_mm, end_mm, factor)
    if (any(type(x) not in (int, float) or not np.isfinite(x) for x in values)
            or not isinstance(profiles, list) or len(profiles) < 3
            or factor <= 0):
        raise ValueError('Finite interval, positive factor and at least three profiles required')
    indices = [p.get('index') for p in profiles]
    if any(type(i) is not int for i in indices) or any(
            b != a + 1 for a, b in zip(indices, indices[1:])):
        raise ValueError('Consecutive section indices required')
    protected = set(protected_indices)
    if any(type(i) is not int for i in protected) or not protected <= set(indices):
        raise ValueError('Protected indices must identify supplied sections')
    # Validate the complete input before constructing any result.
    for profile in profiles:
        scale_section(profile, 1.)
    origins = np.asarray([p['origin_mm'] for p in profiles])
    distances = np.linalg.norm(np.diff(origins, axis=0), axis=1)
    arc = np.r_[0., np.cumsum(distances)]
    if np.any(distances <= 1e-12) or not 0 <= start_mm < end_mm <= arc[-1]:
        raise ValueError('Distinct stations and an interval inside the supplied path required')
    active = (arc > start_mm) & (arc < end_mm)
    if not active.any():
        raise ValueError('Interval must contain at least one interior station')
    if factor != 1 and any(active[k] and i in protected for k, i in enumerate(indices)):
        raise ValueError('Edit intersects a protected section')
    scales = np.ones(len(profiles))
    t = (arc[active] - start_mm) / (end_mm - start_mm)
    ramp = 2 * np.minimum(t, 1 - t)
    weight = ramp**3 * (10 - 15 * ramp + 6 * ramp**2)
    scales[active] += (factor - 1) * weight
    result = [deepcopy(p) if s == 1 else scale_section(p, float(s))
              for p, s in zip(profiles, scales)]
    return dict(profiles=result, scales=scales.tolist(), arclength_mm=arc.tolist(),
                operation='noncircular-interval-scale/1', factor=float(factor),
                start_mm=float(start_mm), end_mm=float(end_mm),
                protected_indices=sorted(protected),
                arclength_origin='first supplied section',
                junction_validation='NOT RUN', collision_validation='NOT RUN')


def scale_section(profile, factor):
    """Return a synthetic profile; never reinterpret area radius as tube radius.

    The centerline station and section plane stay fixed. This local operation
    does not approve neighboring surfaces, branch junctions or anatomical ranges.
    """
    if (type(factor) not in (int, float) or not np.isfinite(factor) or factor <= 0
            or profile.get('status') != 'MEASURED'):
        raise ValueError('Measured profile and positive finite scale required')
    xy = np.asarray(profile['contour_uv_mm'], dtype=float)
    origin = np.asarray(profile['origin_mm'], dtype=float)
    frame = np.asarray([profile['u'], profile['v'], profile['normal']], dtype=float)
    if (xy.ndim != 2 or xy.shape[1] != 2 or len(xy) < 4
            or not np.isfinite(xy).all() or origin.shape != (3,)
            or not np.isfinite(origin).all() or frame.shape != (3, 3)
            or not np.isfinite(frame).all()
            or not np.allclose(frame @ frame.T, np.eye(3), atol=1e-8, rtol=0)
            or np.linalg.det(frame) < 0
            or not np.array_equal(xy[0], xy[-1])
            or not contains(xy, np.zeros((1, 2)))[0]):
        raise ValueError('Closed enclosing contour and orthonormal right-handed frame required')
    expected = origin + xy @ frame[:2]
    actual = np.asarray(profile['contour_xyz_mm'], dtype=float)
    if actual.shape != expected.shape or not np.allclose(actual, expected, atol=1e-8, rtol=0):
        raise ValueError('World and local contours disagree')
    scaled = xy * factor
    a, b = scaled[:-1], scaled[1:]
    delta = b - a
    norm2 = (delta * delta).sum(axis=1)
    cross = a[:, 0] * b[:, 1] - b[:, 0] * a[:, 1]
    area = float(cross.sum() / 2)
    if not np.isfinite(scaled).all() or np.any(norm2 <= 1e-24) or abs(area) <= 1e-12:
        raise ValueError('Degenerate or unrepresentable scaled contour')
    centroid = ((a + b) * cross[:, None]).sum(axis=0) / (6 * area)
    fraction = np.clip(-(a * delta).sum(axis=1) / norm2, 0, 1)
    distance = float(np.linalg.norm(a + fraction[:, None] * delta, axis=1).min())
    result = deepcopy(profile)
    result.update(
        contour_uv_mm=scaled.tolist(),
        contour_xyz_mm=(origin + scaled @ frame[:2]).tolist(),
        area_mm2=abs(area),
        area_equivalent_radius_mm=float(np.sqrt(abs(area) / np.pi)),
        center_boundary_distance_mm=distance,
        centroid_uv_mm=centroid.tolist(),
        centroid_xyz_mm=(origin + centroid @ frame[:2]).tolist(),
        provenance='synthetic-section-scale',
        modification=dict(operation='centerline-anchored-section-scale/1', factor=float(factor)),
        junction_validation='NOT RUN', collision_validation='NOT RUN',
        anatomical_validation='NOT RUN')
    return result
