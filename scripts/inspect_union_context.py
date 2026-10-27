"""Hash-bound before/after candidate screening against every context profile."""
import hashlib
import json
from collections import Counter
from pathlib import Path
import numpy as np
from vv_toolbox.case_io import load_case
from vv_toolbox.surface_context import inspect_surface_context
from vv_toolbox.saccular_surface import _parent_field

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    snapshot = ROOT / 'exports/atlas-case-inspection/all-arterial.snapshot.json'
    case, revision = load_case(snapshot)
    inputs = {snapshot: digest(snapshot)}
    parent = next(e for e in case['edges'] if e['id'] == 'FJ1692:e0')
    reports = {}
    for name, folder, evidence in (
        ('before', 'surface-neck-union-refined', 'surface-neck-union-refined'),
        ('after', 'union-regularization', 'union-regularization'),
    ):
        path = ROOT / f'exports/{folder}/surface.npz'
        source = json.loads((ROOT / f'docs/evidence/{evidence}.json').read_text())
        inputs[path] = digest(path)
        if inputs[path] != source['artifact_sha256']:
            raise ValueError('candidate hash mismatch')
        with np.load(path, allow_pickle=False) as data:
            vertices, faces = data['vertices_mm'], data['faces']
            metadata = json.loads(str(data['metadata'].item()))
        if metadata['case_revision'] != revision:
            raise ValueError('candidate case revision mismatch')
        report = inspect_surface_context(case, vertices, faces, parent_edge_id=parent['id'])
        for row in report['results']:
            if row.get('witness'):
                point = np.array([row['witness']['position_mm']])
                row['witness']['baseline_parent_field_mm'] = float(_parent_field(
                    point, np.array(parent['centerline_mm']), np.array(parent['radii_mm']))[0])
        report['artifact_sha256'] = inputs[path]
        report['counts'] = dict(Counter(r['status'] for r in report['results']))
        reports[name] = report
        print(json.dumps(dict(stage=name, status=report['status'], counts=report['counts'],
                              aabb_separated_count=report['aabb_separated_count'])), flush=True)
    if any(digest(path) != expected for path, expected in inputs.items()):
        raise ValueError('inspection input changed')
    result = dict(schema='vv-toolbox.union-context-inspection/1',
                  case_revision=revision, reports=reports, inputs_unchanged=True,
                  app_applied=False, clinical_validation='NOT RUN')
    (ROOT / 'docs/evidence/union-context-inspection.json').write_text(
        json.dumps(result, indent=2, allow_nan=False) + '\n')


if __name__ == '__main__':
    main()
