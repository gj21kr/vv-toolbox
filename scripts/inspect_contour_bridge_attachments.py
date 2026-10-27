"""Measure candidate end caps against declared source volumes without union."""
import hashlib
import json
import argparse
from pathlib import Path

import numpy as np
import trimesh

from vv_toolbox.case_io import load_case
from vv_toolbox.estimated_tube_volume import cap_estimated_neck
from vv_toolbox.surface_indexing import exact_vertex_index_copy
from vv_toolbox.voxel_output import _inside


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--preserve-corners',action='store_true')
    args=parser.parse_args()
    suffix='-corners' if args.preserve_corners else ''
    record=json.loads(Path('docs/evidence/atlas-neck-volume-case.json').read_text())
    case,revision=load_case(record['derived_case_file'])
    parts={p['part_id']:p for p in case['surface_parts']}
    measurement=json.loads(Path('docs/evidence/neck-source-contours.json').read_text())
    profiles={(r['part_id'],r['end']):r for r in measurement['rows']
              if r['plane_definition']=='endpoint_tangent_normal'}
    candidate_report=json.loads(Path('docs/evidence/neck-candidate-contacts.json').read_text())
    if args.preserve_corners:
        built=json.loads(Path('docs/evidence/neck-contour-candidates-corners.json').read_text())
        candidate_report={'candidate_file_sha256':{
            r['part_id']:hashlib.sha256((Path('exports/neck-contour-candidates-corners')/
                                       (r['part_id']+'.npz')).read_bytes()).hexdigest()
            for r in built['candidates']}}
    rows=[]
    for pid,digest in candidate_report['candidate_file_sha256'].items():
        path=Path('exports/neck-contour-candidates'+suffix)/(pid+'.npz')
        if hashlib.sha256(path.read_bytes()).hexdigest()!=digest:
            raise ValueError('Candidate geometry changed')
        with np.load(path,allow_pickle=False) as data:
            part=dict(vertices=data['vertices'],faces=data['faces'],
                      metadata=dict(kind='estimated-neck-connector',original_atlas_geometry=False))
            n_side=len(part['faces'])
            closed=cap_estimated_neck(part,max_planarity_mm=.001,cap_method='planar-earcut')
        vertices,faces=closed['vertices'],closed['faces']
        caps=faces[n_side:]
        for end in (0,1):
            row=profiles[pid,end];profile=row['profile'];source=parts[row['target']]
            mesh,_=exact_vertex_index_copy(trimesh.Trimesh(
                source['vertices_mm'],source['faces'],process=False))
            origin=np.asarray(profile['origin_mm']);normal=np.asarray(profile['normal'])
            cap=caps[np.max(np.abs((vertices[caps]-origin)@normal),axis=1)<1e-6]
            if not len(cap) or not mesh.is_volume:
                raise ValueError('Missing candidate cap or valid source volume')
            triangles=vertices[cap]
            probes=np.unique(np.concatenate([
                triangles.reshape(-1,3),triangles.mean(1),
                ((triangles+np.roll(triangles,1,axis=1))/2).reshape(-1,3)]),axis=0)
            inside=_inside(probes,mesh.triangles,1e-8)
            outside=probes[~inside]
            distances=trimesh.proximity.closest_point(mesh,outside)[1] if len(outside) else np.array([])
            witness=origin+(.25 if end==0 else -.25)*normal
            overlap=bool(_inside(witness[None],mesh.triangles,1e-8)[0]
                         and _inside(witness[None],vertices[faces],1e-8)[0])
            rows.append(dict(part_id=pid,target=row['target'],end=end,
                             cap_samples=len(probes),outside_samples=len(outside),
                             maximum_outside_distance_mm=float(distances.max()) if len(distances) else 0.,
                             sampled_cap_coverage='PASS' if inside.all() else 'FAIL',
                             witness_mm=witness.tolist(),interior_overlap_witness=overlap,
                             witness_definition='0.25 mm from declared origin along inward bridge endpoint normal'))
            print(json.dumps(rows[-1]),flush=True)
    report=dict(case_revision=revision,candidate_file_sha256=candidate_report['candidate_file_sha256'],
                rows=rows,cap_coverage_pass=sum(r['sampled_cap_coverage']=='PASS' for r in rows),
                overlap_witness_pass=sum(r['interior_overlap_witness'] for r in rows),
                continuous_lumen='NOT RUN',anatomical_validation='NOT RUN',live_scene_changed=False)
    Path('docs/evidence/contour-bridge-attachments'+suffix+'.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':
    main()
