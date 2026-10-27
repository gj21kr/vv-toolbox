"""Bind the rejected loft's contact intervals to source graph endpoints."""
import hashlib
import json
from pathlib import Path

import numpy as np

from vv_toolbox.case_io import load_case


def main():
    root = Path(__file__).resolve().parents[1]
    evidence = root / 'docs/evidence'
    sections_path = evidence / 'frontobasal-endpoint-sections.json'
    loft_path = evidence / 'frontobasal-profile-loft.json'
    sections = json.loads(sections_path.read_text())
    loft = json.loads(loft_path.read_text())
    parent = json.loads((evidence / 'frontobasal-centering.json').read_text())
    if not (sections['parent_artifact_sha256'] == parent['sha256'] == loft['parent_path_sha256']):
        raise ValueError('Path identity mismatch')
    for report in (parent, loft):
        if hashlib.sha256((root / report['artifact']).read_bytes()).hexdigest() != report['sha256']:
            raise ValueError('Artifact changed')
    case, revision = load_case(root / 'exports/atlas-case-inspection/all-arterial.snapshot.json')
    baseline = json.loads((evidence / 'aca-branch-paths.json').read_text())
    if revision != baseline['source_case_revision'] or revision != parent['source_case_revision']:
        raise ValueError('Source graph changed')
    edge = next(e for e in case['edges'] if e['id'] == 'FJ1690:e0')
    with np.load(root / parent['artifact'], allow_pickle=False) as data:
        points = data['candidate_points_mm']
    endpoints = []
    for side, index in [('start', 0), ('end', -1)]:
        node = edge[side]
        incident = [e for e in case['edges'] if node in (e['start'], e['end'])]
        endpoints.append(dict(side=side, node_id=node, degree=len(incident),
            incident_edges=[dict(edge_id=e['id'], source_part_id=e['source_part_id'],
                endpoint_sides=[s for s in ('start', 'end') if e[s] == node]) for e in incident],
            displacement_from_source_mm=float(np.linalg.norm(points[index] - np.asarray(edge['centerline_mm'][index])))))
    profiles = sections['sections']['profiles']
    transitions = []
    for a, b in zip(profiles, profiles[1:]):
        transitions.append(dict(from_index=a['index'], to_index=b['index'],
            from_area_mm2=a['area_mm2'], to_area_mm2=b['area_mm2'],
            area_ratio=b['area_mm2'] / a['area_mm2'],
            origin_spacing_mm=float(np.linalg.norm(np.asarray(b['origin_mm'])-a['origin_mm'])),
            from_contour_count=a['contour_count'], to_contour_count=b['contour_count']))
    with np.load(root / loft['artifact'], allow_pickle=False) as data:
        faces = data['faces']
    samples = loft['loft']['samples_per_profile']
    groups = {}
    for pair in loft['self_contact']['contact_pairs']:
        spans = []
        for face_id in pair:
            stations = faces[face_id] // samples
            spans.append([int(stations.min()), int(stations.max())])
        key = json.dumps(spans)
        groups[key] = groups.get(key, 0) + 1
    result = dict(schema='vv-toolbox.frontobasal-junction-transition/1',
        source_case_revision=revision, path_sha256=parent['sha256'], loft_sha256=loft['sha256'],
        input_reports_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (sections_path, loft_path)},
        endpoints=endpoints, transitions=transitions,
        contact_spans=[dict(profile_spans=json.loads(key), pair_count=count) for key,count in groups.items()],
        status='DIAGNOSTIC', accepted_for_generation=False,
        scope='Source extraction graph degree and measured contour transitions; no anatomical junction acceptance.',
        next_geometry_requirement='Preserve the shared junction and all incident branches; a single open-cylinder loft is not a junction reconstruction.')
    (evidence / 'frontobasal-junction-transition.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps(dict(endpoints=endpoints, last_transition=transitions[-1], contact_spans=result['contact_spans'])), flush=True)


if __name__ == '__main__':
    main()
