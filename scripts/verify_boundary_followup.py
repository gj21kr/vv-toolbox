"""Verify provenance and complete coverage of the twelve boundary review groups.

This validates evidence bookkeeping, not anatomical correctness. Run in Docker.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check():
    source = ROOT / 'reference-data/bodyparts3d'
    archive = source / 'isa_BP3D_4.0_obj_99.zip'
    archive_sha = sha(archive)
    manifest = json.loads((source / 'acquisition.json').read_text())
    if archive_sha != manifest['files'][archive.name]['sha256']:
        raise ValueError('Source archive differs from acquisition manifest')
    centerline_sha = sha(source / 'centerlines-preview.json')
    expected = {
        f'B.{side}.{artery}.{boundary}'
        for side in ('L', 'R')
        for artery, boundaries in (
            ('ACA', ('A1_A2', 'A2_A3', 'A3_A4')),
            ('MCA', ('M1_M2', 'M2_M3', 'M3_M4')),
        )
        for boundary in boundaries
    }
    groups, reports, figures = [], [], []
    for artery in ('aca', 'mca'):
        path = ROOT / f'docs/evidence/{artery}-boundary-followup.json'
        report = json.loads(path.read_text())
        if report['source_archive_sha256'] != archive_sha:
            raise ValueError(f'{artery}: stale archive fingerprint')
        recorded = report.get('centerline_sha256', report.get('centerline_preview_sha256'))
        if recorded != centerline_sha:
            raise ValueError(f'{artery}: stale centerline fingerprint')
        rows = report.get('boundaries', report.get('groups'))
        if not isinstance(rows, list) or len(rows) != 6:
            raise ValueError(f'{artery}: expected six boundary groups')
        groups.extend(row['boundary_id'] for row in rows)
        for figure in report['figures']:
            target = (ROOT / figure['path']).resolve()
            if not target.is_relative_to(ROOT.resolve()):
                raise ValueError('Figure path escapes repository')
            if sha(target) != figure['sha256']:
                raise ValueError(f'Figure fingerprint mismatch: {figure["path"]}')
            figures.append(figure['path'])
        reports.append({'path': str(path.relative_to(ROOT)), 'sha256': sha(path)})
    if len(groups) != len(set(groups)) or set(groups) != expected:
        raise ValueError('Missing, duplicate, or unexpected boundary group')
    if not figures:
        raise ValueError('No review figures recorded')
    result = {
        'schema': 'vv-toolbox.boundary-followup-verification/1',
        'evidence_integrity': 'PASS',
        'boundary_group_count': len(groups),
        'boundary_ids': sorted(groups),
        'source_archive_sha256': archive_sha,
        'centerline_sha256': centerline_sha,
        'reports': reports,
        'verified_figure_count': len(figures),
        'anatomical_correctness': 'NOT ASSESSED BY THIS SCRIPT',
        'limitation': 'Coverage and hashes do not validate landmarks or lumen connectivity.',
    }
    output = ROOT / 'docs/evidence/boundary-followup-verification.json'
    output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    check()
