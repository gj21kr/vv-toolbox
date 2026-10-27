"""Separate fixed-range diagnostic; preserves the original failed designs."""
import json
from pathlib import Path
import numpy as np
from vv_toolbox.case_io import load_case
from vv_toolbox.bifurcation_placement import scan_bifurcation_placement


def main():
    root=Path(__file__).resolve().parents[1]
    source=root/'exports/candidate-case-download/case.snapshot.json'
    before=source.read_bytes();case,revision=load_case(source)
    prior=json.loads((root/'docs/evidence/access-aca-sac-attachment.json').read_text())
    if revision!=prior['case_revision']:raise ValueError('Original diagnostic revision changed')
    offsets=np.linspace(-1.,5.,121).tolist()
    attempts=[]
    for item in prior['attempts']:
        result=scan_bifurcation_placement(case,item['specification'],offsets_mm=offsets,burial_margin_mm=.15)
        attempts.append(dict(junction_id=item['junction_id'],scan=result))
        print(json.dumps(dict(junction_id=item['junction_id'],tested_count=result['tested_count'],
            passing_offsets_mm=result['passing_offsets_mm'],
            minimum_total_failed_samples=min(r['interior_rim_samples']+r['insufficient_burial_samples'] for r in result['samples']))))
    if source.read_bytes()!=before:raise RuntimeError('Input changed')
    report=dict(schema='vv-toolbox.aca-placement-diagnostic/1',case_revision=revision,input_unchanged=True,
        scope='Separate fixed -1 to +5 mm normal translation scan in 0.05 mm steps; original failure preserved',
        attempts=attempts,accepted_for_generation=False,app_applied=False)
    (root/'docs/evidence/aca-placement-offsets.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')


if __name__=='__main__':main()
