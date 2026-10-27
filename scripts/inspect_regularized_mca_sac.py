"""Regenerate a source-bound sac on the bounded, regularized MCA baseline."""
import hashlib
import json
from pathlib import Path
import numpy as np
from vv_toolbox.case_io import load_case
from vv_toolbox.saccular import saccular_spec
from vv_toolbox.saccular_frame import propose_saccular_frame
from vv_toolbox.surface_neck_union import build_surface_neck_union
from vv_toolbox.surface_regularization import regularize_surface
from vv_toolbox.surface_context import inspect_surface_context

ROOT=Path(__file__).resolve().parents[1]


def main():
    path=ROOT/'exports/mca-profile-regularization/case.snapshot.json'
    source=path.read_bytes()
    case,revision=load_case(path)
    profile=json.loads((ROOT/'docs/evidence/mca-profile-regularization.json').read_text())
    if profile['case_revision']!=revision or profile['artifact_sha256']!=hashlib.sha256(source).hexdigest():
        raise ValueError('regularized baseline evidence mismatch')
    old=json.loads((ROOT/'docs/evidence/mca-saccular-grid-recheck-3000000.json').read_text())['specification']
    if old['case_revision']!=profile['source_case_revision']:
        raise ValueError('old design lineage mismatch')
    parent=next(e for e in case['edges'] if e['id']==old['parameters']['edge_id'])
    lengths=np.linalg.norm(np.diff(np.array(parent['centerline_mm']),axis=0),axis=1)
    index,fraction=old['parent_anchor']['interval_index'],old['parent_anchor']['fraction']
    station=float(lengths[:index].sum()+fraction*lengths[index])
    frame=propose_saccular_frame(case,parent['id'],station,
        old['parameters']['outward_normal'],search_mm=8.)
    parameters=dict(old['parameters'])
    parameters.update(station_mm=station,**{k:frame[k] for k in
        ('neck_center_mm','outward_normal','width_direction')})
    spec=saccular_spec(case,**parameters)
    report=dict(case_revision=revision,previous_case_revision=old['case_revision'],
        placement_policy='retain original interval index and interpolation fraction',
        specification=spec,frame_proposal=frame,app_applied=False)
    print('Generating regularized MCA union at 0.15 mm',flush=True)
    try:
        vertices,faces,meta=build_surface_neck_union(case,spec,spacing_mm=.15,
            ray_half_span_mm=1.,ray_step_mm=.05)
        vertices,faces,smoothing=regularize_surface(vertices,faces,iterations=10,
            max_displacement_mm=.15,max_volume_change_fraction=.02)
        audit=inspect_surface_context(case,vertices,faces,parent_edge_id=parent['id'])
        out=ROOT/'exports/regularized-mca-sac'
        out.mkdir(exist_ok=True)
        np.savez_compressed(out/'surface.npz',vertices_mm=vertices,faces=faces,
            metadata=np.array(json.dumps(dict(meta,surface_regularization=smoothing))))
        report.update(status='CANDIDATE',vertices=len(vertices),triangles=len(faces),
            union_checks=meta['checks'],surface_regularization=smoothing,
            context_inspection=audit,
            artifact_sha256=hashlib.sha256((out/'surface.npz').read_bytes()).hexdigest(),
            neck_dimensions_after_remesh='NOT RUN',clinical_validation='NOT RUN')
    except ValueError as error:
        report.update(status='FAIL',reason=str(error))
    report['input_unchanged']=source==path.read_bytes()
    if not report['input_unchanged']:
        raise ValueError('baseline changed')
    (ROOT/'docs/evidence/regularized-mca-sac.json').write_text(
        json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:report[k] for k in ('status','reason','vertices','triangles') if k in report}))


if __name__=='__main__':
    main()
