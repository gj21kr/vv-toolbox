"""Source-preserving ACA candidate localization from measured surface sections."""
import hashlib
import io
import json
from pathlib import Path
import zipfile

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import trimesh

from recheck_aca_boundaries import section

ROOT = Path(__file__).resolve().parents[1]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def intersections(first, second, z):
    hits = []
    cross = lambda a, b: a[0]*b[1]-a[1]*b[0]
    for p in first:
        for q in second:
            for a, b in zip(p[:-1, :2], p[1:, :2]):
                for c, d in zip(q[:-1, :2], q[1:, :2]):
                    u, v = b-a, d-c
                    det = cross(u, v)
                    if abs(det) < 1e-12:
                        continue
                    t, s = cross(c-a, v)/det, cross(c-a, u)/det
                    if 0 < t < 1 and 0 < s < 1:
                        point = a+t*u
                        hits.append([float(point[0]), float(point[1]), float(z)])
    return hits


def projection(points, target):
    points = np.asarray(points)
    delta = np.diff(points, axis=0)
    t = np.clip(np.sum((target-points[:-1])*delta, axis=1)/np.sum(delta*delta, axis=1), 0, 1)
    closest = points[:-1]+t[:, None]*delta
    distance = np.linalg.norm(closest-target, axis=1)
    i = int(np.argmin(distance))
    arc = np.r_[0, np.cumsum(np.linalg.norm(delta, axis=1))]
    station = float(arc[i]+t[i]*(arc[i+1]-arc[i]))
    tangent = np.array([np.interp(min(arc[-1], station+1), arc, points[:, j])-
                        np.interp(max(0, station-1), arc, points[:, j]) for j in range(3)])
    tangent /= np.linalg.norm(tangent)
    return {'interval_index': i, 'fraction': float(t[i]), 'position_mm': closest[i].tolist(),
            'distance_to_surface_intersection_centroid_mm': float(distance[i]),
            'station_mm': station, 'plane_normal': tangent.tolist(),
            'at_extraction_endpoint': bool(station < 1e-8 or abs(station-arc[-1]) < 1e-8)}


def main():
    out = ROOT/'exports/aca-boundary-resolution'; out.mkdir(parents=True, exist_ok=True)
    old_raw = (ROOT/'docs/evidence/aca-boundary-review.json').read_bytes()
    follow_raw = (ROOT/'docs/evidence/aca-boundary-followup.json').read_bytes()
    old, follow = json.loads(old_raw), json.loads(follow_raw)
    if follow['previous_report_sha256'] != sha(old_raw) or follow['obj_sha256'] != old['obj_sha256']:
        raise ValueError('followup source lineage mismatch')
    source = ROOT/'reference-data/bodyparts3d'
    archive_raw = (source/'isa_BP3D_4.0_obj_99.zip').read_bytes()
    preview_raw = (source/'centerlines-preview.json').read_bytes()
    if sha(archive_raw) != old['source_archive_sha256'] or sha(preview_raw) != old['centerline_sha256']:
        raise ValueError('source changed since boundary inspection')
    edges = {e['id']: e for e in json.loads(preview_raw)['edges']}
    meshes = {}
    with zipfile.ZipFile(io.BytesIO(archive_raw)) as archive:
        for ident, expected in old['obj_sha256'].items():
            names = [n for n in archive.namelist() if Path(n).name == ident+'.obj']
            if len(names) != 1:
                raise ValueError('source OBJ not unique')
            raw = archive.read(names[0])
            if sha(raw) != expected:
                raise ValueError('source OBJ hash mismatch')
            meshes[ident] = trimesh.load(io.BytesIO(raw), file_type='obj', process=False)
    sweeps = {}
    for step in [.05, .025]:
        by_side = {'R': [], 'L': []}
        for z in np.arange(1536.5, 1539.000001, step):
            acom = section(meshes['FJ1655'], [0, 0, z], [0, 0, 1])
            for side, ident in [('R', 'FJ1654'), ('L', 'FJ1654M')]:
                aca = section(meshes[ident], [0, 0, z], [0, 0, 1])
                by_side[side].extend(intersections(aca, acom, z))
        sweeps[str(step)] = by_side
    boundaries = []
    fig, axes = plt.subplots(1, 2, figsize=(12, 6))
    for side, ident, ax in [('R', 'FJ1654', axes[0]), ('L', 'FJ1654M', axes[1])]:
        candidate_rows = []
        edge = next(e for e in edges.values() if e['part_id'] == ident)
        points = np.array(edge['points'])
        for step in [.05, .025]:
            cloud = np.array(sweeps[str(step)][side])
            if len(cloud) == 0:
                raise ValueError('no strict section intersections')
            center = cloud.mean(axis=0)
            candidate = projection(points, center)
            stations = [projection(points, p)['station_mm'] for p in cloud]
            candidate_rows.append({'slice_step_mm': step, 'intersection_count': len(cloud),
                'intersection_bounds_mm': [cloud.min(0).tolist(), cloud.max(0).tolist()],
                'intersection_centroid_mm': center.tolist(), 'candidate': candidate,
                'projected_intersection_station_range_mm': [min(stations), max(stations)]})
        cloud = np.array(sweeps['0.025'][side]); center = candidate_rows[-1]['candidate']['position_mm']
        ax.scatter(cloud[:, 1], cloud[:, 2], s=5, c='royalblue', label='Actual ACA/ACom surface crossings')
        ax.plot(points[:, 1], points[:, 2], c='firebrick', label='ACA derived centerline projection')
        ax.scatter(center[1], center[2], c='black', marker='x', s=60, label='Operational continuous projection')
        ax.set(xlim=(-117, -108), ylim=(1535.5, 1540), title=side+' A1/A2 source intersection region', xlabel='LPS Y mm', ylabel='LPS Z mm')
        ax.set_aspect('equal'); ax.grid(alpha=.2); ax.legend(fontsize=7)
        boundaries.append({'boundary_id': f'B.{side}.ACA.A1_A2', 'edge_id': edge['id'],
            'position': None, 'candidate': candidate_rows[-1]['candidate'],
            'status': 'surface_intersection_based_operational_candidate',
            'candidate_rule': 'Project arithmetic centroid of uniformly Z-sampled strict ACA/ACom contour intersections onto continuous ACA polyline; no nearest vertex selection',
            'measurements': candidate_rows,
            'resolution_candidate_shift_mm': float(np.linalg.norm(np.array(candidate_rows[0]['candidate']['position_mm'])-candidate_rows[1]['candidate']['position_mm'])),
            'exact_boundary_approved': False,
            'unresolved_reason': 'Intersection is between independent surfaces, not an open ostium. Slice-weighted centroid is an operational choice. No lumen union or anatomical plane adjudication.'})
    fig.tight_layout(); fig.savefig(out/'acom-intersection-anchors.png', dpi=160); plt.close(fig)
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    callosal = {str(x): section(meshes['FJ1742'], [x, 0, 0], [1, 0, 0]) for x in [-3., 0., 3.]}
    regions = [b for b in follow['boundaries'] if b['status'] == 'region_only']
    for region, ax in zip(regions, axes.flat):
        old_region = next(b for b in old['boundaries'] if b['boundary_id'] == region['boundary_id'])
        edge = edges[region['edge_id']]
        p = np.array(edge['points'])
        midpoint = next(c for c in region['candidates'] if c['region_fraction'] == .5)
        for x, curves in callosal.items():
            for curve in curves:
                ax.plot(curve[:, 1], curve[:, 2], linewidth=1, alpha=.6, label='Callosal sagittal X='+x)
        ax.plot(p[:, 1], p[:, 2], c='firebrick', label='Vessel centerline projection')
        candidates = region['candidates']
        cp = np.array([c['position_mm'] for c in candidates])
        ax.scatter(cp[:, 1], cp[:, 2], c=['blue', 'black', 'blue'], marker='x', s=50)
        center = np.array(midpoint['position_mm'])
        ax.set(xlim=(center[1]-18, center[1]+18), ylim=(center[2]-18, center[2]+18),
               title=region['boundary_id'], xlabel='LPS Y mm', ylabel='LPS Z mm')
        ax.set_aspect('equal'); ax.grid(alpha=.2)
        # Keep actual callosal contour coordinates for independent reinspection.
        boundaries.append({'boundary_id': region['boundary_id'], 'edge_id': region['edge_id'],
            'position': None,
            'candidate': {'interval_index': midpoint['edge_point_interval'][0],
                          'fraction': midpoint['interval_fraction'],
                          'position_mm': midpoint['position_mm'], 'plane_normal': midpoint['plane_normal']},
            'status': 'region_only_not_narrowed', 'region_bounds_mm': old_region['region_bounds_mm'],
            'region_arclength_mm': region['region_arclength_mm'],
            'operational_plane_candidate': {k: midpoint[k] for k in ('edge_point_interval', 'interval_fraction', 'position_mm', 'plane_normal', 'station_from_edge_start_mm')},
            'endpoint_candidates': [{k: c[k] for k in ('edge_point_interval', 'interval_fraction', 'position_mm', 'plane_normal')} for c in (candidates[0], candidates[-1])],
            'callosal_landmark_part': 'FJ1742', 'callosal_sagittal_section_x_mm': [-3, 0, 3],
            'exact_boundary_approved': False,
            'unresolved_reason': 'Actual sagittal callosal contours retain a smooth rostrum/genu or superior-genu/body transition without a unique surface seam or annotated landmark vertex. Narrowing requires a declared anatomical/operator convention; nearest contour vertex or curvature maximum would introduce a new unvalidated rule.',
            'uncertainty': 'Prior reviewed region extent, not statistical confidence or calibrated measurement error'})
    fig.suptitle('Actual callosal sections and vessel projections; blue=reviewed region ends, black=operational midpoint')
    fig.tight_layout(); fig.savefig(out/'callosal-transition-regions.png', dpi=160); plt.close(fig)
    report = {'schema': 'vv-toolbox.aca-boundary-resolution/1',
        'source_archive_sha256': sha(archive_raw), 'centerline_sha256': sha(preview_raw),
        'prior_review_sha256': sha(old_raw), 'prior_followup_sha256': sha(follow_raw),
        'obj_sha256': old['obj_sha256'], 'boundaries': boundaries,
        'surface_intersection_samples': sweeps,
        'callosal_sections': {x: [p.tolist() for p in curves] for x, curves in callosal.items()},
        'summary': {'groups_inspected': len(boundaries), 'surface_based_A1_A2_candidates': 2,
                    'regions_not_uniquely_narrowed': 4, 'exact_boundaries_approved': 0},
        'source_geometry_changed': False, 'app_labels_changed': False,
        'figures': [{'path': str(p.relative_to(ROOT)), 'sha256': sha(p.read_bytes())} for p in sorted(out.glob('*.png'))]}
    report['input_bytes_unchanged'] = (
        (source/'centerlines-preview.json').read_bytes() == preview_raw and
        sha((source/'isa_BP3D_4.0_obj_99.zip').read_bytes()) == sha(archive_raw) and
        (ROOT/'docs/evidence/aca-boundary-review.json').read_bytes() == old_raw and
        (ROOT/'docs/evidence/aca-boundary-followup.json').read_bytes() == follow_raw)
    if not report['input_bytes_unchanged']:
        raise ValueError('inputs changed during inspection')
    (ROOT/'docs/evidence/aca-boundary-resolution.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({'summary': report['summary'], 'A1_A2': boundaries[:2]}, ensure_ascii=False))


if __name__ == '__main__':
    main()
