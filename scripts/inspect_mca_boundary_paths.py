"""All-source MCA path coverage and reproducible unapproved bend locators."""
import hashlib
import json
import zipfile
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np

from vv_toolbox.atlas import parse_obj

ROOT=Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def at(points, arc, station):
    i=min(int(np.searchsorted(arc,station,side='right')-1),len(points)-2)
    i=max(0,i)
    f=float((station-arc[i])/(arc[i+1]-arc[i]))
    return i,f,points[i]*(1-f)+points[i+1]*f


def bend(edge, near=None):
    points=np.asarray(edge['points'],float)
    arc=np.r_[0.,np.cumsum(np.linalg.norm(np.diff(points,axis=0),axis=1))]
    if arc[-1]<=4.:
        return None
    stations=np.arange(2.,arc[-1]-2.+1e-8,.25)
    reference_arc=None
    if near is not None:
        delta=np.diff(points,axis=0)
        t=np.clip(np.sum((near-points[:-1])*delta,axis=1)/np.sum(delta*delta,axis=1),0,1)
        locations=points[:-1]+t[:,None]*delta
        k=int(np.argmin(np.linalg.norm(locations-near,axis=1)))
        reference_arc=float(arc[k]+t[k]*(arc[k+1]-arc[k]))
        stations=stations[np.abs(stations-reference_arc)<=8.]
    if not len(stations):
        return None
    rows=[]
    for s in stations:
        i,f,p=at(points,arc,s)
        a=p-at(points,arc,s-2.)[2];b=at(points,arc,s+2.)[2]-p
        norm=np.linalg.norm(a)*np.linalg.norm(b)
        if norm<1e-12:
            continue
        angle=float(np.degrees(np.arccos(np.clip(a@b/norm,-1.,1.))))
        rows.append(dict(edge_id=edge['id'],interval_index=i,fraction=f,position_mm=p.tolist(),
            arc_from_start_mm=float(s),radius_mm=float(np.interp(f,[0,1],edge['radii'][i:i+2])),
            turn_angle_degrees=angle,reference_locator_arc_mm=reference_arc,
            uncertainty_window_arc_mm=[float(max(0,s-2.)),float(min(arc[-1],s+2.))]))
    if not rows:
        return None
    row=max(rows,key=lambda r:r['turn_angle_degrees'])
    row.update(status='operational_bend_locator',anatomical_boundary_approved=False,
        method='Maximum chord turn on 0.25 mm stations with +/-2 mm chords'+(' within +/-8 mm of prior surface contact projection' if near is not None else ''),
        limitation='Voxel-derived path bend may be extraction noise or ordinary vessel curvature; not a genu, circular sulcus, or opercular exit annotation.')
    return row


def main():
    prior_path=ROOT/'docs/evidence/mca-boundary-review.json'
    prior=json.loads(prior_path.read_text())
    source=ROOT/'reference-data/bodyparts3d'
    archive=source/'isa_BP3D_4.0_obj_99.zip';preview=source/'centerlines-preview.json'
    if sha(archive)!=prior['source_archive_sha256'] or sha(preview)!=prior['centerline_preview_sha256']:
        raise ValueError('source fingerprints changed')
    edges=json.loads(preview.read_text())['edges']
    meshes={}
    with zipfile.ZipFile(archive) as z:
        lookup={Path(n).stem:n for n in z.namelist() if n.endswith('.obj')}
        for asset in prior['assets']:
            raw=z.read(lookup[asset['element_id']])
            if hashlib.sha256(raw).hexdigest()!=asset['sha256']:
                raise ValueError('OBJ changed')
            meshes[asset['element_id']]=parse_obj(raw)
    out=ROOT/'exports/mca-boundary-path-audit';out.mkdir(parents=True,exist_ok=True)
    rows=[];candidates=[];figures=[]
    assets={a['element_id']:a for a in prior['assets']}
    for route in prior['routes']:
        pid=route['source_element_id'];side=route['side']
        selected=[e for e in edges if e['part_id']==pid]
        if {e['id'] for e in selected}!={e['id'] for e in route['centerline_edges']}:
            raise ValueError('edge coverage changed')
        names=assets[pid]['names']
        perforator=any('central branch' in n for n in names)
        named_insular=any('insular part' in n for n in names)
        named_m1=any('sphenoid part' in n and n.startswith(('sphenoid','left','right')) for n in names)
        records=[]
        for e in selected:
            p=np.array(e['points']);length=float(np.linalg.norm(np.diff(p,axis=0),axis=1).sum())
            probe=bend(e)
            decisions={}
            for boundary in ('M1_M2','M2_M3','M3_M4'):
                if perforator:
                    reason='Source central-branch identity; do not impose the cortical trunk segment sequence on this extracted edge.'
                    decision='Trace source origin and adjudicate branch eligibility before any cortical segment boundary.'
                elif boundary=='M1_M2':
                    reason='No specimen genu/limen annotation or oriented daughter continuity.'
                    decision='Compare M1 and named insular daughter together at the recorded contact-window bend; mark limen/genu independently of bifurcation.'
                elif boundary=='M2_M3':
                    reason='No circular-sulcus curve intersected with this path; insula proximity is not that curve.'
                    decision='Trace insula margin groove in this side-specific context, then mark path crossing; verify source-part continuity first if path ends before groove.'
                else:
                    reason='No opercular cleft exit curve for this path; nearest cortical surface is not an exit.'
                    decision='Follow same identified cortical daughter through opercular cleft to exposed convexity and annotate the exit with source surface evidence.'
                decisions[boundary]=dict(status='unresolved',position=None,reason=reason,next_decision=decision)
            records.append(dict(edge_id=e['id'],start_node=e['start'],end_node=e['end'],
                point_count=len(p),length_mm=length,endpoints_mm=[p[0].tolist(),p[-1].tolist()],
                orientation='source extraction order; not validated flow/proximal direction',
                operational_path_probe=probe,probe_absence_reason=None if probe else 'Path too short or degenerate for +/-2 mm chord measurement',
                boundary_assessments=decisions))
        for locator in prior['inspection_locators']:
            if locator['branch_id']!=pid:
                continue
            for e in selected:
                candidate=bend(e,np.array(locator['position']))
                if candidate:
                    candidate.update(source_element_id=pid,boundary_group=locator['boundary_group'],
                        source_surface_locator=locator['position'],source_obj_sha256=assets[pid]['sha256'],
                        next_decision='Inspect this bend in source surface plus M1/insula context; separately label limen/genu and verify daughter continuity before accepting a boundary.')
                    candidates.append(candidate)
        rows.append(dict(side=side,source_element_id=pid,source_names=names,source_obj_sha256=assets[pid]['sha256'],
            source_class='central_branch_identity' if perforator else 'named_insular' if named_insular else 'named_M1' if named_m1 else 'other_MCA_named_branch',
            extracted_edge_count=len(records),edges=records,anatomical_daughter_count=None))
    # All parts shown separately in two views; each edge is colored and labelled.
    for side,context in [('R',['FJ1749','FJ1745','FJ1801','FJ1798','FJ1842','FJ1838','FJ1840']),
                         ('L',['FJ1748','FJ1744','FJ1800','FJ1797','FJ1841','FJ1837','FJ1839'])]:
        side_rows=[r for r in rows if r['side']==side]
        for batch in range(0,len(side_rows),6):
            subset=side_rows[batch:batch+6]
            fig=plt.figure(figsize=(14,3.7*len(subset)))
            for rownum,row in enumerate(subset):
                pid=row['source_element_id'];selected=[e for e in edges if e['part_id']==pid]
                for view,(elev,azim) in enumerate([(15,25),(50,115)]):
                    ax=fig.add_subplot(len(subset),2,rownum*2+view+1,projection='3d')
                    for j,cid in enumerate(context):
                        v,f=meshes[cid]
                        ax.add_collection3d(Poly3DCollection(v[f],facecolor='#62b39a' if j==0 else '#b8bcc7',alpha=.12 if j==0 else .025,edgecolors='none'))
                    v,f=meshes[pid]
                    ax.add_collection3d(Poly3DCollection(v[f],facecolor='crimson',alpha=.18,edgecolors='none'))
                    m1='FJ1692'+('M' if side=='L' else '')
                    if pid!=m1:
                        mv,mf=meshes[m1]
                        ax.add_collection3d(Poly3DCollection(mv[mf],facecolor='#606060',alpha=.18,edgecolors='none'))
                    for n,e in enumerate(selected):
                        p=np.array(e['points']);color=plt.cm.tab20(n%20)
                        ax.plot(*p.T,color=color,lw=1.5)
                        ax.text(*p[len(p)//2],e['id'].split(':')[1],fontsize=6)
                    for c in candidates:
                        if c['source_element_id']==pid:
                            ax.scatter(*c['position_mm'],color='blue',s=24)
                    bounds=np.vstack([meshes[context[0]][0],v]);mid=(bounds.min(0)+bounds.max(0))/2
                    span=float(np.max(np.ptp(bounds,axis=0)))*.55
                    ax.set(xlim=(mid[0]-span,mid[0]+span),ylim=(mid[1]-span,mid[1]+span),zlim=(mid[2]-span,mid[2]+span))
                    ax.set_box_aspect((1,1,1));ax.view_init(elev,azim)
                    ax.set_title(pid+' | '+str(len(selected))+' extraction edges',fontsize=10)
                    ax.set_xlabel('LPS X');ax.set_ylabel('LPS Y');ax.set_zlabel('LPS Z')
            fig.suptitle(side+' MCA all-source path audit; blue = unapproved contact-window bend',fontsize=12)
            fig.tight_layout(rect=(0,0,1,.98));path=out/(side+'-'+str(batch//6+1)+'.png')
            fig.savefig(path,dpi=110);plt.close(fig)
            figures.append(dict(path=str(path.relative_to(ROOT)),sha256=sha(path),part_ids=[r['source_element_id'] for r in subset],views_per_part=2))
    groups=[dict(boundary_id=g['boundary_id'],position=None,status='unresolved',anatomical_boundary_approved=False,
        covered_part_ids=[r['source_element_id'] for r in rows if r['side'] in g['boundary_id'].split('.')]) for g in prior['groups']]
    if len(rows)!=46 or sum(len(r['edges']) for r in rows)!=120 or len(groups)!=6:
        raise ValueError('full MCA coverage mismatch')
    report=dict(schema='vv-toolbox.mca-boundary-path-audit/1',source_archive_sha256=sha(archive),
        centerline_preview_sha256=sha(preview),prior_report_sha256=sha(prior_path),coordinate_frame_id='bodyparts3d_native_LPS',units='mm',
        groups=groups,parts=rows,operational_candidates=candidates,figures=figures,approved_count=0,
        coverage=dict(source_parts=46,extraction_edges=120,views=92,anatomical_daughter_count='UNKNOWN'),
        visual_review_scope='All 8 overview sheets inspected; gross path coverage only, not individual anatomical boundary adjudication. See MCA_BOUNDARY_PATH_AUDIT.md for observations.',
        limitations=['No automatic boundary acceptance from curvature, source element ends, nearest distances, or bounding boxes.',
            'Operational probes/candidates supply reproducible review locations only; not anatomical segmentation.',
            'No source geometry, connectivity, or app annotations modified.'])
    (ROOT/'docs/evidence/mca-boundary-path-audit.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps(dict(parts=len(rows),edges=sum(len(r['edges']) for r in rows),candidates=len(candidates),figures=len(figures),approved=0)),flush=True)


if __name__=='__main__':
    main()
