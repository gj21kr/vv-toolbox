"""Separate ICA/ACA junction candidate with original-source lineage retained."""
import hashlib
import argparse
import json
from pathlib import Path

import numpy as np
import trimesh

from vv_toolbox.case_io import load_case
from vv_toolbox.estimated_tube_volume import cap_estimated_neck
from vv_toolbox.solid_union import build_solid_union
from vv_toolbox.union_lineage import compose_face_lineage, verify_face_lineage


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--acom',action='store_true')
    args=parser.parse_args()
    pid='estimated_left_carotid_neck'
    record=json.loads(Path('docs/evidence/atlas-neck-volume-case.json').read_text())
    case,revision=load_case(record['derived_case_file'])
    prior=json.loads(Path('docs/evidence/carotid-solid-union-diagnostic-float64-lineage.json').read_text())
    checks=json.loads(Path('docs/evidence/carotid-union-lineage.json').read_text())
    if revision!=prior['source_case_revision'] or revision!=checks['source_case_revision']:
        raise ValueError('Parent source revisions differ')
    row=next(r for r in prior['rows'] if r['part_id']==pid)
    check=next(r for r in checks['rows'] if r['part_id']==pid)
    path=Path('exports/carotid-solid-union-diagnostic-float64-lineage')/(pid+'.npz')
    if check['status']!='PASS' or hashlib.sha256(path.read_bytes()).hexdigest()!=check['union_sha256']:
        raise ValueError('Parent union does not match verified lineage')
    parent_lineage=row['face_lineage']
    input_surfaces=dict(row['input_surfaces'])
    parent_hash=check['union_sha256']
    added_source='FJ1654M'
    output_name='left-carotid-aca-union.json'
    output_folder='carotid-aca-junction'
    if args.acom:
        previous=json.loads(Path('docs/evidence/left-carotid-aca-union.json').read_text())
        path=Path('exports/carotid-aca-junction/left.npz')
        if (previous['status']!='CANDIDATE' or previous['source_case_revision']!=revision
                or previous['lineage_check']['status']!='PASS'
                or hashlib.sha256(path.read_bytes()).hexdigest()!=previous['output_sha256']):
            raise ValueError('ACA parent candidate identity mismatch')
        parent_lineage=previous['face_lineage']
        input_surfaces.update(previous['union']['input_surfaces'])
        parent_hash=previous['output_sha256']
        added_source='FJ1655'
        output_name='left-carotid-aca-acom-union.json'
        output_folder='carotid-aca-acom-junction'
    with np.load(path,allow_pickle=False) as data:
        parent=trimesh.Trimesh(data['vertices'],data['faces'],process=False)
    parts={p['part_id']:p for p in case['surface_parts']}
    source=parts[added_source]
    aca=trimesh.Trimesh(source['vertices_mm'],source['faces'],process=False)
    report=dict(source_case_revision=revision,parent_union_sha256=parent_hash,
                added_source=added_source,live_scene_changed=False,
                whole_context='NOT RUN',anatomical_validation='NOT RUN')
    if args.acom:
        report['reference_relation']=dict(id='acom',specimen_status='unverified',
            source_url='https://pubmed.ncbi.nlm.nih.gov/6111033/',
            right_aca_connection='NOT INCLUDED in this candidate')
    try:
        merged,audit=build_solid_union({'parent':parent,added_source:aca})
        flat=compose_face_lineage(audit['face_lineage'],{'parent':parent_lineage})
        sources={added_source:aca}
        for name in parent_lineage['source_names']:
            if name==pid:
                with np.load(Path('exports/neck-contour-candidates-corners')/(pid+'.npz'),allow_pickle=False) as data:
                    capped=cap_estimated_neck(dict(vertices=data['vertices'],faces=data['faces'],
                        metadata=dict(kind='estimated-neck-connector',original_atlas_geometry=False)),
                        max_planarity_mm=.001,cap_method='planar-earcut')
                mesh=trimesh.Trimesh(capped['vertices'],capped['faces'],process=False)
            else:
                p=parts[name];mesh=trimesh.Trimesh(p['vertices_mm'],p['faces'],process=False)
            digest=hashlib.sha256(np.asarray(mesh.vertices,dtype='<f8').tobytes()+
                                  np.asarray(mesh.faces,dtype='<i8').tobytes()).hexdigest()
            if digest!=input_surfaces[name]['geometry_sha256']:
                raise ValueError('Original input source changed')
            sources[name]=mesh
        validation=verify_face_lineage(merged,sources,flat)
        if validation['status']!='PASS':
            raise ValueError('Flattened original-source lineage failed verification')
        folder=Path('exports')/output_folder;folder.mkdir(parents=True,exist_ok=True)
        output=folder/'left.npz'
        np.savez_compressed(output,vertices=merged.vertices,faces=merged.faces)
        report.update(status='CANDIDATE',union=audit,face_lineage=flat,lineage_check=validation,
                      output_sha256=hashlib.sha256(output.read_bytes()).hexdigest())
    except ValueError as error:
        report.update(status='FAIL',reason=str(error))
    (Path('docs/evidence')/output_name).write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({key:value for key,value in report.items() if key not in ('union','face_lineage','lineage_check')}),flush=True)


if __name__=='__main__':
    main()
