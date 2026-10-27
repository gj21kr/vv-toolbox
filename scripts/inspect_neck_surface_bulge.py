"""Compare source-derived radius profiles with actual generated neck sections."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh

from vv_toolbox.case_io import load_case


def inspect(snapshot, surface, normal_half_window_mm=.3):
    if not np.isfinite(normal_half_window_mm) or normal_half_window_mm <= 0:
        raise ValueError('positive finite normal half window required')
    case, revision = load_case(snapshot)
    with np.load(surface, allow_pickle=False) as data:
        mesh = trimesh.Trimesh(vertices=data['vertices_mm'], faces=data['faces'], process=False)
        metadata = json.loads(str(data['metadata']))
    if metadata['case_revision'] != revision:
        raise ValueError('surface/snapshot revision mismatch')
    by_id = {e['id']: e for e in case['edges']}
    records = []
    for bridge_id in case['synthetic_route_inspection']['bridge_ids']:
        bridge = by_id[bridge_id]
        for anchor_index, anchor in enumerate(bridge['derivation']['anchors']):
            source = by_id[anchor['edge_id']]
            p, r = np.array(source['centerline_mm']), np.array(source['radii_mm'])
            if anchor['endpoint'] == 'start':
                p, r = p[::-1], r[::-1]
            bp, br = np.array(bridge['centerline_mm']), np.array(bridge['radii_mm'])
            if anchor_index == 1:
                bp, br = bp[::-1], br[::-1]
            points, radii = np.concatenate([p[:-1], bp]), np.concatenate([r[:-1], br])
            arc = np.r_[0., np.cumsum(np.linalg.norm(np.diff(points, axis=0), axis=1))]
            junction = float(arc[len(p)-1])
            stations = []
            for offset in np.arange(-15., 15.01, 1.):
                location = junction+offset
                if location < normal_half_window_mm or location > arc[-1]-normal_half_window_mm:
                    continue
                center = np.array([np.interp(location, arc, points[:, j]) for j in range(3)])
                tangent = np.array([np.interp(location+normal_half_window_mm, arc, points[:, j])-np.interp(location-normal_half_window_mm, arc, points[:, j]) for j in range(3)])
                if np.linalg.norm(tangent) <= 1e-12:
                    raise ValueError('normal window has degenerate chord')
                tangent /= np.linalg.norm(tangent)
                radius = float(np.interp(location, arc, radii))
                section = mesh.section(plane_origin=center, plane_normal=tangent)
                loops = []
                if section is not None:
                    for polygon in section.discrete:
                        if not np.allclose(polygon[0], polygon[-1], atol=1e-5):
                            continue
                        area = float(np.linalg.norm(np.cross(polygon[:-1]-center, polygon[1:]-center).sum(axis=0))/2)
                        loops.append({'centroid_distance_mm': float(np.linalg.norm(polygon[:-1].mean(axis=0)-center)),
                                      'area_mm2': area, 'equivalent_radius_mm': float(np.sqrt(area/np.pi))})
                selected = min(loops, key=lambda item: item['centroid_distance_mm']) if loops else None
                if selected is None or selected['centroid_distance_mm'] > radius:
                    raise ValueError('no unambiguous nearby section loop')
                stations.append({'offset_from_attachment_mm': float(offset), 'center_mm': center.tolist(),
                                 'normal': tangent.tolist(), 'profile_radius_mm': radius,
                                 'section': selected, 'section_loop_count': len(loops)})
            negative = [s for s in stations if s['offset_from_attachment_mm'] <= 0]
            profile = [s['profile_radius_mm'] for s in negative]
            measured = [s['section']['equivalent_radius_mm'] for s in negative]
            records.append({'bridge_id': bridge_id, 'source_edge_id': source['id'],
                'attachment': 'start' if anchor_index == 0 else 'end',
                'source_geometry_kind': source['geometry_kind'],
                'source_derivation': source.get('derivation'),
                'source_side_profile_min_max_mm': [min(profile), max(profile)],
                'source_side_surface_min_max_equivalent_radius_mm': [min(measured), max(measured)],
                'source_side_profile_total_variation_mm': float(np.abs(np.diff(profile)).sum()),
                'source_side_surface_total_variation_mm': float(np.abs(np.diff(measured)).sum()),
                'stations': stations})
    return {'schema': 'vv-toolbox.neck-surface-bulge-inspection/1', 'case_revision': revision,
        'snapshot_file_sha256': hashlib.sha256(Path(snapshot).read_bytes()).hexdigest(),
        'surface_file_sha256': hashlib.sha256(Path(surface).read_bytes()).hexdigest(),
        'spacing_mm': metadata['spacing_mm'], 'scope': '31 local cross sections per attachment, source side offsets -15..0 and bridge side 0..15 mm',
        'normal_half_window_mm': normal_half_window_mm,
        'station_count': sum(len(r['stations']) for r in records), 'attachments': records,
        'surface_smoothness_acceptance': 'UNKNOWN', 'anatomical_acceptance': 'UNKNOWN'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--snapshot', default='exports/synthetic-neck-case/case.snapshot.json')
    parser.add_argument('--surface', default='exports/synthetic-neck-case/neck-surface.npz')
    parser.add_argument('--output', default='docs/evidence/neck-surface-bulge.json')
    parser.add_argument('--figure', default='exports/synthetic-neck-case/neck-surface-radius-profiles.png')
    parser.add_argument('--normal-half-window-mm', type=float, default=.3)
    args = parser.parse_args()
    report = inspect(args.snapshot, args.surface, args.normal_half_window_mm)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), sharex=True)
    for ax, row in zip(axes.flat, report['attachments']):
        stations = row['stations']
        x = [s['offset_from_attachment_mm'] for s in stations]
        ax.plot(x, [s['profile_radius_mm'] for s in stations], label='Input radius', color='black')
        ax.plot(x, [s['section']['equivalent_radius_mm'] for s in stations], label='Mesh area-equivalent radius', color='firebrick')
        ax.axvline(0, color='orange', linestyle='--')
        ax.set_title(row['source_edge_id']+' / '+row['attachment'])
        ax.set_ylabel('Radius (mm)'); ax.set_xlabel('Source < 0 | attachment | bridge > 0 (mm)')
        ax.grid(alpha=.2); ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(args.figure, dpi=150); plt.close(fig)
    report['figure'] = {'path': args.figure, 'sha256': hashlib.sha256(Path(args.figure).read_bytes()).hexdigest()}
    Path(args.output).write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({'station_count': report['station_count'], 'attachments': [
        {k: v for k, v in row.items() if k not in ('stations', 'source_derivation')} for row in report['attachments']]}))


if __name__ == '__main__':
    main()
