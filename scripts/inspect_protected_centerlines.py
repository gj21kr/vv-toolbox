"""Bind frozen centerlines to serialized protected surfaces and audit every interval."""
import hashlib
import argparse
import io
import json
from pathlib import Path

import trimesh

from vv_toolbox.case_io import load_case
from vv_toolbox.centerline_containment import inspect_centerline_containment
from vv_toolbox.protected_preview import load_protected_preview
from vv_toolbox.radius_sections import inspect_radius_sections


def main(*, radius_sections=False):
    root = Path(__file__).resolve().parents[1]
    # Reuse the app's artifact, protected-coordinate and full scene coverage checks.
    load_protected_preview(root)
    fit_raw = (root / 'docs/evidence/protected-cerebral-fit.json').read_bytes()
    fit = json.loads(fit_raw)
    previous_raw = (root / 'docs/evidence/cerebral-interval-containment.json').read_bytes()
    previous = json.loads(previous_raw)
    prior_rows = {row['edge_id']: row for row in previous['rows']}
    source_path = root / 'exports/atlas-case-inspection/all-arterial.snapshot.json'
    source, revision = load_case(source_path)
    source_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()
    if source_hash != previous['source_file_sha256']:
        raise ValueError('Frozen source changed')
    rows = []
    for entry in fit['rows']:
        ident = entry['edge_id']
        prior = prior_rows[ident]
        name = ('workbench-mca-smoothing-exact-indices.json' if ident == 'FJ1692:e0'
                else f'workbench-smoothing-{ident.replace(":", "-")}-exact-indices.json')
        raw = (root / 'docs/evidence' / name).read_bytes()
        smoothing = json.loads(raw)
        modified, result_revision = load_case(root / smoothing['result_file'])
        if (hashlib.sha256(raw).hexdigest() != prior['prior_report_sha256']
                or revision != prior['source_revision']
                or result_revision != prior['result_revision']
                or fit['atlas_archive_sha256'] != smoothing['atlas_archive_sha256']):
            raise ValueError('Frozen centerline identity mismatch')
        data = (root / entry['artifact']).read_bytes()
        if hashlib.sha256(data).hexdigest() != entry['sha256']:
            raise ValueError('Protected surface changed')
        mesh = trimesh.load(io.BytesIO(data), file_type='ply', process=False)
        row = dict(edge_id=ident, surface_sha256=entry['sha256'],
                   source_revision=revision, result_revision=result_revision)
        for label, case in [('source', source), ('smoothed', modified)]:
            edge = next(e for e in case['edges'] if e['id'] == ident)
            if radius_sections:
                row[label] = inspect_radius_sections(
                    mesh, edge['centerline_mm'], edge['radii_mm'],
                    samples=64, tolerance_mm=1e-6)
                for section in row[label]['rows']:
                    witnesses = section.pop('outside_witnesses', [])
                    section['maximum_outside_distance_mm'] = max(
                        (w['distance_to_surface_mm'] for w in witnesses), default=None)
                    section['first_outside_witness'] = witnesses[0] if witnesses else None
                row[label]['witness_storage'] = 'First witness and maximum distance per section; all sample counts retained'
            else:
                row[label] = inspect_centerline_containment(
                    mesh, edge['centerline_mm'], tolerance_mm=1e-6,
                    max_depth=16, max_cells=100000)
                row[label]['input_intervals'] = len(edge['centerline_mm']) - 1
        rows.append(row)
        print(json.dumps(dict(edge_id=ident, source=row['source']['status'],
                              smoothed=row['smoothed']['status'])), flush=True)
    states = [row[label]['status'] for row in rows for label in ('source', 'smoothed')]
    report = dict(
        status='FAIL' if 'FAIL' in states else 'UNKNOWN' if 'UNKNOWN' in states else 'PASS',
        scope=('64 circular samples per non-endpoint normal section in protected surfaces'
               if radius_sections else 'Whole-interval centerline containment in serialized protected surfaces'),
        candidate_report_sha256=hashlib.sha256(fit_raw).hexdigest(),
        previous_containment_report_sha256=hashlib.sha256(previous_raw).hexdigest(),
        source_file_sha256=source_hash, rows=rows,
        continuous_tube_wall='NOT RUN', anatomical_validity='NOT RUN')
    output = 'protected-radius-sections.json' if radius_sections else 'protected-centerlines.json'
    (root / 'docs/evidence' / output).write_text(
        json.dumps(report, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--radius-sections', action='store_true')
    main(radius_sections=parser.parse_args().radius_sections)
