"""Inspect actual bilateral iliofemoral source openings; no source repair."""
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np
import trimesh

from vv_toolbox.atlas import load_atlas
from vv_toolbox.case_io import case_digest, load_case


def main():
    root = Path(__file__).resolve().parents[1]
    out = root/'exports/iliofemoral-gaps'; out.mkdir(exist_ok=True, parents=True)
    source_path = root/'exports/atlas-case-inspection/all-arterial-case.json'
    raw = source_path.read_bytes(); case = json.loads(raw)
    inventory = json.loads((root/'docs/evidence/access-route-endpoints.json').read_text())
    parent_path = root/'exports/synthetic-arch-carotid-case/case.snapshot.json'
    parent_raw = parent_path.read_bytes(); parent, revision = load_case(parent_path)
    atlas = load_atlas()
    hashes = {s['id']: s['sha256'] for s in parent['sources']}
    if (case_digest(case) != inventory['source_case_canonical_sha256'] or
            atlas.metadata['sha256'] != inventory['source_sha256'] or
            hashes != {s['id']: s['sha256'] for s in case['sources']}):
        raise ValueError('input source identity mismatch')
    edges = {e['id']: e for e in case['edges']}
    pe = {e['id']: e for e in parent['edges']}
    declarations = [('L','FJ3466','end','FJ2074','start'), ('R','FJ3567','start','FJ2143','end')]
    parts = {m['id']: m for m in atlas.meshes if m['id'] in ['FJ3466','FJ2074','FJ3567','FJ2143']}
    meshes = {pid: trimesh.Trimesh(vertices=m['vertices'], faces=m['faces'], process=False) for pid,m in parts.items()}
    results = []; figures = []
    for side, iliac, iep, femoral, fep in declarations:
        rows = []; chosen = []; fig = plt.figure(figsize=(13, 9))
        ax = fig.add_subplot(121, projection='3d'); secax = fig.add_subplot(122)
        for pid, endpoint, color in [(iliac, iep, 'firebrick'),(femoral,fep,'royalblue')]:
            edge = edges[pid+':e0']
            if pe[edge['id']] != edge:
                raise ValueError('parent target geometry changed')
            p = np.asarray(edge['centerline_mm']); idx, neighbour = (0,1) if endpoint=='start' else (-1,-2)
            outward = p[idx]-p[neighbour]; outward /= np.linalg.norm(outward)
            ar = np.r_[0., np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))]
            inner = 5. if endpoint=='start' else ar[-1]-5.
            tangent = p[idx]-np.array([np.interp(inner,ar,p[:,k]) for k in range(3)])
            tangent /= np.linalg.norm(tangent)
            mesh = meshes[pid]; boundaries = []
            for index, polygon in enumerate(mesh.outline().discrete):
                closed = bool(np.allclose(polygon[0],polygon[-1]))
                ring = polygon[:-1] if closed else polygon
                center = ring.mean(0)
                if len(ring)<3: continue
                _,_,vh = np.linalg.svd(ring-center,full_matrices=False); normal=vh[-1]
                area=float(np.linalg.norm(np.cross(ring-center,np.roll(ring,-1,axis=0)-center).sum(0))/2)
                radius=float(np.sqrt(area/np.pi))
                row=dict(index=index,closed=closed,vertex_count=len(ring),center_mm=center.tolist(),
                         normal=normal.tolist(),projected_area_mm2=area,equivalent_radius_mm=radius,
                         planarity_max_mm=float(np.max(np.abs((ring-center)@normal))),
                         axial_outward_mm=float((center-p[idx])@tangent),
                         alignment=abs(float(normal@tangent)),distance_to_endpoint_mm=float(np.linalg.norm(center-p[idx])))
                boundaries.append(row)
            # Inspect all rings; no forced choice if terminal criteria fail.
            candidates=[r for r in boundaries if r['closed'] and r['projected_area_mm2']>1 and
                        r['planarity_max_mm']<.25*r['equivalent_radius_mm'] and r['alignment']>.8 and
                        r['axial_outward_mm']>0 and r['distance_to_endpoint_mm']<15]
            selected=candidates[0] if len(candidates)==1 else None
            rows.append(dict(part_id=pid,edge_id=edge['id'],endpoint=endpoint,position_mm=p[idx].tolist(),
                radius_mm=edge['radii_mm'][idx],outward_unit_chord=outward.tolist(),
                outward_five_mm_direction=tangent.tolist(),boundaries=boundaries,
                terminal_candidates=candidates,selected_opening=selected,
                mesh_bounds_mm=mesh.bounds.tolist(),mesh_vertices=len(mesh.vertices),mesh_faces=len(mesh.faces)))
            chosen.append(p[idx])
            # Actual triangles within 45 mm of endpoint, not fabricated surfaces.
            faces=mesh.faces[np.linalg.norm(mesh.triangles_center-p[idx],axis=1)<45]
            ax.add_collection3d(Poly3DCollection(mesh.vertices[faces],facecolor=color,alpha=.22,edgecolor='none'))
            nearby=p[np.linalg.norm(p-p[idx],axis=1)<45]
            ax.plot(*nearby.T,c=color); ax.scatter(*p[idx],c=color,marker='x',s=60)
            for r in candidates: ax.scatter(*r['center_mm'],c=color,s=30)
        a,b=chosen; direction=b-a; gap=float(np.linalg.norm(direction)); direction/=gap
        directions=[]
        for row, desired, other in [(rows[0],direction,femoral),(rows[1],-direction,iliac)]:
            closest,distances,triangles=trimesh.proximity.closest_point_naive(meshes[other],np.array([row['position_mm']]))
            directions.append(dict(part_id=row['part_id'],
                outward_chord_angle_to_other_endpoint_deg=float(np.degrees(np.arccos(np.clip(np.dot(row['outward_unit_chord'],desired),-1,1)))),
                outward_five_mm_angle_to_other_endpoint_deg=float(np.degrees(np.arccos(np.clip(np.dot(row['outward_five_mm_direction'],desired),-1,1)))),
                endpoint_distance_to_other_surface_mm=float(distances[0]),closest_other_surface_point_mm=closest[0].tolist(),
                closest_other_face_index=int(triangles[0])))
        midpoint=(a+b)/2
        ax.plot(*np.array([a,b]).T,c='orange',linestyle='--',label='endpoint chord only')
        ax.set(xlim=(midpoint[0]-40,midpoint[0]+40),ylim=(midpoint[1]-45,midpoint[1]+45),zlim=(midpoint[2]-45,midpoint[2]+45),xlabel='LPS X mm',ylabel='LPS Y mm',zlabel='LPS Z mm',title=side+' actual source triangles and extracted endpoints')
        u=np.cross(direction,[1,0,0]); u/=np.linalg.norm(u); v=np.cross(direction,u)
        sections=[]
        for fraction in [0.,.25,.5,.75,1.]:
            origin=a+fraction*(b-a); parts_sections={}
            for pid,color in [(iliac,'firebrick'),(femoral,'royalblue')]:
                section=meshes[pid].section(plane_origin=origin,plane_normal=direction)
                lines=[] if section is None else section.discrete
                parts_sections[pid]=[dict(closed=bool(np.allclose(line[0],line[-1])),points_mm=line.tolist()) for line in lines]
                for line in lines:
                    secax.plot((line-origin)@u+fraction*35,(line-origin)@v,c=color)
            sections.append(dict(chord_fraction=fraction,origin_mm=origin.tolist(),normal=direction.tolist(),parts=parts_sections))
        secax.set_aspect('equal'); secax.set_title('Source sections at 0, .25, .5, .75, 1 chord\nEach section offset horizontally by 35 × fraction mm')
        secax.set_xlabel('Local transverse coordinate + panel offset mm'); secax.set_ylabel('Local transverse coordinate mm')
        fig.tight_layout(); path=out/(side.lower()+'-source-openings.png'); fig.savefig(path,dpi=160); plt.close(fig)
        figures.append(dict(path=str(path.relative_to(root)),sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        results.append(dict(side=side,parts=rows,endpoint_chord_mm=gap,sections=sections,
            endpoint_direction_diagnostics=directions,
            source_endpoint_selection='Distal external iliac endpoint and proximal femoral endpoint selected by source part identity and superior/inferior course, not minimum pair distance.',
            bridge_specification_status='WITHHELD_UNSUPPORTED_CONTINUATION',
            unresolved_reason='All mesh outline paths have near-zero projected area; no terminal opening ring supports these extraction endpoints. Endpoint chord spans adjacent source courses rather than a confirmed missing lumen segment. Requires source-coordinate/part overlap and anatomical transition review before a synthetic cut or bridge.'))
    report=dict(schema='vv-toolbox.iliofemoral-gaps/1',source_archive_sha256=hashes['bp3d'],
        centerline_preview_sha256=hashes['bp3d-preview'],source_case_revision=case_digest(case),
        parent_case_revision=revision,parent_snapshot_sha256=hashlib.sha256(parent_raw).hexdigest(),
        sides=results,figures=figures,extension_specification=None,
        inspection_status='COMPLETE_WITH_UNRESOLVED_CONNECTIONS',anatomical_acceptance='UNKNOWN',source_unchanged=source_path.read_bytes()==raw,
        parent_unchanged=parent_path.read_bytes()==parent_raw)
    (root/'docs/evidence/iliofemoral-gaps.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps([dict(side=r['side'],gap=r['endpoint_chord_mm'],parts=[dict(part=p['part_id'],rings=len(p['boundaries']),candidates=p['terminal_candidates']) for p in r['parts']]) for r in results]))


if __name__=='__main__': main()
