"""Build a bounded source-section-guided candidate; keep source and radii intact."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import numpy as np
import trimesh
from matplotlib.path import Path as PolygonPath
from vv_toolbox.atlas import load_atlas
from vv_toolbox.case_io import load_case
from vv_toolbox.case_contract import validate_case
from vv_toolbox.geometry_quality import screen_nonincident_clearance, segment_distance
from vv_toolbox.junction_continuity import inspect_bridge_continuity
from build_synthetic_arch_carotid_case import store_snapshot

ROOT=Path(__file__).resolve().parents[1]


def area_centroid(contour):
    """Centroid of one closed simple planar contour, independent of winding."""
    xy=np.asarray(contour,dtype=float)[:,:2]
    if len(xy)<4 or not np.allclose(xy[0],xy[-1],rtol=0,atol=1e-7):
        raise ValueError('one closed contour required')
    a,b=xy[:-1],xy[1:]
    cross=a[:,0]*b[:,1]-b[:,0]*a[:,1]
    twice_area=float(cross.sum())
    if abs(twice_area)<1e-9:
        raise ValueError('degenerate section')
    centroid=((a+b)*cross[:,None]).sum(axis=0)/(3*twice_area)
    if not PolygonPath(xy).contains_point(centroid):
        raise ValueError('section centroid outside polygon')
    return centroid


def main():
    path=ROOT/'exports/synthetic-common-iliac-trunk/case.snapshot.json'
    raw=path.read_bytes();case,revision=load_case(path)
    evidence_path=ROOT/'docs/evidence/iliac-contact-source-sections.json'
    evidence_raw=evidence_path.read_bytes();evidence=json.loads(evidence_raw)
    atlas=load_atlas()
    if evidence['case_revision']!=revision or evidence['source_archive_sha256']!=atlas.metadata['sha256']:
        raise ValueError('source evidence mismatch')
    part=next(p for p in atlas.meshes if p['id']=='FJ3617')
    fingerprint=hashlib.sha256(np.asarray(part['vertices']).tobytes()+np.asarray(part['faces']).tobytes()).hexdigest()
    if fingerprint!=evidence['source_mesh_fingerprints']['FJ3617']:
        raise ValueError('source mesh differs')
    mesh=trimesh.Trimesh(part['vertices'],part['faces'],process=False)
    original=next(e for e in case['edges'] if e['id']=='FJ3617:e0')
    points=np.array(original['centerline_mm']);changed=points.copy();samples=[]
    # Fixed local support around the prior witness; no radius shrink or adaptive search.
    config=dict(source_id='FJ3617',edge_id=original['id'],z_support_mm=[870.,890.],
                full_weight_z_mm=[875.,885.],max_displacement_mm=3.,radii_policy='unchanged',
                evidence_ref='docs/evidence/iliac-contact-source-sections.json')
    for i,p in enumerate(points):
        if i in (0,1,len(points)-2,len(points)-1) or not 870<p[2]<890:
            continue
        section=mesh.section(plane_origin=[0,0,p[2]],plane_normal=[0,0,1])
        contours=[] if section is None else section.discrete
        if len(contours)!=1:
            raise ValueError('ambiguous source section at '+str(i))
        center=area_centroid(contours[0])
        t=float(np.clip(min(p[2]-870,890-p[2])/5,0,1));weight=t*t*(3-2*t)
        changed[i,:2]=p[:2]+weight*(center-p[:2])
        samples.append(dict(index=i,z_mm=float(p[2]),weight=weight,section_centroid_xy_mm=center.tolist(),
            before_inside_section=bool(PolygonPath(contours[0][:,:2]).contains_point(p[:2])),
            after_inside_section=bool(PolygonPath(contours[0][:,:2]).contains_point(changed[i,:2]))))
    displacement=float(np.linalg.norm(changed-points,axis=1).max())
    if not samples or displacement>config['max_displacement_mm']:
        raise ValueError('empty or excessive source-guided correction')
    candidate=deepcopy(case);candidate['case_id']='R-testicular-source-centroid-candidate'
    edge=next(e for e in candidate['edges'] if e['id']==original['id'])
    edge['centerline_mm']=changed.tolist();edge['geometry_kind']='estimated';edge['evidence_status']='synthetic_estimate'
    candidate['source_section_correction']=dict(parent_revision=revision,config=config,original_edge=original,
        measured_displacement_mm=displacement,anatomical_acceptance='UNKNOWN',
        parent_quality_not_applicable={k:candidate.pop(k) for k in ('quality','geometry_quality','surface_quality') if k in candidate})
    candidate['generation']=dict(seed=case['generation']['seed'],generator_version='source-section-centroid-1',
        config=dict(parent_case_revision=revision,parameters=config,parent_generation=case['generation']))
    previous=candidate.get('synthetic_route_inspection')
    if previous:
        for key in ('collision_check','surface_junction_check'): previous[key]='NOT RUN'
        previous['source_edges_preserved']=False
    validate_case(candidate)
    continuity=inspect_bridge_continuity(candidate,max_angle_deg=3.,max_radius_jump_mm=0.)
    screens=[]
    for item in (case,candidate):
        screen=screen_nonincident_clearance(item,[e['id'] for e in item['edges'] if e['centerline_mm'] is not None],
            focus_edge_ids=[original['id']],margin_mm=1.2,max_segment_pairs=20_000_000)
        if screen.get('reason')=='pair_budget_exhausted':raise ValueError('budget exhausted')
        screens.append(screen)
    pairs=[{tuple(sorted(r['edges'])) for r in s['potential_contacts']} for s in screens]
    # Resolve the target pair completely; first threshold witnesses can remain
    # identical even when the negative-overlap location improves.
    target_bounds=[]
    for item in (case,candidate):
        target=next(e for e in item['edges'] if e['id']=='R-EIA-retained')
        vessel=next(e for e in item['edges'] if e['id']==original['id'])
        p,q=np.array(target['centerline_mm']),np.array(vessel['centerline_mm'])
        rp,rq=np.array(target['radii_mm']),np.array(vessel['radii_mm'])
        best=(float('inf'),None)
        for i in range(len(p)-1):
            for j in range(len(q)-1):
                bound=segment_distance(p[i],p[i+1],q[j],q[j+1])-max(rp[i:i+2])-max(rq[j:j+2])
                if bound<best[0]:best=(float(bound),[i,j])
        target_bounds.append(dict(minimum_capsule_bound_mm=best[0],intervals=best[1],
                                  checked_segment_pairs=(len(p)-1)*(len(q)-1)))
    out=ROOT/'exports/synthetic-testicular-recentered'
    out.mkdir(parents=True,exist_ok=True);new_revision=store_snapshot(out/'case.snapshot.json',candidate)
    if path.read_bytes()!=raw or evidence_path.read_bytes()!=evidence_raw:raise ValueError('input changed')
    report=dict(schema='vv-toolbox.source-section-correction/1',parent_revision=revision,case_revision=new_revision,
        config=config,source_mesh_fingerprint=fingerprint,samples=samples,max_displacement_mm=displacement,
        endpoint_chords_unchanged=bool(np.array_equal(points[[0,1,-2,-1]],changed[[0,1,-2,-1]])),
        radii_unchanged=edge['radii_mm']==original['radii_mm'],continuity=continuity,
        before_screen=screens[0],after_screen=screens[1],new_pairs=[list(p) for p in sorted(pairs[1]-pairs[0])],
        target_pair_complete_bounds=target_bounds,
        removed_pairs=[list(p) for p in sorted(pairs[0]-pairs[1])],inputs_unchanged=True,
        final_mesh_collision='NOT RUN',anatomical_acceptance='UNKNOWN',default_app_applied=False)
    (ROOT/'docs/evidence/testicular-source-correction.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(revision=new_revision,samples=len(samples),max_displacement_mm=displacement,
        new_pairs=report['new_pairs'],removed_pairs=report['removed_pairs'],continuity=continuity['status'])))


if __name__=='__main__':main()
