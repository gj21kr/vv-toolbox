"""Surface-following neck contour proposals; separate from planar sac designs."""
from copy import deepcopy
import hashlib
import json
import math
import numpy as np
from .saccular import validate_saccular_spec
from .saccular_surface import _parent_field


def _project_rim(rim,normal,offsets,points,radii):
    count=len(offsets)
    rays=rim[:,None,:]+offsets[None,:,None]*normal
    values=_parent_field(rays.reshape(-1,3),points,radii).reshape(len(rim),count)
    if np.any(values[:,0]>=0) or np.any(values[:,-1]<=0):
        raise ValueError('ray endpoints must bracket inside-to-outside parent crossing')
    inside=values<0
    exits=inside[:,:-1]&~inside[:,1:]
    entries=~inside[:,:-1]&inside[:,1:]
    if np.any(exits.sum(axis=1)!=1) or np.any(entries):
        raise ValueError('multiple parent crossings along sampled neck ray')
    indices=exits.argmax(axis=1)
    low,high=offsets[indices].copy(),offsets[indices+1].copy()
    for _ in range(40):
        middle=(low+high)/2
        field=_parent_field(rim+middle[:,None]*normal,points,radii)
        mask=field<0
        low=np.where(mask,middle,low)
        high=np.where(mask,high,middle)
    return (low+high)/2


def propose_surface_neck(case, spec, *, ray_half_span_mm, ray_step_mm,
                         refine_chords=False):
    """Find an outward baseline-profile crossing along each declared rim ray.

    Projected ellipse axes remain fixed; 3D contour heights are new estimates.
    Sampled crossing uniqueness is not continuous topology certification.
    """
    validate_saccular_spec(spec,case)
    if type(refine_chords) is not bool:
        raise ValueError('refine_chords must be boolean')
    for value in (ray_half_span_mm,ray_step_mm):
        if type(value) not in (int,float) or not math.isfinite(value) or value<=0:
            raise ValueError('positive finite ray span and step required')
    count=math.ceil(2*ray_half_span_mm/ray_step_mm)+1
    if not 3<=count<=4097:
        raise ValueError('ray sampling requires between 3 and 4097 points')
    edge=next(e for e in case['edges'] if e['id']==spec['parameters']['edge_id'])
    points,radii=np.asarray(edge['centerline_mm']),np.asarray(edge['radii_mm'])
    neck=spec['neck']
    rim,normal=np.asarray(neck['curve_mm']),np.asarray(neck['normal'])
    offsets=np.linspace(-ray_half_span_mm,ray_half_span_mm,count)
    angles=np.arange(len(rim))*2*np.pi/len(rim)
    heights=_project_rim(rim,normal,offsets,points,radii)
    curve=rim+heights[:,None]*normal
    rounds=0
    for iteration in range(13):
        samples=np.stack([curve+t*(np.roll(curve,-1,axis=0)-curve)
                          for t in (.25,.5,.75)],axis=1)
        chord_field=_parent_field(samples.reshape(-1,3),points,radii).reshape(len(curve),3)
        bad=np.any(chord_field>1e-6,axis=1)
        if not refine_chords or not bad.any():
            break
        if iteration==12 or len(curve)+int(bad.sum())>512:
            raise ValueError('neck chord refinement budget exceeded')
        next_angles=np.r_[angles[1:],2*np.pi]
        added=(angles[bad]+next_angles[bad])/2
        p=spec['parameters']
        added_rim=(np.asarray(neck['center_mm'])+
                   np.cos(added)[:,None]*np.asarray(neck['width_axis'])*p['neck_width_mm']/2+
                   np.sin(added)[:,None]*np.asarray(neck['depth_axis'])*p['neck_depth_mm']/2)
        added_heights=_project_rim(added_rim,normal,offsets,points,radii)
        angles=np.r_[angles,added]
        heights=np.r_[heights,added_heights]
        curve=np.vstack([curve,added_rim+added_heights[:,None]*normal])
        order=np.argsort(angles)
        angles,heights,curve=angles[order],heights[order],curve[order]
        rounds+=1
    residual=float(np.max(np.abs(_parent_field(curve,points,radii))))
    if not np.isfinite(curve).all() or residual>1e-7:
        raise ValueError('surface crossing refinement failed')
    basis=np.column_stack([neck['width_axis'],neck['depth_axis'],normal])
    local=(curve-np.asarray(neck['center_mm']))@basis
    return dict(schema='vv-toolbox.surface-neck-proposal/1',status='CANDIDATE',
        case_revision=spec['case_revision'],base_model_id=case['base_model_id'],
        frame=deepcopy(case['frame']),edge_id=edge['id'],
        planar_specification_sha256=hashlib.sha256(json.dumps(spec,sort_keys=True,
            separators=(',',':'),allow_nan=False).encode()).hexdigest(),
        method='per-rim-ray outward parent-profile crossing; bisection',
        ray_half_span_mm=ray_half_span_mm,ray_step_mm=ray_step_mm,
        actual_ray_step_mm=float(offsets[1]-offsets[0]),ray_sample_count=count,
        curve_mm=curve.tolist(),normal_offsets_mm=heights.tolist(),
        angles_radians=angles.tolist(),
        chord_refinement=dict(enabled=refine_chords,rounds=rounds,
            vertex_count=len(curve),sample_fractions=[.25,.5,.75],
            tolerance_mm=1e-6,max_parent_field_mm=float(chord_field.max()),
            status='PASS' if not bad.any() else 'FAIL'),
        projected_width_depth_mm=np.ptp(local[:,:2],axis=0).tolist(),
        normal_offset_range_mm=[float(heights.min()),float(heights.max())],
        parent_field_max_abs_residual_mm=residual,
        checks=dict(sampled_crossing='PASS',surface_residual='PASS',
                    continuous_crossing_uniqueness='NOT RUN',generated_sac='NOT RUN',
                    source_mesh_agreement='NOT RUN',clinical_validity='NOT RUN'),
        limitation='Nonplanar attachment proposal on derived parent profile. Original planar sac is unchanged; no accepted lesion or generated sac.')
