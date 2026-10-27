"""Generate an explicitly synthetic sac fixture and inspect actual output triangles."""
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import trimesh

from vv_toolbox.saccular import saccular_spec
from vv_toolbox.saccular_surface import build_saccular_candidate
from vv_toolbox.voxel_output import Grid, Surface, voxelize

ROOT = Path(__file__).resolve().parents[1]


def fixture():
    case = dict(schema='vv-toolbox.case/1', case_id='sac-straight-parent-fixture',
        base_model_id='engineering-fixture', model_kind='synthetic', split='unassigned',
        generation=dict(seed=0, generator_version='straight-parent-fixture-1', config={}),
        frame=dict(id='fixture', units='mm', axes='LPS', origin='arbitrary engineering origin'),
        sources=[dict(id='fixture',sha256='a'*64,license_ref='generated fixture; no atlas')],
        nodes={n:dict(kind='scope_boundary', evidence_status='synthetic_estimate', position_mm=p)
               for n,p in [('a',[0,0,0]),('b',[20,0,0])]},
        edges=[dict(id='e', start='a', end='b', source_ids=['fixture'],
                    geometry_kind='estimated', evidence_status='synthetic_estimate',
                    anatomy=dict(artery='ACA',side='L',segment='unresolved',branch_id='e'),
                    centerline_mm=[[0,0,0],[20,0,0]], radii_mm=[2,2])])
    spec = saccular_spec(case, lesion_id='manual-sac', edge_id='e', region='aca',
        station_mm=10, neck_center_mm=[10,2,0], outward_normal=[0,1,0], width_direction=[1,0,0],
        neck_width_mm=2, neck_depth_mm=1, height_perpendicular_mm=5,
        dome_width_mm=4, dome_depth_mm=3, blending_extent_mm=.5)
    return case, spec


def main():
    case, spec = fixture()
    v,f,meta = build_saccular_candidate(case,spec,spacing_mm=.15)
    out = ROOT/'exports/saccular-neck-preservation'
    out.mkdir(parents=True,exist_ok=True)
    np.savez_compressed(out/'surface.npz',vertices_mm=v,faces=f,metadata=np.array(json.dumps(meta)))
    (out/'specification.json').write_text(json.dumps(spec,indent=2)+'\n')
    mesh = trimesh.Trimesh(vertices=v,faces=f,process=False)
    section = mesh.section(plane_origin=[10,0,0],plane_normal=[1,0,0])
    neck_section = mesh.section(plane_origin=[10,2,0],plane_normal=[0,1,0])
    if neck_section is None or len(neck_section.discrete) != 1:
        raise RuntimeError('Neck section is not a single contour')
    measured_neck = np.ptp(neck_section.discrete[0],axis=0)[[0,2]].tolist()
    grid = Grid((3,29,3),(.25,.25,.25),(9.75,-.25,-.25),'fixture')
    mask = voxelize([Surface(1,0,'estimated',v,f,'fixture','generated sac candidate')],grid)
    channel = bool(mask.foreground[1,1:27,1].all())
    if not channel or section is None or len(section.discrete) != 1:
        raise RuntimeError('Independent output mesh inspection failed')
    fig = plt.figure(figsize=(12,5))
    ax = fig.add_subplot(121,projection='3d')
    ax.plot_trisurf(v[:,0],v[:,1],v[:,2],triangles=f,color='#c84c59',linewidth=0,alpha=1)
    ax.set(xlabel='X (mm)',ylabel='Y (mm)',zlabel='Z (mm)',title='Generated union surface')
    ax.set_box_aspect(np.ptp(v,axis=0));ax.view_init(elev=30,azim=-65)
    ax = fig.add_subplot(122)
    for curve in section.discrete:
        ax.plot(curve[:,1],curve[:,2],color='#c84c59')
    ax.axvline(2,color='black',ls='--',label='Declared neck plane')
    ax.plot(np.arange(0,6.5,.25),np.zeros(26),'.',color='#188782',label='Mesh-derived occupied channel voxels')
    ax.set(xlabel='Y (mm)',ylabel='Z (mm)',title='Actual triangle section at X = 10 mm')
    ax.set_aspect('equal');ax.legend(fontsize=8)
    fig.suptitle('Synthetic engineering fixture — not anatomical or clinical validation')
    fig.tight_layout();fig.savefig(out/'inspection.png',dpi=160);plt.close(fig)
    report = dict(**meta, vertices=len(v),triangles=len(f),
        independent_mesh_section_loops=len(section.discrete),
        independent_mesh_voxel_central_channel='PASS' if channel else 'FAIL',
        fixture='straight circular parent with manually specified sidewall sac; not atlas',
        actual_tip_y_mm=float(v[:,1].max()), requested_tip_y_mm=7,
        actual_neck_width_depth_mm=measured_neck, requested_neck_width_depth_mm=[2,1],
        measurement_note='Same declared plane and triangle contour axis spans; engineering tolerance fixed at two grid spacings (0.30 mm).',
        neck_dimension_tolerance_mm=.30,
        neck_dimension_check='PASS' if np.all(np.abs(np.asarray(measured_neck)-[2,1]) <= .30) else 'FAIL',
        surface_sha256=hashlib.sha256((out/'surface.npz').read_bytes()).hexdigest(),
        figure_sha256=hashlib.sha256((out/'inspection.png').read_bytes()).hexdigest())
    (ROOT/'docs/evidence/saccular-neck-preservation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('status','vertices','triangles',
        'independent_mesh_section_loops','independent_mesh_voxel_central_channel','actual_tip_y_mm')}))


if __name__ == '__main__':
    main()
