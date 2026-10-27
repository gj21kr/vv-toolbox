"""Paired actual lumen measurements; requested scale is not a measured radius."""
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh

from vv_toolbox.case_io import load_case
from vv_toolbox.source_sections import extract_source_sections


def main():
    root = Path('docs/evidence')
    read = lambda name: json.loads((root / name).read_text())
    edit = read('access-radius-edit.json')
    parent = read('resampled-access-protected.json')
    case, revision = load_case(read('atlas-neck-volume-case.json')['derived_case_file'])
    if revision != edit['source_case_revision'] or edit['parent_surface_sha256'] != parent['output_sha256']:
        raise ValueError('Measurement source mismatch')
    edge = next(e for e in case['edges'] if e['id'] == edit['source_edge'])
    source = np.asarray(edge['centerline_mm'])
    arc = np.r_[0., np.cumsum(np.linalg.norm(np.diff(source, axis=0), axis=1))]
    stations = np.linspace(0, arc[-1], 33)
    points = np.column_stack([np.interp(stations, arc, source[:, i]) for i in range(3)])
    report = dict(status='RUNNING', source=edit['source'], source_case_revision=revision,
                  before_sha256=parent['output_sha256'], after_sha256=edit['output_sha256'],
                  requested_scale=edit['parameters']['scale'], station_count=33,
                  expected_interior_sections=31, endpoint_sections='NOT RUN',
                  scope='31 paired chord-normal sections; not continuous whole-vessel bounds',
                  anatomical_validation='NOT RUN', live_scene_changed=False, rows=[])
    target = root / 'access-radius-sections.json'

    def save():
        temp = target.with_suffix('.json.tmp')
        temp.write_text(json.dumps(report, indent=2) + '\n')
        temp.replace(target)

    save()
    profiles = []
    for record in (parent, edit):
        path = Path(record['artifact'])
        if hashlib.sha256(path.read_bytes()).hexdigest() != record['output_sha256']:
            raise ValueError('Measurement surface mismatch')
        with np.load(path, allow_pickle=False) as data:
            mesh = trimesh.Trimesh(data['vertices'], data['faces'], process=False)
        profiles.append(extract_source_sections(mesh, points)['profiles'])
    if any(len(p) != 31 for p in profiles):
        raise ValueError('Incomplete paired section coverage')
    for before, after in zip(*profiles):
        index = before['index']
        if index != after['index'] or before['origin_mm'] != after['origin_mm']:
            raise ValueError('Section planes differ')
        row = dict(index=index, arclength_mm=float(stations[index]), before=before, after=after,
                   status='MEASURED' if before['status'] == after['status'] == 'MEASURED' else 'UNKNOWN')
        if row['status'] == 'MEASURED':
            row['area_ratio'] = after['area_mm2'] / before['area_mm2']
            row['equivalent_radius_ratio'] = after['area_equivalent_radius_mm'] / before['area_equivalent_radius_mm']
        report['rows'].append(row)
    measured = [r for r in report['rows'] if r['status'] == 'MEASURED']
    report.update(status='MEASURED' if len(measured) == 31 else 'UNKNOWN', measured=len(measured),
                  equivalent_radius_ratio_range=([min(r['equivalent_radius_ratio'] for r in measured),
                                                   max(r['equivalent_radius_ratio'] for r in measured)] if measured else None))
    save()
    print(json.dumps({k: report[k] for k in ('status', 'measured', 'equivalent_radius_ratio_range')}), flush=True)


if __name__ == '__main__':
    main()
