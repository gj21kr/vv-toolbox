"""Fit local synthetic radii to measured native normal-section area."""
from copy import deepcopy
import json
from pathlib import Path
import numpy as np
import trimesh
from vv_toolbox.atlas import load_atlas
from vv_toolbox.case_io import load_case
from vv_toolbox.case_contract import validate_case
from vv_toolbox.geometry_quality import screen_nonincident_clearance, segment_distance
from vv_toolbox.junction_continuity import inspect_bridge_continuity
from build_synthetic_arch_carotid_case import store_snapshot
from inspect_iliac_normal_sections import section_metrics

ROOT=Path(__file__).resolve().parents[1]


def main():
    path=ROOT/'exports/synthetic-testicular-recentered/case.snapshot.json'
    raw=path.read_bytes();case,revision=load_case(path)
    evidence=json.loads((ROOT/'docs/evidence/iliac-normal-sections.json').read_text())
    atlas=load_atlas()
    if evidence['case_revision']!=revision or atlas.metadata['sha256']!=evidence['source_archive_sha256']:
        raise ValueError('normal-section evidence differs')
    mapping={'R-EIA-retained':'FJ3567','FJ3617:e0':'FJ3617'}
    candidate=deepcopy(case);candidate['case_id']='R-iliac-native-area-radius-candidate'
    records=[]
    config=dict(z_support_mm=[870.,890.],full_weight_z_mm=[875.,885.],
                radius_method='sqrt(normal-section-area/pi)',max_radius_change_mm=2.,
                plane_tangent_half_chord_mm=2.,source_mapping=mapping)
    for edge in candidate['edges']:
        if edge['id'] not in mapping:continue
        part=next(p for p in atlas.meshes if p['id']==mapping[edge['id']])
        mesh=trimesh.Trimesh(part['vertices'],part['faces'],process=False)
        old=deepcopy(edge);p=np.array(edge['centerline_mm'])
        arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))]
        for i,point in enumerate(p):
            if i in (0,1,len(p)-2,len(p)-1) or not 870<point[2]<890:continue
            normal=np.array([np.interp(min(arc[-1],arc[i]+2),arc,p[:,k])-
                             np.interp(max(0,arc[i]-2),arc,p[:,k]) for k in range(3)])
            normal/=np.linalg.norm(normal)
            u=np.cross(normal,np.eye(3)[int(np.argmin(abs(normal)))]);u/=np.linalg.norm(u)
            v=np.cross(normal,u)
            section=mesh.section(plane_origin=point,plane_normal=normal)
            cs=[] if section is None else section.discrete
            if len(cs)!=1:raise ValueError('ambiguous normal section')
            measured=section_metrics((cs[0]-point)@np.array([u,v]).T)
            target=measured['area_equivalent_radius_mm'];radius=old['radii_mm'][i]
            t=float(np.clip(min(point[2]-870,890-point[2])/5,0,1));weight=t*t*(3-2*t)
            value=radius+weight*(target-radius)
            if abs(value-radius)>config['max_radius_change_mm']:raise ValueError('radius change bound exceeded')
            edge['radii_mm'][i]=value
            records.append(dict(edge_id=edge['id'],index=i,original_radius_mm=radius,
                                target_radius_mm=target,modified_radius_mm=value,weight=weight))
        edge['geometry_kind']='estimated';edge['evidence_status']='synthetic_estimate'
        edge.setdefault('source_radius_history',[]).append(dict(parent_revision=revision,original_edge=old,config=config))
    candidate['generation']=dict(seed=case['generation']['seed'],generator_version='native-normal-area-radius-1',
        config=dict(parent_case_revision=revision,parameters=config,parent_generation=case['generation']))
    for key in ('quality','geometry_quality','surface_quality'):candidate.pop(key,None)
    previous=candidate.get('synthetic_route_inspection')
    if previous:
        previous.update(collision_check='NOT RUN',surface_junction_check='NOT RUN',source_edges_preserved=False)
    validate_case(candidate)
    for old,new in zip(case['edges'],candidate['edges']):
        if old['id'] not in mapping:
            if old!=new:raise ValueError('unselected edge changed')
        elif old['centerline_mm']!=new['centerline_mm'] or any(
                old['radii_mm'][i]!=new['radii_mm'][i] for i in (0,1,-2,-1)):
            raise ValueError('centerline or frozen endpoint radius changed')
    if candidate['nodes']!=case['nodes']:raise ValueError('nodes changed')
    continuity=inspect_bridge_continuity(candidate,max_angle_deg=3.,max_radius_jump_mm=0.)
    screens=[];bounds=[]
    for item in (case,candidate):
        screens.append(screen_nonincident_clearance(item,[e['id'] for e in item['edges'] if e['centerline_mm'] is not None],
            focus_edge_ids=list(mapping),margin_mm=1.2,max_segment_pairs=20_000_000))
        if screens[-1].get('reason')=='pair_budget_exhausted':raise ValueError('budget exhausted')
        a,b=[next(e for e in item['edges'] if e['id']==ident) for ident in mapping]
        p,q=np.array(a['centerline_mm']),np.array(b['centerline_mm']);best=(float('inf'),None)
        for i in range(len(p)-1):
            for j in range(len(q)-1):
                gap=segment_distance(p[i],p[i+1],q[j],q[j+1])-max(a['radii_mm'][i:i+2])-max(b['radii_mm'][j:j+2])
                if gap<best[0]:best=(float(gap),[i,j])
        bounds.append(dict(minimum_capsule_bound_mm=best[0],intervals=best[1]))
    pairs=[{tuple(sorted(r['edges'])) for r in s['potential_contacts']} for s in screens]
    i,j=bounds[0]['intervals']
    previous_location_after=segment_distance(p[i],p[i+1],q[j],q[j+1])-max(a['radii_mm'][i:i+2])-max(b['radii_mm'][j:j+2])
    out=ROOT/'exports/synthetic-iliac-source-radii';out.mkdir(parents=True,exist_ok=True)
    new_revision=store_snapshot(out/'case.snapshot.json',candidate)
    if path.read_bytes()!=raw:raise ValueError('input changed')
    report=dict(schema='vv-toolbox.iliac-source-radius-fit/1',parent_revision=revision,case_revision=new_revision,
        config=config,records=records,target_pair_bounds=bounds,continuity=continuity,
        previous_minimum_location_after_bound_mm=float(previous_location_after),
        centerlines_nodes_and_unselected_edges_unchanged=True,endpoint_radii_unchanged=True,
        before_screen=screens[0],after_screen=screens[1],new_pairs=[list(p) for p in sorted(pairs[1]-pairs[0])],
        removed_pairs=[list(p) for p in sorted(pairs[0]-pairs[1])],input_unchanged=True,
        final_mesh_collision='NOT RUN',anatomical_acceptance='UNKNOWN',default_app_applied=False)
    (ROOT/'docs/evidence/iliac-source-radius-fit.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(revision=new_revision,bounds=bounds,changed_samples=len(records),
                          new_pairs=report['new_pairs'],removed_pairs=report['removed_pairs'],continuity=continuity['status'])))


if __name__=='__main__':main()
