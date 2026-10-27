"""Check exact uniform-transition candidate against the current source network."""
import hashlib
import argparse
import io
import json
from collections import Counter
from pathlib import Path
import numpy as np
from vv_toolbox.case_io import load_case
from vv_toolbox.surface_context import inspect_surface_artifact, inspect_surface_context, refine_profile_separation

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--retained-fairing', action='store_true')
    args = parser.parse_args()
    name = 'mca-tangent-transition-constant-earcut-flips-uniform'
    if args.retained_fairing:
        name = 'mca-retained-fairing'
    source = json.loads((ROOT/'docs/evidence'/f'{name}.json').read_text())
    case, revision = load_case(ROOT/'exports/mca-profile-regularization/case.snapshot.json')
    path = ROOT/'exports'/name/'surface.npz'
    raw = path.read_bytes()
    report = inspect_surface_artifact(case, path, parent_edge_id='FJ1692:e0',
                                      expected_sha256=source['artifact_sha256'])
    with np.load(io.BytesIO(raw), allow_pickle=False) as data:
        v, f = data['vertices_mm'], data['faces']
        meta = json.loads(str(data['metadata'].item()))
    edges = {edge['id']: edge for edge in case['edges']}
    refinements = []
    for row in report['results']:
        if row['status'] == 'UNKNOWN':
            edge = edges[row['edge_id']]
            if edge['centerline_mm'] is None:
                continue
            result = refine_profile_separation(v, f, edge['centerline_mm'], edge['radii_mm'],
                                               max_depth=8, max_cells=100000)
            refinements.append(dict(edge_id=edge['id'], **result))
    patch = np.asarray(meta['face_origin_labels']) == 4
    patch_report = inspect_surface_context(case, v, f[patch], parent_edge_id='FJ1692:e0')
    region_reports = {}
    for label, region_name in [(0, 'retained_parent'), (1, 'retained_sac')]:
        region_reports[region_name] = inspect_surface_context(
            case, v, f[np.asarray(meta['face_origin_labels']) == label], parent_edge_id='FJ1692:e0')
    prior_raw = (ROOT/'docs/evidence/regularized-mca-sac.json').read_bytes()
    prior = json.loads(prior_raw)['context_inspection']
    witness_ids = lambda audit: sorted(row['edge_id'] for row in audit['results']
                                       if row['status'] == 'PROFILE_INTERIOR_WITNESS')
    report.update(refinements=refinements, new_transition_only=patch_report,
                  retained_regions=region_reports,
                  prior_context_evidence_sha256=hashlib.sha256(prior_raw).hexdigest(),
                  witness_edge_set_unchanged=witness_ids(report) == witness_ids(prior),
                  input_unchanged=raw == path.read_bytes(),
                  app_applied=False, case_snapshot_revision=revision)
    filename = 'mca-retained-fairing-context.json' if args.retained_fairing else 'mca-uniform-transition-context.json'
    (ROOT/'docs/evidence'/filename).write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(aabb_separated_count=report['aabb_separated_count'],
                          result_counts=dict(Counter(r['status'] for r in report['results'])),
                          refinements=refinements, used_vertex_count=report['used_vertex_count'],
                          unused_vertex_count=report['unused_vertex_count'],
                          new_transition_only=dict(status=patch_report['status'],
                              aabb_separated_count=patch_report['aabb_separated_count'],
                              result_counts=dict(Counter(r['status'] for r in patch_report['results']))),
                          region_witnesses={key: witness_ids(value) for key, value in region_reports.items()},
                          witness_edges=[r['edge_id'] for r in report['results']
                                         if r['status']=='PROFILE_INTERIOR_WITNESS'])))


if __name__ == '__main__':
    main()
