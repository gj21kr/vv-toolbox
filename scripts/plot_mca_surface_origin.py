"""Orthographic triangle projections colored by retained source labels."""
import hashlib
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.patches import Patch
import numpy as np

ROOT=Path(__file__).resolve().parents[1]


def main():
    report_path=ROOT/'docs/evidence/mca-surface-origin.json'
    report=json.loads(report_path.read_text())
    path=ROOT/'exports/mca-surface-origin/surface.npz'
    if hashlib.sha256(path.read_bytes()).hexdigest()!=report['artifact_sha256']:
        raise ValueError('surface hash mismatch')
    spec=json.loads((ROOT/'docs/evidence/regularized-mca-sac.json').read_text())['specification']
    with np.load(path,allow_pickle=False) as data:
        vertices,faces=data['vertices_mm'],data['faces']
        meta=json.loads(str(data['metadata'].item()))
    neck=spec['neck']
    basis=np.column_stack([neck[k] for k in ('width_axis','depth_axis','normal')])
    local=(vertices-np.array(neck['center_mm']))@basis
    triangles=local[faces];labels=np.array(meta['surface_origin']['face_labels'])
    order=np.argsort(triangles[:,:,1].mean(axis=1))
    palette=np.array(['#bfc6cd','#c94c60','#f0b44c','#853ec7'])
    fig,axes=plt.subplots(1,2,figsize=(12,5))
    for ax in axes:
        ax.add_collection(PolyCollection(triangles[order][:,:,[0,2]],
            facecolors=palette[labels[order]],edgecolors='none'))
        ax.autoscale();ax.set_aspect('equal')
        ax.set(xlabel='Neck width axis (mm)',ylabel='Normal axis (mm)')
    axes[0].set_title('Full candidate: sampled source ownership')
    axes[1].set(xlim=(-3,3),ylim=(-2,3),title='Attachment region')
    fig.legend(handles=[Patch(color=palette[i],label=name) for i,name in enumerate(
        ['Parent','Sac','Mixed / tied','Unsupported'])],loc='upper center',ncol=4)
    fig.tight_layout(rect=(0,0,1,.92))
    image=ROOT/'exports/mca-surface-origin/ownership.png'
    fig.savefig(image,dpi=160);plt.close(fig)
    report['figure_sha256']=hashlib.sha256(image.read_bytes()).hexdigest()
    report_path.write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':
    main()
