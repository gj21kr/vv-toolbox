"""Fixed eight-edge audit; no threshold tuning or exclusion after failures."""
import json
import argparse
from inspect_workbench_mca_smoothing import main, ROOT

EDGES=['FJ1654:e0','FJ1654M:e0','FJ1660:e0','FJ1660M:e0',
       'FJ1692:e0','FJ1692M:e0','FJ1694:e0','FJ1694M:e0']
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--exact-indices',action='store_true')
args=parser.parse_args()
rows=[]
for edge_id in EDGES:
    try:
        report=main(edge_id,exact_indices=args.exact_indices)
    except (ValueError,OSError) as error:
        report=dict(status='FAIL',reason=str(error),
            parameters=dict(edge_id=edge_id,sigma_mm=.5,max_displacement_mm=.3))
    row=dict(edge_id=edge_id,status=report['status'],parameters=report['parameters'])
    if 'measurements' in report:
        row['max_displacement_mm']=report['centerline_metrics'][0]['max_displacement_mm']
        row['measurements']={name:dict(
            stations=values['stations'],sampled_intervals=values['sampled_intervals'],
            section_count=len(values['cross_sections']),
            measured_sections=sum(s['status']=='MEASURED' for s in values['cross_sections']))
            for name,values in report['measurements'].items()}
    else:
        row['reason']=report.get('reason','unknown')
    rows.append(row)
summary=dict(scope='Eight explicit ACA/MCA source edges; not confirmed A1-A3/M1-M3 boundaries',
    protocol=dict(sigma_mm=.5,max_displacement_mm=.3,containment_sample_spacing_mm=.1),
    status='PASS' if all(r['status']=='PASS' for r in rows) else 'UNKNOWN',
    rows=rows,anatomical_acceptance='UNKNOWN',continuous_containment='NOT RUN',
    full_femoral_cerebral_route='NOT RUN')
summary['exact_index_copies']=args.exact_indices
target=ROOT/('docs/evidence/workbench-cerebral-smoothing-summary'+
             ('-exact-indices' if args.exact_indices else '')+'.json')
target.write_text(
    json.dumps(summary,indent=2,allow_nan=False)+'\n')
print(json.dumps(dict(status=summary['status'],counts={
    state:sum(r['status']==state for r in rows) for state in ('PASS','FAIL','UNKNOWN')})))
