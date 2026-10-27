"""Render bilateral MCA open sac patches with their preserved attachment rims."""
import hashlib
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from vv_toolbox.case_io import load_case
from vv_toolbox.surface_neck_loft import build_surface_neck_loft

ROOT=Path(__file__).resolve().parents[1]


def main():
    path=ROOT/'exports/atlas-case-inspection/all-arterial.snapshot.json'
    before=path.read_bytes()
    case,revision=load_case(path)
    out=ROOT/'exports/surface-neck-loft'
    out.mkdir(exist_ok=True)
    reports=[]
    fig=plt.figure(figsize=(11,5))
    for i,name in enumerate(['mca-saccular-grid-recheck-3000000.json','left-mca-saccular-frame.json']):
        spec=json.loads((ROOT/'docs/evidence'/name).read_text())['specification']
        if spec['case_revision']!=revision:
            raise ValueError('stale source')
        v,f,meta=build_surface_neck_loft(case,spec,ray_half_span_mm=1.,ray_step_mm=.05)
        artifact=out/(spec['parameters']['edge_id'].replace(':','-')+'.npz')
        np.savez_compressed(artifact,vertices_mm=v,faces=f,metadata=np.array(json.dumps(meta)))
        meta['artifact_sha256']=hashlib.sha256(artifact.read_bytes()).hexdigest()
        reports.append(meta)
        neck=spec['neck']
        basis=np.column_stack([neck[k] for k in ('width_axis','depth_axis','normal')])
        local=(v-np.asarray(neck['center_mm']))@basis
        ax=fig.add_subplot(1,2,i+1,projection='3d')
        ax.plot_trisurf(local[:,0],local[:,1],local[:,2],triangles=f,
                       color='#c84c59',linewidth=0,alpha=.85)
        closed=np.r_[np.arange(64),0]
        ax.plot(*local[closed].T,color='#162d50',linewidth=2)
        ax.set(title=spec['parameters']['edge_id']+' — open at neck',
               xlabel='Width (mm)',ylabel='Depth (mm)',zlabel='Normal height (mm)')
        ax.set_box_aspect(np.ptp(local,axis=0))
    fig.suptitle('Surface-following sac patch; parent union and smooth junction NOT RUN')
    fig.tight_layout()
    fig.savefig(out/'patches.png',dpi=150)
    plt.close(fig)
    report=dict(case_revision=revision,input_unchanged=before==path.read_bytes(),results=reports,
                figure_sha256=hashlib.sha256((out/'patches.png').read_bytes()).hexdigest(),
                app_applied=False)
    if not report['input_unchanged']:
        raise ValueError('source changed')
    (ROOT/'docs/evidence/surface-neck-loft-inspection.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps([dict(edge_id=r['attachment']['edge_id'],triangles=r['triangle_count'],
        parent_interior_vertices=r['parent_interior_vertex_count'],checks=r['checks']) for r in reports]))


if __name__=='__main__':
    main()
