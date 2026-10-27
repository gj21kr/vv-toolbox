"""Build explicit full source-guided profiles, preserving connected endpoint chords."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import numpy as np
import trimesh
from vv_toolbox.atlas import load_atlas
from vv_toolbox.case_io import load_case
from vv_toolbox.case_contract import validate_case
from vv_toolbox.geometry_quality import screen_nonincident_clearance,segment_distance
from vv_toolbox.junction_continuity import inspect_bridge_continuity
from build_synthetic_arch_carotid_case import store_snapshot
from inspect_iliac_normal_sections import section_metrics

ROOT=Path(__file__).resolve().parents[1]


def main():
    parent_path=ROOT/'exports/synthetic-common-iliac-trunk/case.snapshot.json'
    raw=parent_path.read_bytes();case,revision=load_case(parent_path)
    source_path=ROOT/'docs/evidence/full-iliac-source-profiles-axial.json'
    source_raw=source_path.read_bytes();source=json.loads(source_raw)
    atlas=load_atlas()
    if source['case_revision']!=revision or source['source_archive_sha256']!=atlas.metadata['sha256']:
        raise ValueError('profile evidence differs')
    candidate=deepcopy(case);candidate['case_id']='R-iliac-full-source-profile-candidate'
    changes=[];old_edges={e['id']:e for e in case['edges']}
    for profile in source['paths']:
        edge=next(e for e in candidate['edges'] if e['id']==profile['edge_id'])
        old=deepcopy(edge);p=np.array(edge['centerline_mm']);arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))]
        if profile['unresolved_indices'] or len(profile['samples'])!=len(p):raise ValueError('incomplete profile')
        target=np.array([s['centroid_mm'] for s in profile['samples']]);weight=np.ones(len(p));locked=[]
        for endpoint,idx in [('start',0),('end',-1)]:
            if sum(edge[endpoint] in (e['start'],e['end']) for e in case['edges'])>1:
                locked.append(endpoint)
                distance=arc-arc[1] if idx==0 else arc[-2]-arc
                t=np.clip(distance/5.,0,1);weight=np.minimum(weight,t*t*(3-2*t))
        changed=p+weight[:,None]*(target-p)
        if np.linalg.norm(changed-p,axis=1).max()>5:raise ValueError('centroid displacement exceeds 5 mm')
        displacement=float(np.linalg.norm(changed-p,axis=1).max())
        # Equal-Z source stations can collapse onto the same axial centroid.
        # Retain their mapping explicitly instead of creating zero-length edges.
        keep=np.r_[True,np.linalg.norm(np.diff(changed,axis=0),axis=1)>1e-9]
        indices=np.flatnonzero(keep)
        changed=changed[keep];weight=weight[keep]
        edge['centerline_mm']=changed.tolist()
        for endpoint,idx in [('start',0),('end',-1)]:
            if endpoint not in locked:
                node=candidate['nodes'][edge[endpoint]]
                node['position_mm']=changed[idx].tolist();node['evidence_status']='synthetic_estimate'
        part=next(p for p in atlas.meshes if p['id']==profile['source_id'])
        fp=hashlib.sha256(np.asarray(part['vertices']).tobytes()+np.asarray(part['faces']).tobytes()).hexdigest()
        if fp!=profile['source_mesh_sha256']:raise ValueError('source mesh differs')
        mesh=trimesh.Trimesh(part['vertices'],part['faces'],process=False)
        new_arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(changed,axis=0),axis=1))];radii=[]
        for i,point in enumerate(changed):
            normal=np.array([np.interp(min(new_arc[-1],new_arc[i]+2),new_arc,changed[:,k])-
                             np.interp(max(0,new_arc[i]-2),new_arc,changed[:,k]) for k in range(3)])
            normal/=np.linalg.norm(normal);u=np.cross(normal,np.eye(3)[int(np.argmin(abs(normal)))]);u/=np.linalg.norm(u);v=np.cross(normal,u)
            section=mesh.section(plane_origin=point,plane_normal=normal);cs=[] if section is None else section.discrete
            if len(cs)!=1:raise ValueError(f'nonunique corrected normal section {edge["id"]}:{i}')
            metric=section_metrics((cs[0]-point)@np.array([u,v]).T)
            old_radius=old['radii_mm'][int(indices[i])]
            radii.append(old_radius+float(weight[i])*(metric['area_equivalent_radius_mm']-old_radius))
        edge['radii_mm']=radii;edge['geometry_kind']='estimated';edge['evidence_status']='synthetic_estimate'
        changes.append(dict(edge_id=edge['id'],original_edge=old,locked_endpoints=locked,
            max_displacement_mm=displacement,source_id=profile['source_id'],
            retained_original_indices=indices.tolist(),original_to_new_index=(np.cumsum(keep)-1).tolist()))
    candidate['full_source_profile']=dict(parent_revision=revision,source_report_sha256=hashlib.sha256(source_raw).hexdigest(),
        changes=changes,original_nodes=case['nodes'],policy='axial area centroids then corrected-path normal area radii; connected endpoint 5 mm taper',
        anatomical_acceptance='UNKNOWN')
    candidate['generation']=dict(seed=case['generation']['seed'],generator_version='full-source-profile-1',
        config=dict(parent_case_revision=revision,parent_generation=case['generation']))
    for key in ('quality','geometry_quality','surface_quality'):candidate.pop(key,None)
    candidate['synthetic_route_inspection'].update(source_nodes_preserved=False,source_edges_preserved=False,
        collision_check='NOT RUN',surface_junction_check='NOT RUN')
    validate_case(candidate)
    selected={c['edge_id']:c for c in changes}
    for edge in candidate['edges']:
        old=old_edges[edge['id']]
        if edge['id'] not in selected:
            if old!=edge:raise ValueError('unselected edge changed')
            continue
        for endpoint in selected[edge['id']]['locked_endpoints']:
            ids=(0,1) if endpoint=='start' else (-2,-1)
            if any(edge['centerline_mm'][i]!=old['centerline_mm'][i] or
                   edge['radii_mm'][i]!=old['radii_mm'][i] for i in ids):
                raise ValueError('connected endpoint chord or radius changed')
    continuity=inspect_bridge_continuity(candidate,max_angle_deg=3.,max_radius_jump_mm=0.)
    focus=[c['edge_id'] for c in changes];screens=[];bounds=[]
    for item in (case,candidate):
        screens.append(screen_nonincident_clearance(item,[e['id'] for e in item['edges'] if e['centerline_mm'] is not None],
            focus_edge_ids=focus,margin_mm=1.2,max_segment_pairs=20_000_000))
        if screens[-1].get('reason')=='pair_budget_exhausted':raise ValueError('budget exhausted')
        a,b=[next(e for e in item['edges'] if e['id']==i) for i in focus]
        p,q=np.array(a['centerline_mm']),np.array(b['centerline_mm'])
        bounds.append(min(segment_distance(p[i],p[i+1],q[j],q[j+1])-max(a['radii_mm'][i:i+2])-max(b['radii_mm'][j:j+2])
                          for i in range(len(p)-1) for j in range(len(q)-1)))
    pairs=[{tuple(sorted(r['edges'])) for r in s['potential_contacts']} for s in screens]
    out=ROOT/'exports/synthetic-full-iliac-profiles';out.mkdir(parents=True,exist_ok=True)
    new_revision=store_snapshot(out/'case.snapshot.json',candidate)
    if parent_path.read_bytes()!=raw or source_path.read_bytes()!=source_raw:raise ValueError('input changed')
    report=dict(schema='vv-toolbox.full-iliac-profile-candidate/1',parent_revision=revision,case_revision=new_revision,
        changes=[{k:v for k,v in c.items() if k!='original_edge'} for c in changes],continuity=continuity,
        target_pair_capsule_bounds_mm=bounds,before_screen=screens[0],after_screen=screens[1],
        new_pairs=[list(p) for p in sorted(pairs[1]-pairs[0])],removed_pairs=[list(p) for p in sorted(pairs[0]-pairs[1])],
        inputs_unchanged=True,connected_endpoint_chords_and_radii_preserved=True,unselected_edges_preserved=True,
        final_mesh_collision='NOT RUN',anatomical_acceptance='UNKNOWN',default_app_applied=False)
    (ROOT/'docs/evidence/full-iliac-profile-candidate.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ['case_revision','target_pair_capsule_bounds_mm','new_pairs','removed_pairs']}))


if __name__=='__main__':main()
