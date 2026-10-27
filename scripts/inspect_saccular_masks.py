"""Inspect whole and finer ROI masks of the synthetic sac engineering fixture."""
import hashlib
import json
import argparse
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
import numpy as np

from inspect_saccular_candidate import fixture
from vv_toolbox.saccular_masks import build_saccular_masks
from vv_toolbox.volume_cli import save_volume

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,default=ROOT/'exports/saccular-mask-inspection')
    args=parser.parse_args()
    case,spec=fixture()
    grids={
        'whole':dict(shape_zyx=[9,12,27],spacing_xyz_mm=[1,1,1],
                     origin_xyz_mm=[-3,-3,-4],frame_id='fixture'),
        'roi':dict(shape_zyx=[11,16,13],spacing_xyz_mm=[.5,.5,.5],
                   origin_xyz_mm=[7,.5,-2.5],frame_id='fixture')}
    out=args.output.resolve()
    if not out.is_relative_to((ROOT/'exports').resolve()):
        raise ValueError('inspection output must be inside exports')
    out.mkdir(parents=True,exist_ok=True)
    results={}
    for name,grid in grids.items():
        volume,labels,meta=build_saccular_masks(case,spec,surface_spacing_mm=.15,
            grid_config=grid,coverage='whole' if name=='whole' else 'sac_roi')
        path=out/f'{name}.npz'
        save_volume(path,volume,lesion_labels=labels,lesion_metadata=meta)
        results[name]=(volume,labels,meta,hashlib.sha256(path.read_bytes()).hexdigest())
    fig,axes=plt.subplots(1,2,figsize=(12,5))
    for ax,(name,(volume,labels,meta,digest)) in zip(axes,results.items()):
        g=volume.grid
        z=int(round(-g.origin_xyz_mm[2]/g.spacing_xyz_mm[2]))
        values=volume.foreground[z].astype(int)+(labels[z]>0).astype(int)
        x,y,_=g.origin_xyz_mm;sx,sy,_=g.spacing_xyz_mm
        ax.imshow(values,origin='lower',interpolation='nearest',vmin=0,vmax=2,
            cmap=ListedColormap(['#ffffff','#bc4d58','#f4bc42']),
            extent=[x-sx/2,x+(g.shape_zyx[2]-.5)*sx,y-sy/2,y+(g.shape_zyx[1]-.5)*sy])
        ax.set(xlabel='LPS X (mm)',ylabel='LPS Y (mm)',title=f'{name}: {sx} mm voxels, Z = 0 mm')
        ax.set_aspect('equal')
    fig.suptitle('Synthetic candidate: red lumen, yellow sac/added-neck label; anatomy labels unknown')
    fig.tight_layout();fig.savefig(out/'masks.png',dpi=150);plt.close(fig)
    report=dict(status='CANDIDATE',fixture='straight parent engineering fixture, no atlas/patient data',
        outputs={name:dict(archive=(out/f'{name}.npz').relative_to(ROOT).as_posix(),sha256=result[3],
                          metadata=result[2]) for name,result in results.items()},
        figure_sha256=hashlib.sha256((out/'masks.png').read_bytes()).hexdigest())
    (ROOT/'docs/evidence/saccular-mask-inspection.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({name:r[2]['voxel_counts'] for name,r in results.items()}))


if __name__=='__main__':
    main()
