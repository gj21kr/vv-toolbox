"""All-arterial context checks for the six fixed-collar radius candidates."""
import hashlib
import argparse
import json
from pathlib import Path

import numpy as np
import trimesh

from vv_toolbox.atlas import load_atlas
from vv_toolbox.disjoint_containment import _SurfaceValidationCache
from vv_toolbox.radius_context import inspect_radius_context


def read_mesh(root, item):
    path=root/item['artifact']
    if hashlib.sha256(path.read_bytes()).hexdigest()!=item['sha256']:
        raise ValueError('Candidate artifact identity mismatch')
    with np.load(path,allow_pickle=False) as data:
        return trimesh.Trimesh(data['vertices_mm'],data['faces'],process=False)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--external-contacts',action='store_true')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    evidence=root/'docs/evidence'
    stem='frontobasal-external-protected-radius' if args.external_contacts else 'frontobasal-protected-radius'
    context_stem='frontobasal-external-radius-context' if args.external_contacts else 'frontobasal-radius-context'
    candidate_path=evidence/f'{stem}.json'
    candidates=json.loads(candidate_path.read_text())
    parent=json.loads((evidence/'frontobasal-junction-partition.json').read_text())
    if candidates['parent_artifact_sha256']!=parent['sha256']:
        raise ValueError('Baseline partition mismatch')
    expected={(f'FJ1690:e{i}',scale) for i in range(3) for scale in (.9,1.1)}
    rows=candidates['rows']
    if (len(rows)!=6 or {(r['edge_id'],r['scale']) for r in rows}!=expected
            or any(r['status']!='CANDIDATE' for r in rows)):
        raise ValueError('All six fixed candidates are required')
    before=read_mesh(root,parent)
    atlas=load_atlas()
    if atlas.metadata['sha256']!=parent['atlas_archive_sha256']:
        raise ValueError('Atlas identity mismatch')
    neighbors={p['id']:trimesh.Trimesh(p['vertices'],p['faces'],process=False)
               for p in atlas.meshes if p['layer']=='arterial' and p['id']!='FJ1690'}
    if len(neighbors)!=517:
        raise ValueError('Expected complete 517-part arterial context')
    output=evidence/context_stem
    output.mkdir(exist_ok=True)
    report_path=evidence/f'{context_stem}.json'
    report=dict(schema='vv-toolbox.frontobasal-radius-context/1',status='RUNNING',
        parent_artifact_sha256=parent['sha256'],atlas_archive_sha256=atlas.metadata['sha256'],
        input_report_sha256=hashlib.sha256(candidate_path.read_bytes()).hexdigest(),
        expected_candidates=6,neighbor_count=len(neighbors),rows=[],accepted_for_generation=False,
        scope='Every radius candidate versus all 517 other arterial parts; original contacts retained in reports.',
        venous_context='NOT RUN',anatomical_validation='NOT RUN')
    def save():
        report_path.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    save()
    cache=_SurfaceValidationCache()
    for index,row in enumerate(rows):
        candidate=read_mesh(root,row)
        def progress(value):
            if value['completed']%100==0:
                print(json.dumps(dict(candidate=index,completed=value['completed'],total=value['total'])),flush=True)
        checked=inspect_radius_context(before,candidate,neighbors,progress=progress,_validation_cache=cache)
        path=output/f'candidate-{index}.json'
        detail=dict(schema='vv-toolbox.frontobasal-radius-context-detail/1',
            artifact_sha256=row['sha256'],baseline_sha256=parent['sha256'],
            edge_id=row['edge_id'],scale=row['scale'],context=checked,accepted_for_generation=False)
        path.write_text(json.dumps(detail,indent=2,allow_nan=False)+'\n')
        summary=dict(edge_id=row['edge_id'],scale=row['scale'],status=checked['status'],
            decision_reason=checked['decision_reason'],
            new_or_extended_contacts=checked['new_or_extended_contacts'],
            remaining_contacts=checked['remaining_contacts'],unknown=checked['unknown'],
            report=str(path.relative_to(root)),sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        report['rows'].append(summary)
        save()
        print(json.dumps(summary),flush=True)
    report['status']='FAIL' if any(r['status']=='FAIL' for r in report['rows']) else (
        'UNKNOWN' if any(r['status']=='UNKNOWN' for r in report['rows']) else 'PASS')
    save()


if __name__=='__main__':main()
