"""Inspect native BCT/RCCA/subclavian boundaries; declare synthetic-only anchors."""
import hashlib
import json
from pathlib import Path
import numpy as np
import trimesh
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.path import Path as PlotPath
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from vv_toolbox.atlas import load_atlas
from vv_toolbox.case_io import case_digest

ROOT=Path(__file__).resolve().parents[1]
IDS=['FJ3417','FJ3564','FJ3579']
COLORS=['#c93440','#dd9a20','#365db5']


def crossings(a,b):
    count=0
    cross=lambda x,y: x[0]*y[1]-x[1]*y[0]
    for p,q in zip(a[:-1],a[1:]):
        u=q-p
        for c,d in zip(b[:-1],b[1:]):
            v=d-c;det=cross(u,v)
            if abs(det)<1e-12:
                continue
            s,t=cross(c-p,v)/det,cross(c-p,u)/det
            if 0<s<1 and 0<t<1:
                count+=1
    return count


def endpoint(edge, end):
    p=np.array(edge['centerline_mm'])
    if end=='end':
        p=p[::-1]
    arc=np.r_[0.,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))]
    inward=np.array([np.interp(min(5.,arc[-1]),arc,p[:,k]) for k in range(3)])-p[0]
    inward/=np.linalg.norm(inward)
    i=0 if end=='start' else len(edge['centerline_mm'])-2
    f=0. if end=='start' else 1.
    return dict(edge_id=edge['id'],endpoint=end,interval_index=i,fraction=f,
        position_mm=p[0].tolist(),radius_mm=float(edge['radii_mm'][0 if end=='start' else -1]),
        outward_unit_direction=(-inward).tolist(),direction_method='5 mm source polyline chord pointing out of selected endpoint')


def main():
    source=ROOT/'exports/atlas-case-inspection/all-arterial-case.json'
    raw=source.read_bytes();case=json.loads(raw)
    inventory=json.loads((ROOT/'docs/evidence/access-route-endpoints.json').read_text())
    if case_digest(case)!=inventory['source_case_canonical_sha256']:
        raise ValueError('case fingerprint mismatch')
    atlas=load_atlas()
    if atlas.metadata['sha256']!=inventory['source_sha256']:
        raise ValueError('archive fingerprint mismatch')
    parts={m['id']:m for m in atlas.meshes if m['id'] in IDS}
    meshes={pid:trimesh.Trimesh(vertices=p['vertices'],faces=p['faces'],process=False) for pid,p in parts.items()}
    edges={pid:next(e for e in case['edges'] if e['id']==pid+':e0') for pid in IDS}
    records=[]
    for pid in IDS:
        edge=edges[pid];boundaries=[]
        for index,path in enumerate(meshes[pid].outline().discrete):
            closed=bool(np.allclose(path[0],path[-1]));p=path[:-1] if closed else path
            c=p.mean(0);_,_,vh=np.linalg.svd(p-c,full_matrices=False);n=vh[-1]
            area=float(np.linalg.norm(np.cross(p-c,np.roll(p,-1,axis=0)-c).sum(0))/2) if closed else None
            boundaries.append(dict(index=index,closed=closed,vertices_mm=p.tolist(),center_mm=c.tolist(),normal=n.tolist(),
                projected_area_mm2=area,planarity_max_mm=float(np.max(np.abs((p-c)@n))),
                distance_to_start_mm=float(np.linalg.norm(c-np.array(edge['centerline_mm'][0]))),
                distance_to_end_mm=float(np.linalg.norm(c-np.array(edge['centerline_mm'][-1])))))
        records.append(dict(part_id=pid,name=parts[pid]['name'],watertight=bool(meshes[pid].is_watertight),
            vertices=len(meshes[pid].vertices),triangles=len(meshes[pid].faces),
            endpoints=[endpoint(edge,'start'),endpoint(edge,'end')],boundaries=boundaries))
    # Explicit source extraction ends selected from known named parts and source
    # superior/inferior extent, then compared below. Never use first capsule hit.
    anchors=[endpoint(edges['FJ3417'],'start'),endpoint(edges['FJ3564'],'end'),endpoint(edges['FJ3579'],'end')]
    center=np.array(anchors[0]['position_mm'])
    sections=[]
    for offset in [-8.,-4.,0.,4.,8.]:
        origin=center+np.array([0.,0.,offset]);row=dict(z_offset_mm=offset,origin_mm=origin.tolist(),normal=[0.,0.,1.],parts={})
        for pid,m in meshes.items():
            s=m.section(plane_origin=origin,plane_normal=[0.,0.,1.])
            row['parts'][pid]=[] if s is None else [dict(closed=bool(np.allclose(p[0],p[-1])),points_mm=p.tolist()) for p in s.discrete]
        comparisons=[]
        for daughter in IDS[1:]:
            for a in row['parts']['FJ3417']:
                for b in row['parts'][daughter]:
                    p,q=np.array(a['points_mm'])[:,:2],np.array(b['points_mm'])[:,:2]
                    if not (a['closed'] and b['closed']):
                        continue
                    comparisons.append(dict(parent='FJ3417',daughter=daughter,
                        daughter_section_centroid_xy=q[:-1].mean(0).tolist(),
                        daughter_vertices_inside_parent=int(PlotPath(p).contains_points(q[:-1]).sum()),
                        daughter_vertex_count=len(q)-1,strict_segment_crossings=crossings(p,q)))
        row['section_comparisons']=comparisons
        sections.append(row)
    distances=[]
    for a in range(3):
        for b in range(a+1,3):
            distances.append(dict(parts=[IDS[a],IDS[b]],endpoint_distance_mm=float(np.linalg.norm(np.array(anchors[a]['position_mm'])-np.array(anchors[b]['position_mm'])))))
    headings=[]
    for child in anchors[1:]:
        chord=np.array(child['position_mm'])-np.array(anchors[0]['position_mm'])
        chord/=np.linalg.norm(chord)
        parent_cos=float(np.array(anchors[0]['outward_unit_direction'])@chord)
        child_cos=float(np.array(child['outward_unit_direction'])@(-chord))
        headings.append(dict(parent=anchors[0]['edge_id'],daughter=child['edge_id'],
            parent_outward_toward_child_cosine=parent_cos,
            child_outward_toward_parent_cosine=child_cos,
            straight_bridge_accepted=False,
            reason=('Short chord opposes source outward directions; a direct Hermite bridge can introduce a tiny loop.' if min(parent_cos,child_cos)<0 else
                    'Directions are broadly aligned, but shared three-way junction and source-overlap surface remain unvalidated; no independent bridge acceptance.')))
    out=ROOT/'exports/brachiocephalic-junction';out.mkdir(parents=True,exist_ok=True)
    figures=[]
    fig=plt.figure(figsize=(15,5))
    for k,(elev,azim) in enumerate([(10,-90),(10,0),(80,-90)]):
        ax=fig.add_subplot(1,3,k+1,projection='3d')
        for pid,color,anchor in zip(IDS,COLORS,anchors):
            m=meshes[pid];p=np.array(edges[pid]['centerline_mm'])
            ax.add_collection3d(Poly3DCollection(m.triangles,facecolor=color,alpha=.22,edgecolors='none'))
            ax.plot(*p.T,color=color,lw=2);ax.scatter(*anchor['position_mm'],color=color,s=35)
        ax.set(xlim=(center[0]-25,center[0]+25),ylim=(center[1]-25,center[1]+25),zlim=(center[2]-25,center[2]+25))
        ax.set_box_aspect((1,1,1));ax.view_init(elev,azim);ax.set_title('Native meshes and extraction ends')
        ax.set_xlabel('LPS X mm');ax.set_ylabel('LPS Y mm');ax.set_zlabel('LPS Z mm')
    fig.tight_layout();p=out/'source-junction.png';fig.savefig(p,dpi=140);plt.close(fig);figures.append(p)
    fig,axes=plt.subplots(1,5,figsize=(20,4))
    for ax,row in zip(axes,sections):
        for pid,color in zip(IDS,COLORS):
            for line in row['parts'][pid]:
                p=np.array(line['points_mm']);ax.plot(p[:,0],p[:,1],color=color)
        ax.set_title('Z '+str(row['origin_mm'][2])+' mm');ax.set_aspect('equal');ax.grid(alpha=.3)
        ax.set_xlim(center[0]-20,center[0]+20);ax.set_ylim(center[1]-20,center[1]+20)
        ax.set_xlabel('LPS X mm');ax.set_ylabel('LPS Y mm')
    fig.suptitle('Native axial sections: red BCT, gold RCCA, blue subclavian; fixed local crop, no repair')
    fig.tight_layout();p=out/'source-sections.png';fig.savefig(p,dpi=140);plt.close(fig);figures.append(p)
    report=dict(schema='vv-toolbox.brachiocephalic-junction/1',status='PASS',scope='source boundary and section inspection; synthetic anchor candidate only',
        source_case_revision=case_digest(case),source_case_sha256=hashlib.sha256(raw).hexdigest(),
        source_archive_sha256=atlas.metadata['sha256'],source_preview_sha256=inventory['preview_sha256'],
        source_parts=[p for p in atlas.metadata['parts'] if p['id'] in IDS],parts=records,sections=sections,
        section_comparison_scope='2D contour vertex inclusion and strict segment crossings; not 3D lumen connectivity. Remote subclavian recuts retained in JSON, fixed local crop in PNG.',
        candidate=dict(status='synthetic_estimate_candidate',parent=anchors[0],daughters=anchors[1:],
            parent_split_required=False,daughter_split_required=False,
            selection_basis='Explicit superior BCT extraction start and inferior RCCA / medial subclavian extraction ends, inspected against native mesh extent and axial sections. No first-contact or nearest-only origin inference.',
            uncertainty='Source open surfaces and overlapping separate parts do not establish a unified lumen. Endpoint coordinates locate an overlap neighborhood only, not an accepted direct bridge.',
            direct_bridge_accepted=False,required_construction='Review terminal-tail trimming/local junction remesh or explicit endpoint coalescence in synthetic model; validate radius, direction, lumen and collisions.',
            anatomical_approval='UNKNOWN'),endpoint_distances=distances,source_graph_modified=False,
        endpoint_heading_checks=headings,
        figures=[dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in figures])
    (ROOT/'docs/evidence/brachiocephalic-junction.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps(dict(anchors=anchors,distances=distances,boundary_counts={r['part_id']:len(r['boundaries']) for r in records})))


if __name__=='__main__':
    main()
