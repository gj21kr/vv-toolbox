"""Source opening inspection and explicit synthetic arch anchor candidate."""
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.path import Path as PlotPath
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np
import trimesh

from vv_toolbox.atlas import load_atlas
from vv_toolbox.case_io import case_digest


def project(point, points):
    delta = np.diff(points, axis=0)
    fractions = np.clip(np.sum((point-points[:-1])*delta, axis=1)/np.sum(delta*delta, axis=1), 0, 1)
    positions = points[:-1]+fractions[:, None]*delta
    index = int(np.argmin(np.linalg.norm(positions-point, axis=1)))
    return index, float(fractions[index]), positions[index]


def main():
    root = Path(__file__).resolve().parents[1]
    source_path = root/'exports/atlas-case-inspection/all-arterial-case.json'
    case = json.loads(source_path.read_text())
    inventory = json.loads((root/'docs/evidence/access-route-endpoints.json').read_text())
    if case_digest(case) != inventory['source_case_canonical_sha256']:
        raise ValueError('source case changed')
    atlas = load_atlas()
    if atlas.metadata['sha256'] != inventory['source_sha256']:
        raise ValueError('atlas archive changed')
    parts = {m['id']: m for m in atlas.meshes if m['id'] in ('FJ3411','FJ3483')}
    meshes = {pid: trimesh.Trimesh(vertices=m['vertices'], faces=m['faces'], process=False) for pid,m in parts.items()}
    edges = {e['id']: e for e in case['edges']}
    arch, cca = edges['FJ3411:e0'], edges['FJ3483:e0']
    ap, cp = np.array(arch['centerline_mm']), np.array(cca['centerline_mm'])
    child_arc=np.r_[0.,np.cumsum(np.linalg.norm(np.diff(cp,axis=0),axis=1))]
    child_direction=np.array([np.interp(5.,child_arc,cp[:,k]) for k in range(3)])-cp[0]
    child_direction/=np.linalg.norm(child_direction)
    boundary_rows, rings = [], []
    for polygon in meshes['FJ3483'].outline().discrete:
        if len(polygon)<4 or not np.allclose(polygon[0],polygon[-1]):
            raise ValueError('CCA boundary is not a closed ring')
        ring = polygon[:-1]
        center = ring.mean(0)
        _,_,vh = np.linalg.svd(ring-center, full_matrices=False)
        normal = vh[-1]
        area = float(np.linalg.norm(np.cross(ring-center,np.roll(ring,-1,axis=0)-center).sum(0))/2)
        boundary_rows.append(dict(index=len(rings),vertex_count=len(ring),center_mm=center.tolist(),
            normal=normal.tolist(),planarity_max_mm=float(np.max(np.abs((ring-center)@normal))),
            projected_area_mm2=area,equivalent_radius_mm=float(np.sqrt(area/np.pi)),
            normal_alignment_with_child=abs(float(normal@child_direction)),
            signed_axial_distance_from_start_mm=float((center-cp[0])@child_direction),
            distance_to_start_mm=float(np.linalg.norm(center-cp[0])),distance_to_end_mm=float(np.linalg.norm(center-cp[-1]))))
        rings.append(ring)
    if len(rings)<2:
        raise ValueError('expected separate CCA terminal boundaries')
    # Boundary extraction also returns side cracks and degenerate backtracking
    # paths. A nearest ring alone picked a nonplanar side hole in this source.
    candidates=[r for r in boundary_rows if r['projected_area_mm2']>1.
        and r['planarity_max_mm']<.25*r['equivalent_radius_mm']
        and r['normal_alignment_with_child']>.8
        and r['signed_axial_distance_from_start_mm']<0]
    if len(candidates)!=1:
        raise ValueError('proximal terminal opening is ambiguous under fixed geometric criteria')
    proximal=candidates[0]
    ring = rings[proximal['index']]
    center, normal = np.array(proximal['center_mm']), np.array(proximal['normal'])
    if normal@(cp[1]-cp[0])<0:
        normal = -normal
    u=np.cross(normal,[1.,0.,0.]);u/=np.linalg.norm(u)
    v=np.cross(normal,u)
    basis=np.column_stack([u,v])
    i,t,anchor = project(center,ap)
    length = np.linalg.norm(np.diff(ap,axis=0),axis=1)
    arc = float(length[:i].sum()+t*length[i])
    radius = float(np.interp(t,[0,1],arch['radii_mm'][i:i+2]))
    # Every opening vertex is compared to the actual arch triangles; no repair.
    closest, distances, triangles = trimesh.proximity.closest_point_naive(meshes['FJ3411'],ring)
    sections=[]
    for offset in [-3.,-1.,0.,1.,3.,5.]:
        origin=center+normal*offset
        row=dict(offset_mm=offset,origin_mm=origin.tolist(),normal=normal.tolist(),parts={})
        for pid,mesh in meshes.items():
            section=mesh.section(plane_origin=origin,plane_normal=normal)
            lines=[] if section is None else section.discrete
            row['parts'][pid]=[dict(closed=bool(np.allclose(p[0],p[-1])),points_mm=p.tolist()) for p in lines]
        arch_polygons=[PlotPath((np.array(p['points_mm'])-origin)@basis) for p in row['parts']['FJ3411'] if p['closed']]
        child_points=[np.array(p['points_mm'])[:-1] for p in row['parts']['FJ3483'] if p['closed']]
        if child_points:
            xy=(np.concatenate(child_points)-origin)@basis
            inside=np.any([p.contains_points(xy) for p in arch_polygons],axis=0) if arch_polygons else np.zeros(len(xy),bool)
            row['cca_section_vertices_inside_arch_section']=dict(inside=int(inside.sum()),total=len(xy),
                scope='2D sampled section vertices, not full mesh volume or validated lumen')
        sections.append(row)
    candidate=dict(status='synthetic_estimate_candidate',parent_edge_id=arch['id'],interval_index=i,
        fraction=t,position_mm=anchor.tolist(),radius_mm=radius,arc_from_start_mm=arc,
        arc_to_end_mm=float(length.sum()-arc),child_edge_id=cca['id'],child_endpoint='start',
        child_position_mm=cp[0].tolist(),child_radius_mm=float(cca['radii_mm'][0]),
        opening_center_mm=center.tolist(),opening_to_anchor_mm=float(np.linalg.norm(center-anchor)),
        child_endpoint_to_anchor_mm=float(np.linalg.norm(cp[0]-anchor)),
        selection_basis='Project the unique planar, transverse, proximal CCA boundary-ring centroid onto source arch polyline after inspecting all boundary paths and both source meshes. Reject nearest nonplanar side hole. This is a synthetic anchor, not an anatomical origin or earlier first capsule witness.',
        requires_parent_split=True,anatomical_approval='UNKNOWN',source_graph_connection=False)
    out=root/'exports/arch-carotid-junction';out.mkdir(parents=True,exist_ok=True)
    fig=plt.figure(figsize=(15,5))
    for panel,(elev,azim) in enumerate([(15,-90),(15,0),(75,-90)],1):
        ax=fig.add_subplot(1,3,panel,projection='3d')
        for pid,color in [('FJ3411','#d94d51'),('FJ3483','#db942b')]:
            mesh=meshes[pid]
            ax.add_collection3d(Poly3DCollection(mesh.triangles,facecolor=color,edgecolor='none',alpha=.2))
        ax.plot(*ap.T,color='#7e161a',lw=1.5)
        ax.plot(*cp.T,color='#8b580a',lw=1.5)
        closed=np.vstack([ring,ring[0]])
        ax.plot(*closed.T,color='cyan',lw=2)
        ax.scatter(*anchor,color='blue',s=30)
        ax.plot(*np.vstack([anchor,center,cp[0]]).T,color='blue',lw=2)
        ax.set(xlim=(center[0]-30,center[0]+30),ylim=(center[1]-30,center[1]+30),zlim=(center[2]-30,center[2]+30))
        ax.set_box_aspect((1,1,1));ax.view_init(elev,azim)
        ax.set_title('Source meshes + candidate (not approved)')
        ax.set_xlabel('LPS X mm');ax.set_ylabel('LPS Y mm');ax.set_zlabel('LPS Z mm')
    fig.tight_layout();figure=out/'source-opening-candidate.png';fig.savefig(figure,dpi=140);plt.close(fig)
    fig,axes=plt.subplots(2,3,figsize=(12,8))
    for ax,row in zip(axes.flat,sections):
        origin=np.array(row['origin_mm'])
        for pid,color in [('FJ3411','#c73540'),('FJ3483','#dc9421')]:
            for polygon in row['parts'][pid]:
                xy=(np.array(polygon['points_mm'])-origin)@basis
                ax.plot(xy[:,0],xy[:,1],color=color,label=pid)
        ax.set_title('Offset '+str(row['offset_mm'])+' mm');ax.set_aspect('equal');ax.grid(alpha=.3)
        ax.set_xlabel('Plane U mm');ax.set_ylabel('Plane V mm')
    fig.suptitle('Native source sections: red arch, gold left CCA; no mesh repair')
    fig.tight_layout();section_figure=out/'source-sections.png';fig.savefig(section_figure,dpi=140);plt.close(fig)
    report=dict(schema='vv-toolbox.arch-carotid-junction/1',status='PASS',scope='source geometry inspection and synthetic anchor declaration only',
        source_case_revision=case_digest(case),source_case_sha256=hashlib.sha256(source_path.read_bytes()).hexdigest(),
        source_archive_sha256=atlas.metadata['sha256'],source_preview_sha256=inventory['preview_sha256'],
        source_parts=[p for p in atlas.metadata['parts'] if p['id'] in parts],
        mesh_checks={pid:dict(watertight=bool(m.is_watertight),vertices=len(m.vertices),triangles=len(m.faces)) for pid,m in meshes.items()},
        cca_boundary_rings=boundary_rows,selected_proximal_ring=proximal['index'],
        opening_selection_criteria=dict(projected_area_greater_than_mm2=1.,planarity_max_less_than_equivalent_radius_fraction=.25,
            normal_alignment_greater_than=.8,signed_axial_distance_from_start_less_than_mm=0.,
            unique_candidate_required=True,clinical_thresholds=False),
        opening_vertex_to_arch_triangle=dict(min_mm=float(distances.min()),max_mm=float(distances.max()),
            mean_mm=float(distances.mean()),distances_mm=distances.tolist(),closest_points_mm=closest.tolist(),triangle_ids=triangles.tolist(),
            interpretation='Boundary vertex distances only; not an exhaustive triangle collision or lumen continuity test.'),
        sections=sections,candidate=candidate,source_graph_modified=False,anatomical_connection='UNKNOWN',
        section_figure=dict(path=str(section_figure.relative_to(root)),sha256=hashlib.sha256(section_figure.read_bytes()).hexdigest()),
        figure=dict(path=str(figure.relative_to(root)),sha256=hashlib.sha256(figure.read_bytes()).hexdigest()))
    (root/'docs/evidence/arch-carotid-junction.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps(dict(candidate=candidate,rings=boundary_rows,distances=report['opening_vertex_to_arch_triangle']['mean_mm'])))


if __name__=='__main__':
    main()
