"""Bounded derived path correction with graph-shared endpoint protection."""
import hashlib
import argparse
import json
from pathlib import Path
import numpy as np
import trimesh
from vv_toolbox.atlas import load_atlas
from vv_toolbox.case_io import load_case
from vv_toolbox.centerline_projection import project_outside_stations
from vv_toolbox.centerline_projection import refine_projected_path
from vv_toolbox.source_sections import extract_source_sections


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--refine',action='store_true');parser.add_argument('--adaptive-inset',action='store_true');args=parser.parse_args()
    suffix='adaptive' if args.adaptive_inset else 'refined' if args.refine else 'projection'
    root=Path(__file__).resolve().parents[1]
    case,revision=load_case(root/'exports/atlas-case-inspection/all-arterial.snapshot.json')
    previous=json.loads((root/'docs/evidence/aca-branch-paths.json').read_text())
    atlas=load_atlas()
    if revision!=previous['source_case_revision'] or atlas.metadata['sha256']!=previous['atlas_archive_sha256']:
        raise ValueError('Source mismatch')
    part=next(p for p in atlas.meshes if p['id']=='FJ1690')
    mesh=trimesh.Trimesh(part['vertices'],part['faces'],process=False)
    edge=next(e for e in case['edges'] if e['id']=='FJ1690:e0');points=np.asarray(edge['centerline_mm'],float)
    movable=list(range(len(points)));protected=[]
    for index,node in [(0,edge['start']),(len(points)-1,edge['end'])]:
        if sum(node in (e['start'],e['end']) for e in case['edges'])>1:
            movable.remove(index);protected.append(index)
    report=dict(schema='vv-toolbox.frontobasal-path-projection/1',source_case_revision=revision,
        atlas_archive_sha256=atlas.metadata['sha256'],edge_id=edge['id'],protected_endpoint_indices=protected,
        protocol=dict(inset_mm=.05,max_displacement_mm=1.),status='FAIL',accepted_for_generation=False)
    try:
        method=refine_projected_path if args.refine else project_outside_stations
        candidate,meta=method(mesh,points,movable_indices=movable,inset_mm=.05,max_displacement_mm=1.,adaptive_inset=args.adaptive_inset)
        sections=extract_source_sections(mesh,candidate)
        path=root/f'exports/frontobasal-path-{suffix}.npz'
        with path.open('xb') as stream:
            np.savez_compressed(stream,original_points_mm=points,candidate_points_mm=candidate,metadata=np.array(json.dumps(meta)))
        report.update(status='CANDIDATE',artifact=str(path.relative_to(root)),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            projection=meta,source_sections=sections)
    except ValueError as error:
        report['reason']=str(error)
        if hasattr(error,'inspection'):report['rejected_path_inspection']=error.inspection
    report['refinement_enabled']=args.refine
    report['adaptive_inset']=args.adaptive_inset
    destination=f'frontobasal-path-{suffix}.json'
    (root/'docs/evidence'/destination).write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(report['status'],report.get('reason'),report.get('projection',{}).get('maximum_displacement_mm'),
          report.get('source_sections',{}).get('counts'),flush=True)


if __name__=='__main__':main()
