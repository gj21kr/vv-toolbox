"""Compare actual triangle sections in one shared, newly declared neck plane."""
import hashlib
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import trimesh

ROOT=Path(__file__).resolve().parents[1]


def main():
    report_path=ROOT/'docs/evidence/regularized-mca-sac.json'
    report=json.loads(report_path.read_text())
    if report['status']!='CANDIDATE':
        raise ValueError('no generated candidate')
    neck=report['specification']['neck']
    center=np.array(neck['center_mm'])
    basis=np.column_stack([neck[k] for k in ('width_axis','depth_axis','normal')])
    fig,ax=plt.subplots(figsize=(9,6))
    paths=[('union-regularization','union-regularization','Before','#777777'),
           ('regularized-mca-sac','regularized-mca-sac','Regularized baseline','#c83c50')]
    sections=[]
    for folder,evidence,label,color in paths:
        path=ROOT/f'exports/{folder}/surface.npz'
        expected=json.loads((ROOT/f'docs/evidence/{evidence}.json').read_text())['artifact_sha256']
        if hashlib.sha256(path.read_bytes()).hexdigest()!=expected:
            raise ValueError('mesh hash mismatch')
        with np.load(path,allow_pickle=False) as data:
            mesh=trimesh.Trimesh(vertices=data['vertices_mm'],faces=data['faces'],process=False)
        section=mesh.section(plane_origin=center,plane_normal=basis[:,1])
        count=0
        if section is not None:
            for line in section.discrete:
                local=(line-center)@basis
                ax.plot(local[:,0],local[:,2],color=color,label=label if count==0 else None)
                count+=1
        sections.append(dict(label=label,loops=count,artifact_sha256=expected))
    ax.set(xlabel='Shared plane width (mm)',ylabel='Shared plane normal (mm)',
           title='Actual mesh sections; placement frame recomputed after baseline change')
    ax.set_aspect('equal');ax.legend();fig.tight_layout()
    image=ROOT/'exports/regularized-mca-sac/comparison.png'
    fig.savefig(image,dpi=150);plt.close(fig)
    report['section_comparison']=dict(sections=sections,
        plane_origin_mm=center.tolist(),plane_normal=basis[:,1].tolist(),
        figure_sha256=hashlib.sha256(image.read_bytes()).hexdigest(),
        limitation='One plane only; not full surface or neck-dimension acceptance')
    report_path.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')


if __name__=='__main__':
    main()
