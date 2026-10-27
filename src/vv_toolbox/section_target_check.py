"""Coverage-complete target checks for measured noncircular section edits."""
import math

import numpy as np


def check_section_targets(original, requested, measured, *, absolute_scale_tolerance):
    """Compare area-radius scale on identical planes; no clinical default.

    Lists must cover exactly the same section IDs. PASS addresses only the
    caller's scale tolerance; collisions and junctions require separate checks.
    """
    if (type(absolute_scale_tolerance) not in (int, float)
            or not math.isfinite(absolute_scale_tolerance)
            or absolute_scale_tolerance < 0):
        raise ValueError('Explicit finite nonnegative absolute scale tolerance required')
    report = dict(status='UNKNOWN', complete=False, rows=[],
                  absolute_scale_tolerance=float(absolute_scale_tolerance),
                  scope='Area-equivalent radius scale on supplied section planes',
                  collision_validation='NOT RUN', junction_validation='NOT RUN')
    def keyed(profiles):
        if not isinstance(profiles, list) or not profiles:
            return None
        result = {}
        for p in profiles:
            if not isinstance(p, dict) or type(p.get('index')) is not int or p['index'] in result:
                return None
            result[p['index']] = p
        return result
    groups = [keyed(p) for p in (original, requested, measured)]
    if any(g is None for g in groups) or not (groups[0].keys() == groups[1].keys() == groups[2].keys()):
        return dict(report, reason='Missing, duplicate or mismatched section coverage')
    for ident in sorted(groups[0]):
        records = [g[ident] for g in groups]
        row = dict(index=ident, status='UNKNOWN')
        try:
            if any(p.get('status') != 'MEASURED' for p in records):
                raise ValueError('Unmeasured section')
            areas = np.array([p['area_mm2'] for p in records], dtype=float)
            origins = np.array([p['origin_mm'] for p in records], dtype=float)
            normals = np.array([p['normal'] for p in records], dtype=float)
            if (areas.shape != (3,) or not np.isfinite(areas).all() or np.any(areas <= 0)
                    or origins.shape != (3, 3) or normals.shape != (3, 3)
                    or not np.isfinite(origins).all() or not np.isfinite(normals).all()
                    or not np.allclose(origins, origins[0], atol=1e-8, rtol=0)
                    or not np.allclose(normals, normals[0], atol=1e-8, rtol=0)
                    or not np.allclose(np.linalg.norm(normals, axis=1), 1, atol=1e-8, rtol=0)):
                raise ValueError('Invalid areas or mismatched section planes')
            expected, actual = np.sqrt(areas[1:] / areas[0])
            if not np.isfinite([expected, actual]).all():
                raise ValueError('Unrepresentable scale')
            error = abs(float(actual - expected))
            row.update(status='PASS' if error <= absolute_scale_tolerance else 'FAIL',
                       requested_scale=float(expected), measured_scale=float(actual),
                       absolute_scale_error=error)
        except (KeyError, TypeError, ValueError) as error:
            row['reason'] = str(error)
        report['rows'].append(row)
    statuses = [r['status'] for r in report['rows']]
    report['complete'] = 'UNKNOWN' not in statuses
    report['status'] = 'FAIL' if 'FAIL' in statuses else 'UNKNOWN' if 'UNKNOWN' in statuses else 'PASS'
    return report
