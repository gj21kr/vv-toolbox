"""Compare six sphere-overlap locations to unmodified atlas mesh sections."""
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
from inspect_brachiocephalic_junction import crossings

ROOT = Path(__file__).resolve().parents[1]


def main():
    report_path = ROOT/'docs/evidence/iliac-contact-refinement.json'
    raw = report_path.read_bytes()
    previous = json.loads(raw)
    path = ROOT/'exports/synthetic-common-iliac-trunk/case.snapshot.json'
    snapshot = path.read_bytes()
    case, revision = load_case(path)
    if revision != previous['case_revision']:
        raise ValueError('stale contact witnesses')
    atlas = load_atlas()
    if atlas.metadata['sha256'] != next(s['sha256'] for s in case['sources'] if s['id']=='bp3d'):
        raise ValueError('source archive mismatch')
    edges = {e['id']:e for e in case['edges']}
    pairs = [r for r in previous['pairs'] if r['scope']=='surrounding' and r['status']=='SWEPT_SPHERE_OVERLAP']
    if len(pairs)!=6:
        raise ValueError('expected six source review pairs')
    mapping = {'synthetic_R_common_iliac_trunk':'FJ3565','R-EIA-retained':'FJ3567'}
    def part_id(edge_id):
        return mapping[edge_id] if edge_id in mapping else edge_id.split(':')[0]
    ids = {part_id(e) for r in pairs for e in r['edges']}
    parts = {p['id']:p for p in atlas.meshes if p['id'] in ids}
    if set(parts)!=ids:
        raise ValueError('source part missing')
    meshes = {ident:trimesh.Trimesh(p['vertices'],p['faces'],process=False) for ident,p in parts.items()}
    out = ROOT/'exports/iliac-contact-sources'; out.mkdir(parents=True,exist_ok=True)
    rows, figures = [], []
    for batch in range(2):
        fig,axes = plt.subplots(3,3,figsize=(13,12))
        for row_index,r in enumerate(pairs[batch*3:batch*3+3]):
            source_ids = [part_id(e) for e in r['edges']]
            centers = np.array(r['witness']['centers_mm'])
            middle = centers.mean(axis=0)
            center_surface_distances=[]
            for ident,center in zip(source_ids,centers):
                _,distances,_=trimesh.proximity.closest_point_naive(meshes[ident],center[None,:])
                center_surface_distances.append(float(distances[0]))
            levels = sorted(set([float(middle[2]+d) for d in [-2,-1,-.5,0,.5,1,2]]+centers[:,2].tolist()))
            sections=[]
            for z in levels:
                contours=[]
                for ident in source_ids:
                    section = meshes[ident].section(plane_origin=[0,0,z],plane_normal=[0,0,1])
                    contours.append([] if section is None else section.discrete)
                count=sum(crossings(a[:,:2],b[:,:2]) for a in contours[0] for b in contours[1])
                sections.append(dict(z_mm=z,proper_contour_crossings=count,
                    contour_counts=[len(c) for c in contours],
                    contours_mm=[[c.tolist() for c in cs] for cs in contours]))
            for col,offset in enumerate([-2,0,2]):
                ax=axes[row_index,col]
                item=min(sections,key=lambda item:abs(item['z_mm']-(middle[2]+offset)))
                for ident,color,cs in zip(source_ids,['firebrick','royalblue'],item['contours_mm']):
                    for n,c in enumerate(cs):
                        c=np.array(c);ax.plot(c[:,0],c[:,1],color=color,label=ident if n==0 else None)
                for center,radius,color in zip(centers,r['witness']['radii_mm'],['firebrick','royalblue']):
                    square=radius**2-(item['z_mm']-center[2])**2
                    if square>0:
                        ax.add_patch(Circle(center[:2],np.sqrt(square),fill=False,
                                            linestyle=':',color=color,alpha=.8))
                # Same physical crop in all three sections of a pair.
                extent=max(12.,float(max(r['witness']['radii_mm']))+5)
                ax.set(xlim=(middle[0]-extent,middle[0]+extent),ylim=(middle[1]-extent,middle[1]+extent),
                       title=f'{source_ids[0]} / {source_ids[1]}\nZ={item["z_mm"]:.3f}, crossings={item["proper_contour_crossings"]}',
                       xlabel='L (mm)',ylabel='P (mm)')
                ax.set_aspect('equal');ax.grid(alpha=.2)
            rows.append(dict(edges=r['edges'],source_ids=source_ids,witness=r['witness'],sections=sections,
                witness_center_to_own_source_surface_unsigned_mm=center_surface_distances,
                sampled_surface_intersection=any(s['proper_contour_crossings']>0 for s in sections),
                limitation='Proper crossings only; absent crossings do not exclude containment, tangency or intersections outside sampled planes. Original source mesh differs from synthetic radius profiles.'))
        fig.suptitle('Solid: original source sections / dotted: witness sphere sections')
        fig.tight_layout();figure=out/f'source-sections-{batch+1}.png'
        fig.savefig(figure,dpi=130);plt.close(fig)
        figures.append(dict(path=figure.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(figure.read_bytes()).hexdigest()))
    if report_path.read_bytes()!=raw or path.read_bytes()!=snapshot:
        raise ValueError('inputs changed')
    result=dict(schema='vv-toolbox.iliac-contact-source-sections/1',case_revision=revision,
        input_report_sha256=hashlib.sha256(raw).hexdigest(),source_archive_sha256=atlas.metadata['sha256'],
        source_mesh_fingerprints={k:hashlib.sha256(np.asarray(p['vertices']).tobytes()+np.asarray(p['faces']).tobytes()).hexdigest() for k,p in parts.items()},
        pairs=rows,figures=figures,inputs_unchanged=True,anatomical_connectivity='UNKNOWN',default_app_applied=False)
    (ROOT/'docs/evidence/iliac-contact-source-sections.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps([dict(source_ids=r['source_ids'],crossings=[s['proper_contour_crossings'] for s in r['sections']]) for r in rows]))


if __name__=='__main__':
    main()
