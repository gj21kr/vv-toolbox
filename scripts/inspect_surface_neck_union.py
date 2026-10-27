"""Inspect a closed sampled union on the recorded right MCA design."""
import hashlib
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import trimesh
from vv_toolbox.case_io import load_case
from vv_toolbox.surface_neck_union import build_surface_neck_union

ROOT=Path(__file__).resolve().parents[1]


def main():
    path=ROOT/'exports/atlas-case-inspection/all-arterial.snapshot.json'
    before=path.read_bytes()
    case,revision=load_case(path)
    spec=json.loads((ROOT/'docs/evidence/mca-saccular-grid-recheck-3000000.json').read_text())['specification']
    if revision!=spec['case_revision']:
        raise ValueError('stale specification')
    print('Generating right MCA nonplanar union at 0.15 mm',flush=True)
    try:
        v,f,meta=build_surface_neck_union(case,spec,spacing_mm=.15,
                                        ray_half_span_mm=1.,ray_step_mm=.05)
    except ValueError as error:
        report=dict(status='FAIL',case_revision=revision,edge_id=spec['parameters']['edge_id'],
                    reason=str(error),source_unchanged=path.read_bytes()==before,
                    spacing_mm=.15,surface_published=False,app_applied=False)
        (ROOT/'docs/evidence/surface-neck-union-refined.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report))
        return
    out=ROOT/'exports/surface-neck-union-refined'
    out.mkdir(exist_ok=True)
    np.savez_compressed(out/'surface.npz',vertices_mm=v,faces=f,metadata=np.array(json.dumps(meta)))
    neck=spec['neck']
    basis=np.column_stack([neck[k] for k in ('width_axis','depth_axis','normal')])
    local=(v-np.asarray(neck['center_mm']))@basis
    mesh=trimesh.Trimesh(vertices=local,faces=f,process=False)
    section=mesh.section(plane_origin=[0,0,0],plane_normal=[0,1,0])
    fig,ax=plt.subplots(figsize=(8,5))
    if section is not None:
        for curve in section.discrete:
            ax.plot(curve[:,0],curve[:,2],color='#c84c59')
    ax.set(xlabel='Neck width coordinate (mm)',ylabel='Normal coordinate (mm)',
           title='Right MCA sampled union: actual output triangle section')
    ax.set_aspect('equal')
    fig.tight_layout()
    fig.savefig(out/'section.png',dpi=150)
    plt.close(fig)
    report=dict(**meta,vertices=len(v),triangles=len(f),
                section_loops=0 if section is None else len(section.discrete),
                source_unchanged=path.read_bytes()==before,
                artifact_sha256=hashlib.sha256((out/'surface.npz').read_bytes()).hexdigest(),
                figure_sha256=hashlib.sha256((out/'section.png').read_bytes()).hexdigest(),
                app_applied=False)
    if not report['source_unchanged']:
        raise ValueError('source changed')
    (ROOT/'docs/evidence/surface-neck-union-refined.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('status','vertices','triangles','section_loops','checks')}))


if __name__=='__main__':
    main()
