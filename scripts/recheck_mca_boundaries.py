"""Branch-specific rotated/cut-away source inspection, without boundary approval."""
from pathlib import Path
import hashlib
import json
import zipfile
import numpy as np
from scipy.spatial import cKDTree
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'reference-data/bodyparts3d'
OUT = ROOT / 'exports/mca-boundary-followup'


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    prior = json.loads((ROOT / 'docs/evidence/mca-boundary-review.json').read_text())
    archive = SOURCE / 'isa_BP3D_4.0_obj_99.zip'
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == prior['source_archive_sha256']
    preview = SOURCE / 'centerlines-preview.json'
    assert hashlib.sha256(preview.read_bytes()).hexdigest() == prior['centerline_preview_sha256']
    edges = json.loads(preview.read_text())['edges']
    meshes = {}
    with zipfile.ZipFile(archive) as z:
        for asset in prior['assets']:
            ident = asset['element_id']
            name = next(n for n in z.namelist() if Path(n).name == ident + '.obj')
            raw = z.read(name)
            assert hashlib.sha256(raw).hexdigest() == asset['sha256']
            vertices, faces = [], []
            for line in raw.decode().splitlines():
                if line.startswith('v '):
                    vertices.append(list(map(float, line.split()[1:4])))
                if line.startswith('f '):
                    p = [int(t.split('/')[0]) - 1 for t in line.split()[1:]]
                    faces.extend([[p[0], p[i], p[i+1]] for i in range(1, len(p)-1)])
            meshes[ident] = np.array(vertices), np.array(faces)
    results, figures = [], []
    for side, context in [('R', ['FJ1749','FJ1745','FJ1801','FJ1798','FJ1842','FJ1838','FJ1840']),
                          ('L', ['FJ1748','FJ1744','FJ1800','FJ1797','FJ1841','FJ1837','FJ1839'])]:
        suffix = 'M' if side == 'L' else ''
        sign = 1 if side == 'L' else -1
        insula_tree = cKDTree(meshes[context[0]][0])
        for branch in ['FJ1660', 'FJ1694', 'FJ1664', 'FJ1718']:
            ident = branch + suffix
            selected = [e for e in edges if e['part_id'] == ident]
            v, f = meshes[ident]
            # Cut-away removes lateral context triangles by centroid; no new anatomy.
            plane = float(np.median(v[:,0]))
            fig = plt.figure(figsize=(15, 9))
            for k, (elev, azim, cut) in enumerate([(15,25,False),(15,115,False),(55,25,False),(15,25,True)]):
                ax = fig.add_subplot(2,2,k+1, projection='3d')
                for j, cid in enumerate(context):
                    cv, cf = meshes[cid]
                    if cut and j:
                        cf = cf[sign * cv[cf].mean(1)[:,0] <= sign * plane]
                    ax.add_collection3d(Poly3DCollection(cv[cf], facecolors=plt.cm.Set2(j/7), alpha=.09 if j else .3, edgecolors='none'))
                for vid, color, alpha in [('FJ1692'+suffix,'grey',.3), (ident,'crimson',.55)]:
                    mv,mf=meshes[vid]
                    ax.add_collection3d(Poly3DCollection(mv[mf], facecolors=color, alpha=alpha, edgecolors='none'))
                for edge in selected:
                    p = np.asarray(edge['points'])
                    ax.plot(*p.T, color='black', linewidth=1)
                    ax.scatter(*p[0], color='blue', s=15)
                    ax.scatter(*p[-1], color='orange', s=15)
                    ax.text(*p[len(p)//2], edge['id'].split(':')[-1], fontsize=6)
                bounds = np.concatenate([meshes[c][0] for c in context])
                lo, hi = bounds.min(0), bounds.max(0)
                ax.set(xlim=(lo[0],hi[0]),ylim=(lo[1],hi[1]),zlim=(lo[2],hi[2]),xlabel='X mm',ylabel='Y mm',zlabel='Z mm')
                ax.set_box_aspect(hi-lo)
                ax.view_init(elev=elev, azim=azim if side=='R' else 180-azim)
                ax.set_title(f'{ident}: elevation {elev}, azimuth {azim}; '+('context cut-away' if cut else 'full context'))
            fig.suptitle('Native atlas + derived path; blue/orange = extraction endpoints, NOT anatomical boundaries')
            fig.tight_layout()
            path=OUT/f'{ident}-rotations.png'; fig.savefig(path,dpi=125); plt.close(fig)
            figures.append({'path':str(path.relative_to(ROOT)), 'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
            records=[]
            for edge in selected:
                p=np.asarray(edge['points']); length=np.r_[0,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))]
                distance=insula_tree.query(p)[0]
                records.append({'edge_id':edge['id'],'point_count':len(p),'length_mm':float(length[-1]),'endpoint_distance_to_insula_vertices_mm':[float(distance[0]),float(distance[-1])], 'insula_vertex_distance_min_max_mm':[float(distance.min()),float(distance.max())], 'endpoints_mm':[p[0].tolist(),p[-1].tolist()], 'orientation':'extraction order, not proximal-to-distal validated'})
            results.append({'side':side,'source_element_id':ident,'edges':records,'cutaway_plane_x_mm':plane,'cutaway_rule':'remove context triangles with lateral centroid beyond branch median X; not a sulcus plane','boundary_position':None,'status':'unresolved'})
    groups = prior['groups']
    for group in groups:
        group['anatomical_boundary_approved'] = False
        group['followup_branch_source_ids'] = [r['source_element_id'] for r in results if r['side'] in group['boundary_id'].split('.')]
    report={'schema':'vv-toolbox.mca-boundary-followup/1','source_archive_sha256':prior['source_archive_sha256'],'centerline_preview_sha256':prior['centerline_preview_sha256'],'coordinate_frame_id':'bodyparts3d_native_LPS','units':'mm','groups':groups,'branch_reviews':results,'figures':figures,'approved_count':0,'limitations':['Rotated views and centroid cut-away do not supply a named circular sulcus curve or an opercular exit curve.','Preview edges remain unoriented; source part contacts do not establish a continuous daughter path.','No clinical or independent imaging validation.']}
    (ROOT/'docs/evidence/mca-boundary-followup.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'branch_parts':len(results),'edges':sum(len(r['edges']) for r in results),'groups':len(report['groups']),'approved':0,'figures':len(figures)}))


if __name__ == '__main__':
    main()
