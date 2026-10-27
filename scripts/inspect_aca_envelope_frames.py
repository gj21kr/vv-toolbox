"""Actual ACA diagnostic with fixed envelope-ray frame settings."""
import json
from pathlib import Path
import numpy as np
from vv_toolbox.case_io import load_case
from vv_toolbox.bifurcation_frame import propose_bifurcation_frame
from vv_toolbox.bifurcation_saccular import bifurcation_saccular_spec
from vv_toolbox.bifurcation_attachment import inspect_bifurcation_attachment
from vv_toolbox.bifurcation_placement import scan_bifurcation_placement


def main():
    root=Path(__file__).resolve().parents[1]
    source=root/'exports/candidate-case-download/case.snapshot.json'
    before=source.read_bytes();case,revision=load_case(source)
    original=json.loads((root/'docs/evidence/access-aca-sac-attachment.json').read_text())
    if revision!=original['case_revision']:raise ValueError('Source revision changed')
    rows=[]
    for item in original['attempts']:
        row=dict(junction_id=item['junction_id'])
        try:
            frame=propose_bifurcation_frame(case,item['specification'],search_mm=10.,step_mm=.05,gradient_step_mm=.001)
            spec=bifurcation_saccular_spec(case,**frame['parameters'])
            attachment=inspect_bifurcation_attachment(case,spec,burial_margin_mm=.15)
            scan=scan_bifurcation_placement(case,spec,offsets_mm=np.linspace(-1,5,121).tolist(),burial_margin_mm=.15)
            row.update(frame=frame,attachment=attachment,scan=scan,status=attachment['status'])
        except ValueError as error:row.update(status='FAIL',reason=str(error))
        rows.append(row)
        print(json.dumps(dict(junction_id=row['junction_id'],status=row['status'],reason=row.get('reason'),
            passing_offsets_mm=row.get('scan',{}).get('passing_offsets_mm'),
            normal=row.get('frame',{}).get('parameters',{}).get('outward_normal'))))
    if source.read_bytes()!=before:raise RuntimeError('Source changed')
    report=dict(schema='vv-toolbox.aca-envelope-frame-diagnostic/1',case_revision=revision,input_unchanged=True,
        attempts=rows,geometry_generation='NOT RUN',app_applied=False,accepted_for_generation=False)
    (root/'docs/evidence/aca-envelope-frames.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')


if __name__=='__main__':main()
