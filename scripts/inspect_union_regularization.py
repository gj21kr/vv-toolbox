"""Bounded smoothing of the saved right MCA candidate, with rim-distance audit."""
import hashlib
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import trimesh
from vv_toolbox.surface_regularization import regularize_surface

ROOT=Path(__file__).resolve().parents[1]


def rim_distances(mesh,points):
    values=[]
    for start in range(0,len(points),4):
        _,dist,_=trimesh.proximity.closest_point_naive(mesh,points[start:start+4])
        values.extend(dist.tolist())
    return dict(max_mm=max(values),mean_mm=float(np.mean(values)))


def main():
    path=ROOT/'exports/surface-neck-union-refined/surface.npz'
    before=path.read_bytes()
    source=json.loads((ROOT/'docs/evidence/surface-neck-union-refined.json').read_text())
    if hashlib.sha256(before).hexdigest()!=source['artifact_sha256']:
        raise ValueError('input mesh hash mismatch')
    with np.load(path,allow_pickle=False) as data:
        original=data['vertices_mm'].copy()
        faces=data['faces'].copy()
        metadata=json.loads(str(data['metadata'].item()))
    vertices,faces,result=regularize_surface(original,faces,iterations=10,
        max_displacement_mm=.15,max_volume_change_fraction=.02)
    meshes=[trimesh.Trimesh(vertices=v,faces=faces,process=False) for v in (original,vertices)]
    rim=np.array(metadata['attachment']['curve_mm'])
    result['rim_distance_before']=rim_distances(meshes[0],rim)
    result['rim_distance_after']=rim_distances(meshes[1],rim)
    result['rim_distance_limit_mm']=.30
    if result['rim_distance_after']['max_mm']>.30:
        raise ValueError('sampled rim distance limit exceeded')
    result.update(source_artifact_sha256=source['artifact_sha256'],
                  case_revision=metadata['case_revision'],frame=metadata['frame'],
                  attachment=metadata['attachment'],app_applied=False)
    spec=json.loads((ROOT/'docs/evidence/mca-saccular-grid-recheck-3000000.json').read_text())['specification']
    center=np.asarray(spec['neck']['center_mm'])
    basis=np.column_stack([spec['neck'][k] for k in ('width_axis','depth_axis','normal')])
    out=ROOT/'exports/union-regularization'
    out.mkdir(exist_ok=True)
    np.savez_compressed(out/'surface.npz',vertices_mm=vertices,faces=faces,metadata=np.array(json.dumps(result)))
    fig,ax=plt.subplots(figsize=(8,5))
    for mesh,color,name in zip(meshes,['#777777','#c83c50'],['Before','After']):
        section=mesh.section(plane_origin=center,plane_normal=basis[:,1])
        for line in section.discrete:
            local=(line-center)@basis
            ax.plot(local[:,0],local[:,2],color=color,label=name)
    ax.set(xlim=(-6,6),ylim=(-4.5,5.5),xlabel='Width coordinate (mm)',
           ylabel='Normal coordinate (mm)',title='Same triangle section before/after bounded smoothing')
    ax.set_aspect('equal')
    handles,labels=ax.get_legend_handles_labels()
    unique=dict(zip(labels,handles))
    ax.legend(unique.values(),unique.keys())
    fig.tight_layout();fig.savefig(out/'comparison.png',dpi=150);plt.close(fig)
    result.update(input_unchanged=path.read_bytes()==before,
        artifact_sha256=hashlib.sha256((out/'surface.npz').read_bytes()).hexdigest(),
        figure_sha256=hashlib.sha256((out/'comparison.png').read_bytes()).hexdigest())
    if not result['input_unchanged']:
        raise ValueError('input changed')
    (ROOT/'docs/evidence/union-regularization.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('attachment','frame')}))


if __name__=='__main__':
    main()
