"""Fixed 0.02 mm engineering field-residual test on saved ACA rim proposals."""
import json
from pathlib import Path
from vv_toolbox.case_io import load_case
from vv_toolbox.bifurcation_rim_continuity import inspect_projected_rim


def main():
    root=Path(__file__).resolve().parents[1]
    source=root/'exports/candidate-case-download/case.snapshot.json'
    before=source.read_bytes();case,revision=load_case(source)
    prior=json.loads((root/'docs/evidence/aca-projected-rims.json').read_text())
    if prior['case_revision']!=revision:raise ValueError('Source revision changed')
    rows=[]
    for item in prior['attempts']:
        report=inspect_projected_rim(case,item['specification'],item['projection'],tolerance_mm=.02)
        rows.append(dict(junction_id=item['junction_id'],inspection=report))
        print(json.dumps(dict(junction_id=item['junction_id'],status=report['status'],
            max_bound_mm=report['maximum_continuous_absolute_field_bound_mm'],
            failed_chords=sum(r['status']=='FAIL' for r in report['chords']),samples=report['total_sample_count'])))
    if source.read_bytes()!=before:raise RuntimeError('Source changed')
    result=dict(schema='vv-toolbox.aca-rim-continuity-diagnostic/1',case_revision=revision,
                input_unchanged=True,attempts=rows,accepted_for_generation=False,app_applied=False)
    (root/'docs/evidence/aca-rim-continuity.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')


if __name__=='__main__':main()
