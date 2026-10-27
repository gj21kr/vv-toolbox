"""Six predeclared engineering directions, unchanged dimensions and gates."""
import hashlib
import json
from pathlib import Path
import numpy as np
from vv_toolbox.atlas import load_atlas
from vv_toolbox.case_io import load_case
from vv_toolbox.bifurcation_saccular import bifurcation_saccular_spec
from vv_toolbox.bifurcation_frame import propose_bifurcation_frame
from vv_toolbox.bifurcation_rim import project_bifurcation_rim
from vv_toolbox.curved_sac_patch import build_curved_sac_patch
from vv_toolbox.mesh_pair_contact import inspect_pair_contact


def main():
    root=Path(__file__).resolve().parents[1]
    source=root/'exports/candidate-case-download/case.snapshot.json'
    before=source.read_bytes();case,revision=load_case(source)
    prior=json.loads((root/'docs/evidence/access-aca-sac-attachment.json').read_text())
    if revision!=prior['case_revision']:raise ValueError('Case revision changed')
    atlas=load_atlas()
    if atlas.metadata['sha256']!=next(s['sha256'] for s in case['sources'] if s['id']=='bp3d'):
        raise ValueError('Atlas changed')
    parts={p['id']:p for p in atlas.meshes if p['layer']=='arterial'}
    bounds={key:(np.min(p['vertices'],axis=0),np.max(p['vertices'],axis=0)) for key,p in parts.items()}
    output=root/'exports/aca-direction-candidates';output.mkdir(exist_ok=True)
    report=dict(schema='vv-toolbox.aca-direction-candidates/1',state='RUNNING',case_revision=revision,
        atlas_archive_sha256=atlas.metadata['sha256'],expected_attempts=6,
        protocol='Per side: posterior +Y, superior +Z, lateral (right -X; left +X). Fixed 2x1 neck, 4x3x5 dome, 0.5 blend mm. No stop after success.',
        accepted_for_generation=False,app_applied=False,attempts=[])
    report_path=root/'docs/evidence/aca-direction-candidates.json'
    for side,item in enumerate(prior['attempts']):
        parent='FJ1654' if side==0 else 'FJ1654M'
        directions=[('posterior',[0,1,0],[1,0,0]),('superior',[0,0,1],[1,0,0]),
                    ('lateral',[-1,0,0] if side==0 else [1,0,0],[0,0,1])]
        for name,direction,width in directions:
            row=dict(junction_id=item['junction_id'],direction_name=name,ray=direction,status='FAIL',surface_published=False)
            try:
                params=dict(item['specification']['parameters'],outward_normal=direction,width_direction=width)
                initial=bifurcation_saccular_spec(case,**params)
                frame=propose_bifurcation_frame(case,initial,search_mm=10.,step_mm=.05,gradient_step_mm=.001)
                spec=bifurcation_saccular_spec(case,**frame['parameters']);row.update(frame_proposal=frame,specification=spec)
                projection=project_bifurcation_rim(case,spec,lower_mm=-5.,upper_mm=5.,step_mm=.05)
                row['resolved_rim_samples']=projection['resolved_sample_count']
                if projection['curve_mm'] is None:raise ValueError('Incomplete projected rim')
                vertices,faces,meta=build_curved_sac_patch(case,spec,projection,rim_tolerance_mm=.02)
                triangles=vertices[faces];low,high=vertices.min(axis=0),vertices.max(axis=0)
                pairs=[];separated=[]
                for ident in sorted(parts):
                    lo,hi=bounds[ident]
                    if np.any(lo>high+1e-8) or np.any(hi<low-1e-8):separated.append(ident);continue
                    part=parts[ident]
                    checked=inspect_pair_contact(triangles,np.asarray(part['vertices'])[np.asarray(part['faces'])],tolerance_mm=1e-8)
                    pairs.append(dict(part_id=ident,inspection=checked))
                contacting=[r['part_id'] for r in pairs if r['inspection']['status']=='CONTACT_DETECTED']
                others=[ident for ident in contacting if ident!=parent]
                complete=all(r['inspection']['complete'] for r in pairs)
                path=output/f'{side}-{name}.npz'
                with path.open('xb') as stream:np.savez_compressed(stream,vertices_mm=vertices,faces=faces,metadata=np.array(json.dumps(meta)))
                row.update(status='CONTACT_DETECTED' if others else 'NO_OTHER_SURFACE_CONTACT_DETECTED' if complete else 'UNKNOWN',
                    surface_published=True,artifact=str(path.relative_to(root)),artifact_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                    metadata=meta,contacting_parts=contacting,other_contacting_parts=others,parent_part_id=parent,
                    checked_arterial_parts=len(parts),coverage_complete=complete,aabb_separated_parts=separated,tested_pairs=pairs,
                    containment='NOT RUN',parent_attachment='UNKNOWN')
            except ValueError as error:row['reason']=str(error)
            report['attempts'].append(row)
            report_path.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
            print(json.dumps({k:row.get(k) for k in ('junction_id','direction_name','status','reason','other_contacting_parts')}),flush=True)
    if source.read_bytes()!=before:raise RuntimeError('Source changed')
    report.update(state='COMPLETE',input_unchanged=True)
    report_path.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')


if __name__=='__main__':main()
