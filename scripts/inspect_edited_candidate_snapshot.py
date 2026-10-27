"""Replay saved real radius geometry into a case without recomputing its audit."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import numpy as np

from vv_toolbox.candidate_case import candidate_snapshot
from vv_toolbox.case_io import load_case, save_case
from vv_toolbox.case_surface import build_case_surface
from vv_toolbox.resampled_access_preview import load_resampled_access_preview


def main():
    evidence = Path('docs/evidence')
    audit_file = evidence/'access-radius-roundtrip-reuse.json'
    audit = json.loads(audit_file.read_text())
    if audit['status'] != 'PASS' or not audit['baseline_geometry_and_audit_equal']:
        raise ValueError('Completed matching radius audit required')
    candidate = load_resampled_access_preview(Path('.'))
    if candidate['summary']['surface_sha256'] != audit['parent_sha256']:
        raise ValueError('Radius parent mismatch')
    artifact = Path('exports/access-radius-edit/left-femoral-105.npz')
    with np.load(artifact, allow_pickle=False) as data:
        candidate['vertices_mm'] = data['vertices']
        if not np.array_equal(candidate['faces'], data['faces']):
            raise ValueError('Radius topology mismatch')
    candidate['summary'] = deepcopy(audit['candidate'])
    graph, _ = load_case('exports/femoral-anterior-graph/case.snapshot.json')
    document = candidate_snapshot(candidate, graph)
    output = Path('exports/edited-access-inspection/case.snapshot.json')
    if output.exists():
        raise ValueError('Refusing to overwrite inspection case')
    output.parent.mkdir(parents=True, exist_ok=True)
    save_case(output, document['case'])
    loaded, revision = load_case(output)
    vertices, faces, _ = build_case_surface(loaded, [e['id'] for e in graph['edges']], spacing_mm=1.)
    if not np.array_equal(vertices, candidate['vertices_mm']) or not np.array_equal(faces, candidate['faces']):
        raise ValueError('Edited geometry changed during reload')
    inspection = loaded['inspection']['access_candidate']
    if inspection['summary']['radius_edit'] != audit['candidate']['radius_edit']:
        raise ValueError('Edited audit changed during reload')
    if inspection['accepted_for_generation'] or inspection['summary']['radius_edit']['neighbor_contact'] != 'FAIL':
        raise ValueError('Failed candidate was upgraded')
    report = dict(status='PASS', scope='Actual saved radius geometry and existing audit snapshot roundtrip; not live download',
                  revision=revision, artifact=str(output), geometry_sha256=candidate['summary']['geometry_sha256'],
                  preserved_context_status='FAIL', accepted_for_generation=False,
                  audit_file_sha256=hashlib.sha256(audit_file.read_bytes()).hexdigest(),
                  input_surface_sha256=hashlib.sha256(artifact.read_bytes()).hexdigest(),
                  artifact_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),
                  graph_unchanged=loaded['edges'] == graph['edges'])
    (evidence/'edited-access-inspection.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
