"""Project the fixed ACA engineering ellipses without changing old failures."""
import json
from pathlib import Path
from vv_toolbox.case_io import load_case
from vv_toolbox.bifurcation_saccular import bifurcation_saccular_spec
from vv_toolbox.bifurcation_rim import project_bifurcation_rim


def main():
    root=Path(__file__).resolve().parents[1]
    source=root/'exports/candidate-case-download/case.snapshot.json'
    before=source.read_bytes();case,revision=load_case(source)
    frames=json.loads((root/'docs/evidence/aca-envelope-frames.json').read_text())
    if revision!=frames['case_revision']:raise ValueError('Source revision changed')
    attempts=[]
    for row in frames['attempts']:
        spec=bifurcation_saccular_spec(case,**row['frame']['parameters'])
        rim=project_bifurcation_rim(case,spec,lower_mm=-5.,upper_mm=5.,step_mm=.05)
        attempts.append(dict(junction_id=row['junction_id'],specification=spec,projection=rim))
        print(json.dumps(dict(junction_id=row['junction_id'],status=rim['status'],
                              resolved_samples=rim['resolved_sample_count'],total=rim['sample_count'])))
    if source.read_bytes()!=before:raise RuntimeError('Input changed')
    report=dict(schema='vv-toolbox.aca-projected-rim-diagnostic/1',case_revision=revision,input_unchanged=True,
                attempts=attempts,accepted_for_generation=False,app_applied=False)
    (root/'docs/evidence/aca-projected-rims.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')


if __name__=='__main__':main()
