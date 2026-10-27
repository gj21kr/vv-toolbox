"""Fixed right ACA tilt sweep with unchanged neck center and sac dimensions."""
import hashlib
import argparse
import json
from pathlib import Path
import numpy as np
from vv_toolbox.atlas import load_atlas
from vv_toolbox.case_io import load_case
from vv_toolbox.bifurcation_saccular import bifurcation_saccular_spec
from vv_toolbox.source_sac_union import build_source_sac_union
from vv_toolbox.mesh_pair_contact import inspect_pair_contact


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--axis',choices=['width','depth'],default='width')
    parser.add_argument('--translate',action='store_true',help='Move neck along axis instead of rotating')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    prior=json.loads((root/'docs/evidence/aca-source-cut-sac-unions.json').read_text())
    case,revision=load_case(root/'exports/candidate-case-download/case.snapshot.json')
    atlas=load_atlas()
    if revision!=prior['case_revision'] or atlas.metadata['sha256']!=prior['atlas_archive_sha256']:
        raise ValueError('Source identity changed')
    base=next(r for r in prior['rows'] if r['parent_part_id']=='FJ1654')['metadata']['specification']
    parts={p['id']:p for p in atlas.meshes if p['layer']=='arterial'};parent=parts['FJ1654']
    suffix='' if args.axis=='width' else '-depth'
    if args.translate:suffix+='-translate'
    output=root/f'exports/right-aca-tilts{suffix}';output.mkdir(exist_ok=True)
    values=[-1.,-.5,.5,1.] if args.translate else [-30,-15,15,30]
    report=dict(schema='vv-toolbox.right-aca-tilts/1',state='RUNNING',case_revision=revision,
        atlas_archive_sha256=atlas.metadata['sha256'],expected_values=values,
        parameter='neck_offset_mm' if args.translate else 'angle_degrees',
        rotation_axis=args.axis,
        protocol=('Translate neck center along declared axis. Preserve frame, dimensions and source. Evaluate every offset.' if args.translate else
                  'Rotate neck frame around declared axis. Preserve center, dimensions and source. Evaluate every angle.'),
        accepted_for_generation=False,containment='NOT RUN',branch_patency='NOT RUN',attempts=[])
    report_path=root/f'docs/evidence/right-aca-tilts{suffix}.json'
    for angle in values:
        row={report['parameter']:angle,'status':'FAIL'}
        try:
            params=base['parameters'].copy();normal=np.asarray(params['outward_normal']);width=np.asarray(params['width_direction'])
            axis=width if args.axis=='width' else np.cross(normal,width)
            rad=np.deg2rad(angle)
            def rotate(vector):
                return vector*np.cos(rad)+np.cross(axis,vector)*np.sin(rad)+axis*(axis@vector)*(1-np.cos(rad))
            if args.translate:
                params['neck_center_mm']=(np.asarray(params['neck_center_mm'])+axis*angle).tolist()
            else:
                params['outward_normal']=rotate(normal).tolist()
                params['width_direction']=rotate(width).tolist()
            spec=bifurcation_saccular_spec(case,**params)
            v,f,meta=build_source_sac_union(case,spec,parent['vertices'],parent['faces'],source_part_id='FJ1654')
            dome=v[f[np.asarray(meta['source_face_ids'])<0]]
            low,high=dome.min((0,1)),dome.max((0,1));checks=[];separated=[]
            for ident,part in sorted(parts.items()):
                if ident=='FJ1654':continue
                other=np.asarray(part['vertices'],float)[np.asarray(part['faces'])]
                if np.any(other.min((0,1))>high+1e-8) or np.any(other.max((0,1))<low-1e-8):
                    separated.append(ident);continue
                checks.append(dict(part_id=ident,inspection=inspect_pair_contact(dome,other)))
            contacts=[c['part_id'] for c in checks if c['inspection']['status']=='CONTACT_DETECTED']
            complete=all(c['inspection']['complete'] for c in checks)
            path=output/f'tilt-{angle}.npz'
            with path.open('xb') as stream:np.savez_compressed(stream,vertices_mm=v,faces=f,metadata=np.array(json.dumps(meta)))
            row.update(status='CONTACT_DETECTED' if contacts else 'NO_DOME_SURFACE_CONTACT' if complete else 'UNKNOWN',
                artifact=str(path.relative_to(root)),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                contacts=contacts,checks=checks,aabb_separated_parts=separated,coverage_complete=complete,
                compared_other_arteries=len(parts)-1,specification=spec)
        except ValueError as error:row['reason']=str(error)
        report['attempts'].append(row)
        report_path.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
        print(angle,row['status'],row.get('contacts',row.get('reason')),flush=True)
    report['state']='COMPLETED'
    report_path.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')


if __name__=='__main__':main()
