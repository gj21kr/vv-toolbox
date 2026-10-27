"""Measure native sections normal to the corrected path near residual contact."""
import hashlib
import json
from pathlib import Path
import numpy as np
import trimesh
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from vv_toolbox.atlas import load_atlas
from vv_toolbox.case_io import load_case
from recenter_testicular_candidate import area_centroid

ROOT=Path(__file__).resolve().parents[1]


def section_metrics(xy):
    center=area_centroid(xy)
    a,b=xy[:-1],xy[1:]
    area=abs(float(np.sum(a[:,0]*b[:,1]-b[:,0]*a[:,1])))/2
    d=b-a;norm=np.sum(d*d,axis=1)
    if np.any(norm<=0):raise ValueError('degenerate contour intervals')
    t=np.clip(np.sum((center-a)*d,axis=1)/norm,0,1)
    minimum=float(np.linalg.norm(a+t[:,None]*d-center,axis=1).min())
    return dict(area_mm2=area,area_equivalent_radius_mm=float(np.sqrt(area/np.pi)),
                centroid_uv_mm=center.tolist(),centroid_offset_mm=float(np.linalg.norm(center)),
                minimum_centroid_boundary_distance_mm=minimum,
                maximum_centroid_vertex_distance_mm=float(np.linalg.norm(xy-center,axis=1).max()))


def main():
    path=ROOT/'exports/synthetic-testicular-recentered/case.snapshot.json'
    raw=path.read_bytes();case,revision=load_case(path)
    input_path=ROOT/'docs/evidence/testicular-source-correction.json'
    input_raw=input_path.read_bytes();prior=json.loads(input_raw)
    if revision!=prior['case_revision']:raise ValueError('stale corrected case')
    atlas=load_atlas()
    if atlas.metadata['sha256']!=next(s['sha256'] for s in case['sources'] if s['id']=='bp3d'):
        raise ValueError('source differs')
    mapping=[('R-EIA-retained','FJ3567'),('FJ3617:e0','FJ3617')]
    indices=prior['target_pair_complete_bounds'][1]['intervals']
    fig,axes=plt.subplots(2,5,figsize=(17,7));rows=[]
    for row,((edge_id,source_id),interval) in enumerate(zip(mapping,indices)):
        edge=next(e for e in case['edges'] if e['id']==edge_id)
        part=next(p for p in atlas.meshes if p['id']==source_id)
        mesh=trimesh.Trimesh(part['vertices'],part['faces'],process=False)
        p=np.array(edge['centerline_mm']);arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))]
        for col,index in enumerate(range(interval-2,interval+3)):
            if not 0<index<len(p)-1:raise ValueError('inspection window touches endpoint')
            low=max(0,arc[index]-2);high=min(arc[-1],arc[index]+2)
            normal=np.array([np.interp(high,arc,p[:,k])-np.interp(low,arc,p[:,k]) for k in range(3)])
            normal/=np.linalg.norm(normal)
            basis=np.eye(3)[int(np.argmin(abs(normal)))];u=np.cross(normal,basis);u/=np.linalg.norm(u)
            v=np.cross(normal,u)
            section=mesh.section(plane_origin=p[index],plane_normal=normal)
            contours=[] if section is None else section.discrete
            if len(contours)!=1:raise ValueError('nonunique native section')
            xy=(contours[0]-p[index])@np.array([u,v]).T
            metrics=section_metrics(xy);radius=edge['radii_mm'][index]
            ax=axes[row,col];ax.plot(xy[:,0],xy[:,1],color='firebrick')
            ax.add_patch(Circle((0,0),radius,fill=False,color='royalblue',linestyle=':'))
            ax.plot(*metrics['centroid_uv_mm'],'k+');ax.plot(0,0,'bo',markersize=3)
            ax.set_aspect('equal');ax.autoscale_view();ax.grid(alpha=.2)
            ax.set(title=f'{source_id} #{index}\nr={radius:.3f}; area-r={metrics["area_equivalent_radius_mm"]:.3f}',xlabel='u (mm)',ylabel='v (mm)')
            rows.append(dict(edge_id=edge_id,source_id=source_id,index=index,center_mm=p[index].tolist(),
                normal=normal.tolist(),tangent_chord_half_length_mm=2.,stored_radius_mm=radius,
                source_contour_uv_mm=xy.tolist(),metrics=metrics,
                radius_to_area_equivalent_ratio=radius/metrics['area_equivalent_radius_mm']))
    fig.suptitle('Red: native perpendicular section / blue: stored radius at path / +: native area centroid')
    fig.tight_layout();out=ROOT/'exports/iliac-normal-sections';out.mkdir(parents=True,exist_ok=True)
    figure=out/'sections.png';fig.savefig(figure,dpi=140);plt.close(fig)
    if path.read_bytes()!=raw or input_path.read_bytes()!=input_raw:raise ValueError('input changed')
    report=dict(schema='vv-toolbox.iliac-normal-sections/1',case_revision=revision,
        source_archive_sha256=atlas.metadata['sha256'],input_report_sha256=hashlib.sha256(input_raw).hexdigest(),
        sections=rows,figure=dict(path=figure.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(figure.read_bytes()).hexdigest()),
        inputs_unchanged=True,anatomical_acceptance='UNKNOWN',
        limitation='Local sections in planes normal to a 4 mm path chord; not an independently annotated vessel axis or a global lumen fit.')
    (ROOT/'docs/evidence/iliac-normal-sections.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps([dict(edge_id=r['edge_id'],index=r['index'],radius_ratio=r['radius_to_area_equivalent_ratio'],
                          centroid_offset_mm=r['metrics']['centroid_offset_mm']) for r in rows]))


if __name__=='__main__':main()
