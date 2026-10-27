"""Discrete path measurements; no resampling or clinical classification."""
import numpy as np


def polyline_metrics(points):
    points = np.asarray(points, float)
    if points.ndim != 2 or points.shape[1] != 3 or len(points) < 2 or not np.isfinite(points).all():
        raise ValueError('Finite Nx3 path required')
    segments = np.diff(points, axis=0)
    lengths = np.linalg.norm(segments, axis=1)
    if np.any(lengths <= 1e-12):
        raise ValueError('Distinct consecutive path stations required')
    length = float(lengths.sum())
    chord = float(np.linalg.norm(points[-1]-points[0]))
    directions = segments/lengths[:, None]
    angles = np.arccos(np.clip(np.sum(directions[1:]*directions[:-1], axis=1), -1, 1))
    return dict(length_mm=length, chord_mm=chord,
        length_over_chord=length/chord if chord > 1e-12 else None,
        ratio_status='PASS' if chord > 1e-12 else 'UNDEFINED_COINCIDENT_ENDPOINTS',
        maximum_turn_deg=float(np.rad2deg(angles.max())) if len(angles) else 0.,
        total_turn_deg=float(np.rad2deg(angles.sum())),
        definition='Discrete source polyline; length/chord ratio and vertex turning angles; sampling-dependent, not differential torsion')
