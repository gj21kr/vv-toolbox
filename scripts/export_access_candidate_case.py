"""Register exact candidate geometry with its graph, without upgrading evidence."""
from copy import deepcopy
import json
from pathlib import Path

import numpy as np

from vv_toolbox.case_io import case_digest, load_case, save_case
from vv_toolbox.case_source_surfaces import attach_surfaces
from vv_toolbox.case_surface import build_case_surface
from vv_toolbox.resampled_access_preview import load_resampled_access_preview


def main():
    evidence = Path('docs/evidence')
    candidate = load_resampled_access_preview(Path('.'))
    record = json.loads((evidence/'access-sample-graph.json').read_text())
    graph, revision = load_case(record['graph_file'])
    summary = candidate['summary']
    if revision != summary['access_graph']['revision'] or graph['edges'] != candidate['edges']:
        raise ValueError('Complete candidate graph identity mismatch')
    if graph['frame']['axes'] != 'LPS' or graph['frame']['units'] != 'mm':
        raise ValueError('Candidate requires LPS millimetres')
    result = deepcopy(graph)
    result['case_id'] = 'access-candidate-' + summary['surface_sha256'][:16]
    result['model_kind'] = 'synthetic'
    result['generation'] = dict(seed=0, generator_version='registered-access-candidate/1',
        config=dict(parent_graph_revision=revision, parent_generation=graph['generation'],
                    source_case_revision=summary['revision'], surface_sha256=summary['surface_sha256']))
    result['candidate_surface_reference'] = dict(sha256=summary['surface_sha256'],
        role='registered inspection candidate; not accepted anatomy')
    result.setdefault('inspection', {})['access_candidate'] = dict(
        geometry=deepcopy(summary['access_union']), graph=deepcopy(summary['access_graph']),
        anatomy=summary['anatomy'], smoothness=summary['smoothness'],
        anatomical_segment_coverage='UNKNOWN', radius_surface_consistency='NOT RUN',
        accepted_for_generation=False)
    ids = [edge['id'] for edge in graph['edges']]
    result = attach_surfaces(result, [dict(part_id='access-union', edge_ids=ids,
        frame_id=graph['frame']['id'], provenance='estimated',
        source_ids=[s['id'] for s in graph['sources']],
        vertices_mm=candidate['vertices_mm'].tolist(), faces=candidate['faces'].tolist(),
        face_lineage=deepcopy(candidate['face_lineage']),
        lineage_scope='Union input face ownership; not reviewed anatomical segment labels')])
    if result['edges'] != graph['edges'] or result['nodes'] != graph['nodes']:
        raise ValueError('Registration changed graph geometry or evidence')
    folder = Path('exports/access-candidate-case')
    folder.mkdir(parents=True, exist_ok=True)
    target = folder/'case.snapshot.json'
    derived = case_digest(result)
    if target.exists():
        if load_case(target)[1] != derived:
            raise ValueError('Existing registered case differs; refusing overwrite')
    else:
        save_case(target, result)
    restored, saved_revision = load_case(target)
    vertices, faces, surface = build_case_surface(restored, ids, spacing_mm=1.)
    if (saved_revision != derived or restored != result
            or not np.array_equal(vertices, candidate['vertices_mm'])
            or not np.array_equal(faces, candidate['faces'])):
        raise ValueError('Registered candidate export changed geometry or metadata')
    report = dict(status='PASS', scope='Case save/load and exact surface export only',
        case_file=str(target), case_revision=derived, parent_graph_revision=revision,
        surface_sha256=summary['surface_sha256'], vertices=len(vertices), faces=len(faces),
        edges=len(ids), nodes=len(graph['nodes']), graph_evidence_preserved=True,
        face_lineage_preserved=restored['surface_parts'][0]['face_lineage']==candidate['face_lineage'],
        surface_export_method=surface['method'], accepted_for_generation=False,
        anatomy='UNKNOWN', context_status=summary['access_union']['context_status'],
        segment_masks='NOT RUN', live_scene_changed=False)
    (evidence/'access-candidate-case.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report), flush=True)


if __name__=='__main__':
    main()
