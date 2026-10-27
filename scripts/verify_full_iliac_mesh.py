"""Conservative cross-component mesh separation certificate and actual sections."""
import hashlib
import json
from pathlib import Path
import numpy as np
import trimesh
from scipy.spatial import cKDTree
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]


def certify_separation(a,b):
    """Positive global centroid-sphere bound proves every triangle pair separate.

    A failed bound is UNKNOWN, never evidence of actual triangle intersection.
    Outside-bounds witnesses additionally rule out whole-component containment.
    """
    ta,tb=a.triangles,b.triangles
    ca,cb=ta.mean(1),tb.mean(1)
    ra=np.linalg.norm(ta-ca[:,None,:],axis=2).max(1)
    rb=np.linalg.norm(tb-cb[:,None,:],axis=2).max(1)
    distances,_=cKDTree(cb).query(ca)
    bound=float(np.min(distances-ra-rb.max()))
    witnesses=[]
    for first,second in ((a,b),(b,a)):
        outside=np.flatnonzero(np.any((first.vertices<second.bounds[0]-1e-8)|
                                      (first.vertices>second.bounds[1]+1e-8),axis=1))
        witnesses.append(None if len(outside)==0 else first.vertices[int(outside[0])].tolist())
    return dict(status='PASS' if bound>1e-8 and all(w is not None for w in witnesses) else 'UNKNOWN',
        triangle_separation_bound_mm=bound,triangle_pair_count=len(ta)*len(tb),
        outside_other_component_bounds_witnesses_mm=witnesses,
        method='nearest triangle centroid distance minus own enclosing radius minus maximum other enclosing radius',
        individual_surface_self_intersection='NOT RUN',
        limitation='Conservative global bound for these two saved meshes only; no anatomical or all-atlas assertion.')


def main():
    path=ROOT/'exports/full-iliac-surface/surface.npz';raw=path.read_bytes()
    prior=json.loads((ROOT/'docs/evidence/full-iliac-surface.json').read_text())
    if prior['surface']['status']!='PASS' or hashlib.sha256(raw).hexdigest()!=prior['surface']['sha256']:
        raise ValueError('surface evidence mismatch')
    data=np.load(path,allow_pickle=False)
    meshes=trimesh.Trimesh(data['vertices_mm'],data['faces'],process=False).split()
    if len(meshes)!=2:raise ValueError('expected two connected surfaces')
    result=certify_separation(*meshes)
    fig,axes=plt.subplots(2,3,figsize=(12,8));sections=[]
    for ax,z in zip(axes.flat,[850.,855.,860.,875.,880.,885.]):
        counts=[]
        for component,(mesh,color) in enumerate(zip(meshes,['firebrick','darkorange'])):
            section=mesh.section(plane_origin=[0,0,z],plane_normal=[0,0,1])
            cs=[] if section is None else section.discrete;counts.append(len(cs))
            for contour in cs:ax.plot(contour[:,0],contour[:,1],color=color)
        ax.set(title=f'Saved mesh Z={z:g} mm',xlabel='L (mm)',ylabel='P (mm)')
        ax.set_aspect('equal');ax.grid(alpha=.2);sections.append(dict(z_mm=z,contour_counts=counts))
    fig.suptitle('Complete source-guided candidate: actual surface cross-sections')
    fig.tight_layout();figure=path.parent/'mesh-sections.png';fig.savefig(figure,dpi=140);plt.close(fig)
    if path.read_bytes()!=raw:raise ValueError('mesh changed')
    report=dict(schema='vv-toolbox.full-iliac-mesh-separation/1',case_revision=prior['case_revision'],
        surface_sha256=hashlib.sha256(raw).hexdigest(),separation=result,
        components=[dict(vertices=len(m.vertices),triangles=len(m.faces),watertight=bool(m.is_watertight),
                         euler_number=int(m.euler_number)) for m in meshes],sections=sections,
        figure=dict(path=figure.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(figure.read_bytes()).hexdigest()),
        input_unchanged=True,anatomical_acceptance='UNKNOWN',default_app_applied=False)
    (ROOT/'docs/evidence/full-iliac-mesh-separation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__':main()
