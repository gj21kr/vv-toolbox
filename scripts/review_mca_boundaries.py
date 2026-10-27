"""Inspect MCA routes with original gyral/insular context; never auto-approve boundaries."""
from pathlib import Path
import csv, json, hashlib, zipfile
import numpy as np
from scipy.spatial import cKDTree
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'reference-data/bodyparts3d'
OUT=ROOT/'exports/mca-boundary-review'

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    rows=list(csv.reader((SOURCE/'isa_element_parts.txt').read_text().splitlines(),delimiter='\t'))
    vessels=sorted({r[2] for r in rows if len(r)>2 and (r[0] in ['FMA50080','FMA50081'] or 'middle cerebral artery' in r[1])})
    cortex={'R':['FJ1749','FJ1745','FJ1801','FJ1798','FJ1842','FJ1838','FJ1840'],
            'L':['FJ1748','FJ1744','FJ1800','FJ1797','FJ1841','FJ1837','FJ1839']}
    ids=vessels+sum(cortex.values(),[])
    archive=SOURCE/'isa_BP3D_4.0_obj_99.zip'
    sha=hashlib.sha256(archive.read_bytes()).hexdigest()
    assert sha==json.loads((SOURCE/'acquisition.json').read_text())['files'][archive.name]['sha256']
    meshes={}; assets=[]
    with zipfile.ZipFile(archive) as z:
        for ident in ids:
            names=[n for n in z.namelist() if Path(n).name==ident+'.obj']; assert len(names)==1
            raw=z.read(names[0]); lines=raw.decode().splitlines()
            v=np.array([list(map(float,l.split()[1:4])) for l in lines if l.startswith('v ')])
            f=[]
            for line in lines:
                if line.startswith('f '):
                    p=[int(x.split('/')[0])-1 for x in line.split()[1:]]
                    f.extend([[p[0],p[i],p[i+1]] for i in range(1,len(p)-1)])
            f=np.array(f); assert np.isfinite(v).all() and f.min()>=0 and f.max()<len(v)
            meshes[ident]=(v,f)
            assets.append(dict(element_id=ident,names=[r[1] for r in rows if len(r)>2 and r[2]==ident],sha256=hashlib.sha256(raw).hexdigest(),vertices=len(v),triangles=len(f),bounds=[v.min(0).tolist(),v.max(0).tolist()]))
    preview=SOURCE/'centerlines-preview.json'
    graph=json.loads(preview.read_text()); edges=[e for e in graph['edges'] if e['part_id'] in vessels]
    mirror_checks=[]
    for ident in vessels:
        if ident+'M' in meshes:
            reflected=meshes[ident][0]*np.array([-1,1,1])
            distance=cKDTree(meshes[ident+'M'][0]).query(reflected)[0]
            mirror_checks.append(dict(right=ident,left=ident+'M',maximum_reflected_vertex_distance_mm=float(distance.max())))
    figures=[]; routes=[]; locators=[]
    for side,context in cortex.items():
        vi=[i for i in vessels if i.endswith('M')==(side=='L')]
        fig,axes=plt.subplots(1,3,figsize=(19,8))
        for ax,(a,b) in zip(axes,[(1,2),(0,2),(0,1)]):
            for j,ident in enumerate(context):
                v,f=meshes[ident]
                ax.add_collection(PolyCollection(v[f][:,:,[a,b]],facecolors=plt.cm.Set2(j/7),edgecolors='none',alpha=.13 if j else .35))
                p=v.mean(0); ax.text(p[a],p[b],ident,fontsize=7)
            for j,ident in enumerate(vi):
                v,f=meshes[ident]
                ax.add_collection(PolyCollection(v[f][:,:,[a,b]],facecolors=plt.cm.tab20(j/len(vi)),edgecolors='none',alpha=.85))
                p=v.mean(0); ax.text(p[a],p[b],ident,fontsize=6)
            ax.autoscale_view(); ax.set_aspect('equal'); ax.set_xlabel('XYZ'[a]+' mm'); ax.set_ylabel('XYZ'[b]+' mm')
        fig.suptitle(side+' MCA with insula and opercular-covering gyri; projections do not prove contact')
        fig.tight_layout(); path=OUT/(side+'-context.png'); fig.savefig(path,dpi=150); plt.close(fig)
        figures.append(dict(path=str(path.relative_to(ROOT)),sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        insula=meshes[context[0]][0]; tree=cKDTree(insula)
        for ident in vi:
            es=[e for e in edges if e['part_id']==ident]
            routes.append(dict(side=side,source_element_id=ident,centerline_edges=[dict(id=e['id'],point_count=len(e['points']),endpoints=[e['points'][0],e['points'][-1]],nearest_insula_vertex_distance_range_mm=[float(tree.query(e['points'])[0].min()),float(tree.query(e['points'])[0].max())]) for e in es],status='unresolved',limitation='Distance to an insular surface vertex is not a circular sulcus or cortical exit annotation.'))
        suffix='M' if side=='L' else ''
        for part in ['FJ1660','FJ1694']:
            a=meshes['FJ1692'+suffix][0]; b=meshes[part+suffix][0]
            d,k=cKDTree(b).query(a); n=int(d.argmin())
            locators.append(dict(boundary_group=f'B.{side}.MCA.M1_M2',branch_id=part+suffix,position=a[n].tolist(),paired_surface_position=b[k[n]].tolist(),vertex_distance_mm=float(d[n]),method='nearest source-part vertex pair for inspection only',evidence_status='name_candidate',anatomical_boundary_approved=False))
    result=dict(schema='vv-toolbox.mca-boundary-review/1',coordinate_frame_id='bodyparts3d_native_LPS',units='mm',source_archive_sha256=sha,centerline_preview_sha256=hashlib.sha256(preview.read_bytes()).hexdigest(),assets=assets,routes=routes,mirror_checks=mirror_checks,inspection_locators=locators,figures=figures,approved_count=0,groups=[dict(boundary_id=f'B.{s}.MCA.{t}',position=None,evidence_status='unresolved',branch_source_ids=[r['source_element_id'] for r in routes if r['side']==s]) for s in ['L','R'] for t in ['M1_M2','M2_M3','M3_M4']])
    (ROOT/'docs/evidence/mca-boundary-review.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(assets=len(assets),vessels=len(vessels),routes=len(routes),centerline_edges=len(edges),locators=locators,figures=figures)))

if __name__=='__main__': main()
