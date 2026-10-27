"""Inspect a registered edit against the full frozen Atlas context in Docker."""
import argparse
import json
from pathlib import Path
import time

import trimesh

from vv_toolbox.atlas import load_atlas
from vv_toolbox.atlas_neck import build_neck_repairs
from vv_toolbox.case_io import load_case,save_case
from vv_toolbox.registered_context import inspect_registered_context,case_with_context


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--case',required=True)
    parser.add_argument('--report',required=True)
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    target=Path(args.report);output=Path(args.output)
    if target.exists() or output.exists():
        raise ValueError('Refusing to overwrite inspection evidence or case')
    root=Path(__file__).resolve().parents[1]
    case,revision=load_case(args.case)
    parent,parent_revision=load_case(root/'exports/candidate-case-download/case.snapshot.json')
    baseline=json.loads((root/'docs/evidence/resampled-access-context.json').read_text())
    if set(parent['surface_parts'][0]['face_lineage']['source_names'])!=set(baseline['excluded_union_sources']):
        raise ValueError('Frozen context exclusions do not match parent union')
    atlas=load_atlas();neck,_=build_neck_repairs(atlas)
    neighbors={p['id']:trimesh.Trimesh(p['vertices'],p['faces'],process=False)
        for p in [*atlas.meshes,*neck] if p['id'] not in baseline['excluded_union_sources']
        and p['layer'] in ('arterial','systemic_venous','hepatic_portal')}
    report=dict(status='RUNNING',case_revision=revision,parent_case_revision=parent_revision,
                completed=0,neighbor_count=baseline['neighbor_count'],rows=[])
    started=time.perf_counter()
    target.parent.mkdir(parents=True,exist_ok=True)
    def save():
        report['elapsed_seconds']=time.perf_counter()-started
        temporary=target.with_suffix('.json.tmp')
        temporary.write_text(json.dumps(report,indent=2)+'\n');temporary.replace(target)
    def progress(event):
        report['rows'].append(event['row']);report['completed']=event['completed']
        if event['completed']%10==0 or event['completed']==event['total']:save()
        if event['completed']%100==0:print(json.dumps(dict(completed=event['completed'],total=event['total'])),flush=True)
    save()
    try:
        measured=inspect_registered_context(case,parent,neighbors,
            expected_context_sha256=baseline['context_sha256'],
            expected_neighbor_ids=[r['neighbor_id'] for r in baseline['rows']],progress=progress)
        report.update(measured)
        result=case_with_context(case,measured)
        output.parent.mkdir(parents=True,exist_ok=True)
        report['saved_case_revision']=save_case(output,result)
        report['saved_case']=str(output)
    except Exception as error:
        report.update(status='ERROR',error=str(error));raise
    finally:save()
    print(json.dumps({k:report[k] for k in ('status','completed','neighbor_count','saved_case_revision','elapsed_seconds')}),flush=True)


if __name__=='__main__':main()
