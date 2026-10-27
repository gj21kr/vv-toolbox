"""Separate, explicitly parameterized tangent-matched centerline candidates."""
import math

import numpy as np


def build_collar_link(incoming, outgoing, *, collar_mm, samples=129):
    """Retreat/advance along oriented paths and join their local tangents.

    Input paths are unchanged. The output is a sampled cubic, not an accepted
    anatomical junction; surface containment must be checked independently.
    """
    if type(collar_mm) not in (int, float) or not math.isfinite(collar_mm) or collar_mm <= 0:
        raise ValueError("Positive finite collar distance required")
    if type(samples) is not int or not 3 <= samples <= 4097:
        raise ValueError("Bounded sample count required")

    def anchor(raw, incoming_side):
        points = np.asarray(raw, dtype=float)
        if points.ndim != 2 or points.shape[1] != 3 or len(points) < 2 or not np.isfinite(points).all():
            raise ValueError("Finite oriented paths required")
        delta = np.diff(points, axis=0)
        lengths = np.linalg.norm(delta, axis=1)
        if np.any(lengths <= 1e-12):
            raise ValueError("Nondegenerate source intervals required")
        stations = np.r_[0., np.cumsum(lengths)]
        if collar_mm >= stations[-1]:
            raise ValueError("Collar exceeds available source path")
        station = stations[-1]-collar_mm if incoming_side else collar_mm
        index = int(np.clip(np.searchsorted(stations, station, side="left" if incoming_side else "right")-1,
                            0, len(delta)-1))
        fraction = float((station-stations[index])/lengths[index])
        point = points[index]+fraction*delta[index]
        tangent = delta[index]/lengths[index]
        return point, tangent, dict(interval_index=index, fraction=fraction,
                                    station_mm=float(station), path_length_mm=float(stations[-1]))

    a, ta, binding_a = anchor(incoming, True)
    b, tb, binding_b = anchor(outgoing, False)
    chord = float(np.linalg.norm(b-a))
    if chord <= 1e-12:
        raise ValueError("Distinct collar anchors required")
    da, db = chord*ta, chord*tb
    t = np.linspace(0., 1., samples)[:, None]
    points = (2*t**3-3*t**2+1)*a + (t**3-2*t**2+t)*da + (-2*t**3+3*t**2)*b + (t**3-t**2)*db
    points[0], points[-1] = a, b
    delta = np.diff(points, axis=0)
    if np.any(np.linalg.norm(delta, axis=1) <= 1e-12):
        raise ValueError("Degenerate sampled link")

    def angle(x, y):
        return float(np.degrees(np.arccos(np.clip(np.dot(x, y)/(np.linalg.norm(x)*np.linalg.norm(y)), -1., 1.))))

    return dict(points_mm=points, controls_mm=np.stack([a, a+da/3, b-db/3, b]),
                report=dict(method="fixed-collar-hermite/1", collar_mm=collar_mm, samples=samples,
                    derivative_length_mm=chord, incoming_anchor=binding_a, outgoing_anchor=binding_b,
                    analytic_endpoint_tangent_alignment="BY CONSTRUCTION",
                    sampled_start_angle_deg=angle(ta, delta[0]), sampled_end_angle_deg=angle(delta[-1], tb),
                    source_modified=False, surface_containment="NOT RUN",
                    radius_envelope="NOT RUN", self_contact="NOT RUN", anatomical_validation="NOT RUN"))


def build_radius_collar(incoming, outgoing, incoming_radii, outgoing_radii, *,
                        collar_mm, samples=129):
    """Return retained paths and a radius-continuous candidate, without graph edits."""
    result = build_collar_link(incoming, outgoing, collar_mm=collar_mm, samples=samples)
    fragments, anchor_radii = [], []
    for side, raw_points, raw_radii in (
        ("incoming", incoming, incoming_radii), ("outgoing", outgoing, outgoing_radii)
    ):
        points = np.asarray(raw_points, dtype=float)
        radii = np.asarray(raw_radii, dtype=float)
        if radii.shape != (len(points),) or not np.isfinite(radii).all() or np.any(radii <= 0):
            raise ValueError("Positive finite radius at each source point required")
        binding = result["report"][side + "_anchor"]
        index, fraction = binding["interval_index"], binding["fraction"]
        radius = float((1-fraction)*radii[index]+fraction*radii[index+1])
        anchor_radii.append(radius)
        point = result["points_mm"][0 if side == "incoming" else -1]
        if side == "incoming":
            kept_points = np.vstack([points[:index+1], point])
            kept_radii = np.r_[radii[:index+1], radius]
        else:
            kept_points = np.vstack([point, points[index+1:]])
            kept_radii = np.r_[radius, radii[index+1:]]
        fragments.append(dict(points_mm=kept_points, radii_mm=kept_radii))
    # Linear radius along sampled arc length: no unrequested radius reduction.
    stations = np.r_[0., np.cumsum(np.linalg.norm(np.diff(result["points_mm"], axis=0), axis=1))]
    result["radii_mm"] = np.interp(stations, [0., stations[-1]], anchor_radii)
    result["retained_incoming"], result["retained_outgoing"] = fragments
    result["report"].update(radius_method="linear-sampled-arclength/1",
        endpoint_radii_mm=anchor_radii, radius_slope_continuity="NOT ENFORCED",
        branch_reattachment="NOT RUN")
    return result
