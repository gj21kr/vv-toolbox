"""Inspect surface-following contours on both previously failing MCA designs."""
import json
from pathlib import Path
import hashlib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from vv_toolbox.case_io import load_case
from vv_toolbox.surface_neck import propose_surface_neck

ROOT=Path(__file__).resolve().parents[1]


def main():
    path=ROOT/'exports/atlas-case-inspection/all-arterial.snapshot.json'
    before=path.read_bytes()
    case,revision=load_case(path)
    paths=['mca-saccular-grid-recheck-3000000.json','left-mca-saccular-frame.json']
    results=[]
    fig,axes=plt.subplots(1,2,figsize=(11,4))
    for ax,name in zip(axes,paths):
        prior=json.loads((ROOT/'docs/evidence'/name).read_text())
        spec=prior['specification']
        if spec['case_revision']!=revision:
            raise ValueError('stale source')
        try:
            result=propose_surface_neck(case,spec,ray_half_span_mm=1.,ray_step_mm=.05)
            ax.plot(np.arange(64)*360/64,result['normal_offsets_mm'])
            ax.axhline(0,color='grey',ls='--')
            ax.set(xlabel='Projected ellipse angle (degrees)',ylabel='Surface offset from design plane (mm)',
                   title=spec['parameters']['edge_id']+' — nonplanar proposal')
        except ValueError as error:
            result=dict(status='FAIL',edge_id=spec['parameters']['edge_id'],reason=str(error))
            ax.text(.1,.5,str(error),wrap=True)
        results.append(result)
    fig.suptitle('Derived profile surface crossings; no generated sac or anatomical approval')
    fig.tight_layout()
    out=ROOT/'exports/surface-neck'
    out.mkdir(exist_ok=True)
    fig.savefig(out/'offsets.png',dpi=150)
    plt.close(fig)
    report=dict(case_revision=revision,input_unchanged=path.read_bytes()==before,
        results=results,figure_sha256=hashlib.sha256((out/'offsets.png').read_bytes()).hexdigest(),
        app_applied=False,generated_sac='NOT RUN')
    if not report['input_unchanged']:
        raise ValueError('input changed')
    (ROOT/'docs/evidence/surface-neck-inspection.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps([{k:v for k,v in r.items() if k not in ('curve_mm','normal_offsets_mm','frame')}
                      for r in results]))


if __name__=='__main__':
    main()
