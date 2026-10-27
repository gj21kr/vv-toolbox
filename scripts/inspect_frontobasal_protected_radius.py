"""Independent fixed-collar radius probes on all three source arm regions."""
import hashlib
import argparse
import json
from pathlib import Path

import numpy as np
import trimesh

from vv_toolbox.case_io import load_case
from vv_toolbox.union_radius import scale_selected_radius


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--external-contacts',action='store_true')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    reports=root/'docs/evidence'
    prior=json.loads((reports/'frontobasal-junction-partition.json').read_text())
    junction_path=reports/'frontobasal-source-junction.json'
    junction=json.loads(junction_path.read_text())
    if hashlib.sha256(junction_path.read_bytes()).hexdigest()!=prior['parent_report_sha256']:
        raise ValueError('Port report changed')
    if prior['status']!='CANDIDATE' or prior['self_contact']['status']!='NO_CONTACT_DETECTED':
        raise ValueError('Checked partition required')
    path=root/prior['artifact']
    if hashlib.sha256(path.read_bytes()).hexdigest()!=prior['sha256']:
        raise ValueError('Partition changed')
    with np.load(path,allow_pickle=False) as data:
        mesh=trimesh.Trimesh(data['vertices_mm'],data['faces'],process=False)
        labels=data['face_region_labels']
        original_faces=data['source_face_ids']
    case,revision=load_case(root/'exports/atlas-case-inspection/all-arterial.snapshot.json')
    if revision!=junction['source_case_revision']:
        raise ValueError('Source graph changed')
    centered=json.loads((reports/'frontobasal-centering.json').read_text())
    if centered['sha256']!=junction['path_sha256']:
        raise ValueError('Corrected path mismatch')
    centered_path=root/centered['artifact']
    if hashlib.sha256(centered_path.read_bytes()).hexdigest()!=centered['sha256']:
        raise ValueError('Corrected path changed')
    with np.load(centered_path,allow_pickle=False) as data:
        corrected=data['candidate_points_mm']
    edges={e['id']:e for e in case['edges']}
    names=['junction-region']+[p['edge_id'] for p in prior['ports']]
    lineage=dict(source_names=names,face_source_indices=labels.tolist(),source_face_indices=original_faces.tolist())
    protection=None
    protected=None
    if args.external_contacts:
        context_path=reports/'frontobasal-radius-context.json'
        context=json.loads(context_path.read_text())
        detail_path=root/context['rows'][0]['report']
        if hashlib.sha256(detail_path.read_bytes()).hexdigest()!=context['rows'][0]['sha256']:
            raise ValueError('Baseline contact report changed')
        detail=json.loads(detail_path.read_text())
        if (detail['baseline_sha256']!=prior['sha256'] or
                context['atlas_archive_sha256']!=prior['atlas_archive_sha256']):
            raise ValueError('Baseline contact identity mismatch')
        contacts=detail['context']['rows']
        if len(contacts)!=517 or len({r['neighbor_id'] for r in contacts})!=517:
            raise ValueError('Complete arterial context required')
        by_neighbor={r['neighbor_id']:sorted({p[0] for p in r['before']['contact_pairs']})
                     for r in contacts if r['before']['contact_pairs']}
        protected=sorted({f for ids in by_neighbor.values() for f in ids})
        if not protected:
            raise ValueError('Expected baseline contact faces')
        protection=dict(report=str(detail_path.relative_to(root)),
            sha256=hashlib.sha256(detail_path.read_bytes()).hexdigest(),
            protected_face_ids=protected,faces_by_neighbor=by_neighbor,
            unresolved_neighbors=[r['neighbor_id'] for r in contacts if not r['before']['complete']])
    stem='frontobasal-external-protected-radius' if args.external_contacts else 'frontobasal-protected-radius'
    output=root/'exports'/stem
    output.mkdir(exist_ok=True)
    rows=[]
    for index,name in enumerate(names[1:]):
        points=corrected if name=='FJ1690:e0' else edges[name]['centerline_mm']
        for scale in (.9,1.1):
            row=dict(edge_id=name,scale=scale,transition_mm=1.,displacement_bound_mm=.25,
                accepted_for_generation=False,neighbor_contact='NOT RUN',radius_section_agreement='NOT RUN')
            try:
                candidate,checks=scale_selected_radius(mesh,lineage,name,points,scale=scale,
                    transition_mm=1.,max_displacement_mm=.25,protect_interface_faces=True,
                    protected_face_ids=protected)
                if checks['moved_vertices']==0:
                    raise ValueError('Requested scale produced no surface change')
                artifact=output/f'arm-{index}-scale-{str(scale).replace(".","p")}.npz'
                with artifact.open('xb') as stream:
                    np.savez_compressed(stream,vertices_mm=candidate.vertices,faces=candidate.faces,
                        source_face_ids=original_faces,face_region_labels=labels,metadata=np.array(json.dumps(checks)))
                row.update(status='CANDIDATE',checks=checks,artifact=str(artifact.relative_to(root)),
                    sha256=hashlib.sha256(artifact.read_bytes()).hexdigest())
            except ValueError as error:
                row.update(status='FAIL',reason=str(error))
            rows.append(row)
            print(json.dumps(dict(edge_id=name,scale=scale,status=row['status'],reason=row.get('reason'))),flush=True)
    result=dict(schema='vv-toolbox.frontobasal-protected-radius/1',parent_artifact_sha256=prior['sha256'],
        source_case_revision=revision,rows=rows,accepted_for_generation=False,external_contact_protection=protection,
        selection_semantics='Derived source arm regions; not independently validated anatomical segment labels',
        scope='Each change starts from the same source partition. Interface triangles, junction, and other arms remain fixed.')
    (reports/f'{stem}.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')


if __name__=='__main__':main()
