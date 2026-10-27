"""Audit fixed workbench smoothing settings on the saved right-MCA source edge."""
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh

from vv_toolbox.atlas import load_atlas
from vv_toolbox.case_io import load_case, save_case, case_digest
from vv_toolbox.label_workbench import _smooth_copy
from inspect_atlas_edit_sections import containment, sections

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'exports/atlas-case-inspection/all-arterial.snapshot.json'
PARAMETERS=dict(edge_id='FJ1692:e0',sigma_mm=.5,max_displacement_mm=.3)


def sample_polyline(points, spacing=.1):
    points=np.asarray(points,dtype=float)
    lengths=np.linalg.norm(np.diff(points,axis=0),axis=1)
    output=[]
    for a,b,length in zip(points,points[1:],lengths):
        count=max(1,int(np.ceil(length/spacing)))
        output.extend(a+(b-a)*t/count for t in range(count))
    return np.asarray(output+[points[-1]])


def main(edge_id='FJ1692:e0', *, exact_indices=False):
    parameters=dict(PARAMETERS,edge_id=edge_id)
    case,revision=load_case(SOURCE)
    atlas=load_atlas()
    if not any(s['id']=='bp3d' and s['sha256']==atlas.metadata['sha256'] for s in case['sources']):
        raise ValueError('Atlas source hash mismatch')
    original=next(e for e in case['edges'] if e['id']==edge_id)
    part=next(p for p in atlas.meshes if p['id']==edge_id.split(':')[0])
    mesh=trimesh.Trimesh(part['vertices'],part['faces'],process=False)
    indexing=None
    if exact_indices:
        from vv_toolbox.surface_indexing import exact_vertex_index_copy
        mesh,indexing=exact_vertex_index_copy(mesh)
        if not indexing['usable_for_sampled_containment']:
            raise ValueError('Exact index copy remains unsuitable for containment')
    report=dict(scope='Fixed single-edge centerline smoothing and source-surface sampled containment only',
        parameters=parameters,source_file='exports/atlas-case-inspection/all-arterial.snapshot.json',
        source_file_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        source_case_revision=revision,atlas_archive_sha256=atlas.metadata['sha256'],
        surface_triangle_sha256=hashlib.sha256(np.asarray(mesh.vertices[mesh.faces],dtype='<f8').tobytes()).hexdigest(),
        surface_watertight=bool(mesh.is_watertight),clinical_validation='NOT RUN',
        complete_route_acceptance='NOT RUN',new_surface_generation='NOT RUN')
    if indexing is not None:report['index_normalization']=indexing
    try:
        changed=_smooth_copy(case,parameters)
    except ValueError as error:
        report.update(status='FAIL',reason=str(error))
    else:
        modified=next(e for e in changed['edges'] if e['id']==original['id'])
        rows={}
        for name,edge in [('source',original),('smoothed',modified)]:
            path=dict(points=edge['centerline_mm'],radii=edge['radii_mm'])
            rows[name]=dict(stations=containment(mesh,np.asarray(path['points'])),
                sampled_intervals=containment(mesh,sample_polyline(path['points'])),
                cross_sections=sections(mesh,path))
        checks=dict(nodes_unchanged=case['nodes']==changed['nodes'],
            endpoint_chords_unchanged=all(original['centerline_mm'][i]==modified['centerline_mm'][i] for i in (0,1,-2,-1)),
            radii_unchanged=original['radii_mm']==modified['radii_mm'],
            other_edges_unchanged=all(a==b for a,b in zip(case['edges'],changed['edges']) if a['id']!=original['id']),
            source_unchanged=case_digest(case)==revision)
        complete=mesh.is_watertight and all(
            rows[name][kind].get('inside_count')==rows[name][kind]['point_count']
            for name in rows for kind in ('stations','sampled_intervals'))
        relative=f'exports/cerebral-workbench-smoothing/{edge_id.replace(":","-")}/{case_digest(changed)[:16]}/case.snapshot.json'
        output=ROOT/relative
        if output.exists():
            if load_case(output)[1]!=case_digest(changed):raise ValueError('Existing candidate differs')
        else:save_case(output,changed)
        report.update(status='PASS' if complete and all(checks.values()) else 'UNKNOWN',
            checks=checks,measurements=rows,
            centerline_metrics=changed['centerline_regularization']['metrics'],
            result_case_revision=case_digest(changed),
            result_file=relative,
            interpretation='PASS is limited to fixed endpoints/radii and sampled containment, not continuous containment or anatomical validity.')
    target=ROOT/('docs/evidence/workbench-mca-smoothing.json' if edge_id=='FJ1692:e0'
                 else f'docs/evidence/workbench-smoothing-{edge_id.replace(":","-")}.json')
    if exact_indices:target=target.with_stem(target.stem+'-exact-indices')
    target.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:report[k] for k in ('status','scope','parameters')}))
    return report


if __name__=='__main__':
    main()
