"""Inspect BP3D ACA landmarks in native mm; run with Docker numpy/trimesh/matplotlib."""
import hashlib, json, zipfile
from pathlib import Path
import numpy as np
import trimesh
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'exports/aca-boundary-review'
IDS=['FJ1742','FJ1654','FJ1654M','FJ1655','FJ1699','FJ1699M','FJ1676','FJ1676M']

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    src=ROOT/'reference-data/bodyparts3d'
    archive=src/'isa_BP3D_4.0_obj_99.zip'
    expected=json.loads((src/'acquisition.json').read_text())['files'][archive.name]['sha256']
    assert hashlib.sha256(archive.read_bytes()).hexdigest()==expected, 'Source archive fingerprint mismatch'
    meshes={}; hashes={}
    with zipfile.ZipFile(archive) as z:
        for ident in IDS:
            names=[n for n in z.namelist() if Path(n).name==ident+'.obj']
            assert len(names)==1
            raw=z.read(names[0]); hashes[ident]=hashlib.sha256(raw).hexdigest()
            import io
            meshes[ident]=trimesh.load(io.BytesIO(raw),file_type='obj',process=False)
    raw=(src/'centerlines-preview.json').read_bytes()
    cl=json.loads(raw); edges=[e for e in cl['edges'] if e['part_id'] in IDS]
    colors={'FJ1654':'red','FJ1654M':'darkorange','FJ1699':'red','FJ1699M':'darkorange','FJ1676':'purple','FJ1676M':'violet','FJ1655':'blue'}
    fig,axs=plt.subplots(1,3,figsize=(21,9))
    for ax,plane in zip(axs,[0,-3,3]):
        sec=meshes['FJ1742'].section(plane_origin=[plane,0,0],plane_normal=[1,0,0])
        if sec:
            for points in sec.discrete: ax.plot(points[:,1],points[:,2],color='black',lw=2)
        for e in edges:
            p=np.array(e['points'])
            if e['part_id']=='FJ1655' or (plane<=0 and not e['part_id'].endswith('M')) or (plane>0 and e['part_id'].endswith('M')):
                ax.plot(p[:,1],p[:,2],color=colors[e['part_id']],lw=1)
                if e['part_id'].startswith('FJ1699'):
                    for i in range(0,len(p),20): ax.annotate(e['id']+':'+str(i),(p[i,1],p[i,2]),fontsize=6)
        ax.set_title(f'Callosum section X={plane} mm; ACA projected YZ')
        ax.set_xlim(-150,-75);ax.set_ylim(1530,1605);ax.set_aspect('equal');ax.grid();ax.set_xlabel('+Y posterior');ax.set_ylabel('+Z superior')
    fig.tight_layout();fig.savefig(OUT/'sagittal-sections.png',dpi=160);plt.close(fig)
    fig=plt.figure(figsize=(18,8))
    for j,(elev,azim) in enumerate([(15,-20),(25,160)]):
        ax=fig.add_subplot(1,2,j+1,projection='3d')
        for ident,m in meshes.items():
            ax.add_collection3d(Poly3DCollection(m.vertices[m.faces],alpha=.12 if ident=='FJ1742' else .7,facecolor='gray' if ident=='FJ1742' else colors[ident],edgecolor='none'))
        ax.set_xlim(-15,15);ax.set_ylim(-150,-65);ax.set_zlim(1530,1610);ax.set_box_aspect([30,85,80]);ax.view_init(elev,azim)
        ax.set_xlabel('X');ax.set_ylabel('Y');ax.set_zlabel('Z')
    fig.savefig(OUT/'oblique-surfaces.png',dpi=160);plt.close(fig)
    result={'source_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'centerline_sha256':hashlib.sha256(raw).hexdigest(),'obj_sha256':hashes,'edges':[{'id':e['id'],'points':e['points']} for e in edges]}
    (OUT/'inspection.json').write_text(json.dumps(result,indent=2))
    fig,axs=plt.subplots(1,3,figsize=(16,5))
    for ax,zlevel in zip(axs,[1537.5,1538,1538.5]):
        for ident in ['FJ1654','FJ1654M','FJ1655']:
            sec=meshes[ident].section(plane_origin=[0,0,zlevel],plane_normal=[0,0,1])
            if sec:
                for points in sec.discrete: ax.plot(points[:,0],points[:,1],color=colors[ident],label=ident)
        ax.set_xlim(-7,7);ax.set_ylim(-117,-108);ax.set_aspect('equal');ax.grid();ax.set_title(f'True axial section Z={zlevel} mm')
    fig.savefig(OUT/'acom-sections.png',dpi=180);plt.close(fig)
    boundaries=[]
    for side,suffix in [('R',''),('L','M')]:
        for boundary,limits in [('A2_A3',[-127,-119,1553,1557]),('A3_A4',[-120,-110,1576,1581])]:
            matches=[]
            for e in edges:
                if e['part_id']!='FJ1699'+suffix: continue
                for i,p in enumerate(e['points']):
                    if limits[0]<=p[1]<=limits[1] and limits[2]<=p[2]<=limits[3]: matches.append({'edge_id':e['id'],'point_index':i,'position':p})
            assert matches
            pts=np.array([m['position'] for m in matches])
            boundaries.append({'boundary_id':f'B.{side}.ACA.{boundary}','evidence_status':'landmark_reviewed','localization_scope':'region_only','position':None,'region_bounds_mm':[pts.min(0).tolist(),pts.max(0).tolist()],'sample_count':len(matches),'centerline_samples':matches,'region_selection_yz_mm':limits,'region_definition':'Manual visual bracket of rostrum-genu transition' if boundary=='A2_A3' else 'Manual visual bracket of superior genu to posterior supracallosal course','exact_boundary_plane_approved':False,'uncertainty':'Reviewer-selected transition region, not a calibrated confidence interval; no unique sharp boundary on smooth callosal mesh.'})
        e=next(e for e in edges if e['part_id']=='FJ1654'+suffix)
        a=next(e for e in edges if e['part_id']=='FJ1655')
        p=np.array(e['points']);q=np.array(a['points'])
        d=np.linalg.norm(p[:,None,:]-q[None,:,:],axis=2);i,j=np.unravel_index(np.argmin(d),d.shape)
        boundaries.append({'boundary_id':f'B.{side}.ACA.A1_A2','evidence_status':'candidate','position':None,'candidate_position':p[i].tolist(),'edge_id':e['id'],'point_index':int(i),'acom_point_index':int(j),'centerline_distance_mm':float(d[i,j]),'exact_boundary_plane_approved':False,'reason':'ACom side attachment neighborhood identified by crossing closed surface-section contours at Z=1537.5 and 1538 mm. Separate overlapping surfaces do not provide an explicit shared ostial plane. Nearest derived centerline samples are inspection anchors, not a proven lumen junction.'})
    report={'schema':'vv_toolbox.aca_boundary_review/1','review_date':'2026-10-20','coordinate_frame_id':'bodyparts3d_native_LPS','units':'mm','source_archive_sha256':result['source_sha256'],'centerline_sha256':result['centerline_sha256'],'obj_sha256':hashes,'review_method':'Manual inspection of exact X=0,-3,+3 callosal sections, oblique source surface renderings, and axial ACom sections. Centerlines are derived voxel-lee-1, not source annotations.','boundaries':boundaries,'figures':[{'path':str(f.relative_to(ROOT)),'sha256':hashlib.sha256(f.read_bytes()).hexdigest()} for f in sorted(OUT.glob('*.png'))],'clinical_validation':'NOT RUN','lumen_connectivity':'NOT PROVEN','approved_exact_coordinates':0}
    (ROOT/'docs/evidence/aca-boundary-review.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'figures':str(OUT),'edges':[(e['id'],len(e['points'])) for e in edges]}))

if __name__=='__main__': main()
