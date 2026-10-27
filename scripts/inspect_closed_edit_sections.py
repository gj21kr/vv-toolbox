"""Measure achieved noncircular area changes on fixed centerline planes."""
import hashlib
import argparse
import io
import json
from pathlib import Path

import numpy as np
import trimesh

from vv_toolbox.case_io import load_case
from vv_toolbox.source_sections import extract_source_sections
from vv_toolbox.profile_scale import scale_profile_interval
from vv_toolbox.section_target_check import check_section_targets


def main(*, absolute_scale_tolerance=None):
    root = Path(__file__).resolve().parents[1]
    raw = (root / 'docs/evidence/closed-interval-edits.json').read_bytes()
    closed = json.loads(raw)
    edits_raw = (root / 'docs/evidence/profile-interval-edits.json').read_bytes()
    if hashlib.sha256(edits_raw).hexdigest() != closed['source_edits_sha256']:
        raise ValueError('Edit index changed')
    edits = json.loads(edits_raw)
    profile_raw = (root / 'docs/evidence/cerebral-smoothed-section-profiles-window2mm.json').read_bytes()
    if hashlib.sha256(profile_raw).hexdigest() != edits['profile_index_sha256']:
        raise ValueError('Profile index changed')
    profiles = {r['edge_id']: r for r in json.loads(profile_raw)['rows']}
    rows = []
    for entry in closed['rows']:
        ident = entry['edge_id']
        row = dict(edge_id=ident, factor=entry['factor'])
        if entry['status'] != 'CANDIDATE':
            row.update(status='NOT RUN', reason=entry['reason'])
            rows.append(row)
            continue
        binding = profiles[ident]
        payload = (root / binding['artifact']).read_bytes()
        if hashlib.sha256(payload).hexdigest() != binding['sha256']:
            raise ValueError('Profile artifact changed')
        original = json.loads(payload)
        name = ('workbench-mca-smoothing-exact-indices.json' if ident == 'FJ1692:e0'
                else f'workbench-smoothing-{ident.replace(":", "-")}-exact-indices.json')
        prior = json.loads((root / 'docs/evidence' / name).read_bytes())
        case, revision = load_case(root / prior['result_file'])
        if revision != binding['case_revision']:
            raise ValueError('Case revision changed')
        edge = next(e for e in case['edges'] if e['id'] == ident)
        probe = next(e for e in edits['rows'] if e['edge_id'] == ident and e['factor'] == entry['factor'])
        target = scale_profile_interval(original['profiles'], start_mm=probe['start_mm'],
                                       end_mm=probe['end_mm'], factor=entry['factor'])
        data = (root / entry['artifact']).read_bytes()
        if hashlib.sha256(data).hexdigest() != entry['sha256']:
            raise ValueError('Surface changed')
        mesh = trimesh.load(io.BytesIO(data), file_type='ply', process=False)
        measured = extract_source_sections(mesh, edge['centerline_mm'], tangent_half_window_mm=2.)
        if len(measured['profiles']) != len(original['profiles']):
            raise ValueError('Incomplete section coverage')
        sections = []
        for before, expected, actual, scale in zip(original['profiles'], target['profiles'],
                                                 measured['profiles'], target['scales']):
            if (before['index'] != actual['index']
                    or not np.allclose(before['normal'], actual['normal'], atol=1e-10, rtol=0)
                    or not np.allclose(before['origin_mm'], actual['origin_mm'], atol=1e-10, rtol=0)):
                raise ValueError('Section plane mismatch')
            section = dict(index=before['index'], status=actual['status'], requested_scale=scale)
            if actual['status'] == 'MEASURED':
                achieved = float(np.sqrt(actual['area_mm2'] / before['area_mm2']))
                section.update(achieved_area_radius_scale=achieved,
                               absolute_scale_error=abs(achieved - scale),
                               original_area_mm2=before['area_mm2'],
                               target_area_mm2=expected['area_mm2'], actual_area_mm2=actual['area_mm2'])
            sections.append(section)
        errors = [s['absolute_scale_error'] for s in sections if s['status'] == 'MEASURED']
        row.update(status='MEASURED' if measured['counts']['UNKNOWN'] == 0 else 'UNKNOWN',
                   surface_sha256=entry['sha256'], profile_sha256=binding['sha256'],
                   case_revision=revision, sections=sections,
                   maximum_absolute_scale_error=max(errors) if errors else None)
        if absolute_scale_tolerance is not None:
            row['target_check'] = check_section_targets(
                original['profiles'], target['profiles'], measured['profiles'],
                absolute_scale_tolerance=absolute_scale_tolerance)
        rows.append(row)
        print(json.dumps({k: row[k] for k in ('edge_id', 'factor', 'status', 'maximum_absolute_scale_error')}),
              flush=True)
    report = dict(rows=rows, source_report_sha256=hashlib.sha256(raw).hexdigest(),
                  scope='Fixed-plane area-equivalent radius scale; descriptive measurement, no acceptance threshold',
                  target_scale_acceptance='NOT RUN' if absolute_scale_tolerance is None else 'See per-candidate target_check',
                  absolute_scale_tolerance=absolute_scale_tolerance, surroundings='NOT RUN')
    output = ('closed-edit-sections.json' if absolute_scale_tolerance is None
              else f'closed-edit-section-targets-{absolute_scale_tolerance:g}.json')
    (root / 'docs/evidence' / output).write_text(
        json.dumps(report, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--absolute-scale-tolerance', type=float)
    args = parser.parse_args()
    if args.absolute_scale_tolerance is not None and (
            not np.isfinite(args.absolute_scale_tolerance) or args.absolute_scale_tolerance < 0):
        parser.error('Tolerance must be finite and nonnegative')
    main(absolute_scale_tolerance=args.absolute_scale_tolerance)
