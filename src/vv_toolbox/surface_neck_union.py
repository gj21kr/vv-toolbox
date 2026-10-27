"""Experimental voxel union of a nonplanar sac and its baseline parent profile."""
import math
import numpy as np
import trimesh
from scipy.ndimage import label
from skimage.measure import marching_cubes
from .surface_neck_loft import build_surface_neck_loft
from .saccular_surface import _parent_field, _neck_grid_bounds
from .voxel_output import Grid, Surface, voxelize
from .surface_origin import label_union_faces


def build_surface_neck_union(case,spec,*,spacing_mm,ray_half_span_mm,ray_step_mm,
                             max_grid_voxels=3_000_000):
    if type(spacing_mm) not in (int,float) or not math.isfinite(spacing_mm) or spacing_mm<=0:
        raise ValueError('positive finite spacing required')
    if type(max_grid_voxels) is not int or not 1<=max_grid_voxels<=3_000_000:
        raise ValueError('grid budget must be between 1 and 3000000')
    p,neck=spec['parameters'],spec['neck']
    if spacing_mm>min(p['neck_width_mm'],p['neck_depth_mm'])/4:
        raise ValueError('at least four samples across neck axes required')
    v,f,loft=build_surface_neck_loft(case,spec,ray_half_span_mm=ray_half_span_mm,
                                    ray_step_mm=ray_step_mm,refine_neck=True)
    edge=next(e for e in case['edges'] if e['id']==p['edge_id'])
    points,radii=np.asarray(edge['centerline_mm']),np.asarray(edge['radii_mm'])
    basis=np.column_stack([neck[k] for k in ('width_axis','depth_axis','normal')])
    center=np.asarray(neck['center_mm'])
    # Temporary cap lies towards the original internal anchor and is buried
    # by the parent union. Check vertices, midpoints and centroids explicitly.
    anchor=np.asarray(spec['parent_anchor']['position_mm'])
    n=loft['boundary_vertex_count']
    buried_start=len(v)
    buried=v[:n]-p['blending_extent_mm']*np.asarray(neck['normal'])
    cap_id=buried_start+n
    v=np.vstack([v,buried,anchor])
    cap=[]
    for i in range(n):
        j=(i+1)%n
        cap.extend([[j,i,buried_start+i],[j,buried_start+i,buried_start+j],
                    [buried_start+j,buried_start+i,cap_id]])
    cap=np.asarray(cap)
    triangles=v[cap]
    probes=np.vstack([triangles.mean(axis=1),
                       ((triangles+np.roll(triangles,1,axis=1))/2).reshape(-1,3),
                       v[np.unique(cap)]])
    cap_field=_parent_field(probes,points,radii)
    if np.any(cap_field>1e-6):
        worst=int(np.argmax(cap_field))
        raise ValueError(f'temporary cap escapes parent at sampled locations: '
                         f'max_field_mm={float(cap_field[worst]):.12g}, '
                         f'outside_samples={int(np.count_nonzero(cap_field>1e-6))}/{len(probes)}, '
                         f'probe_indices={np.flatnonzero(cap_field>1e-6).tolist()}, '
                         f'cap_triangle_count={len(cap)}, '
                         f'witness_mm={probes[worst].tolist()}')
    f=np.vstack([f,cap])
    solid=trimesh.Trimesh(vertices=v,faces=f,process=False)
    if not solid.is_volume:
        raise ValueError('temporary sac closure is not a positive closed solid')
    local=(v-center)@basis
    low,high=_neck_grid_bounds(points,radii,neck,p,spacing_mm)
    low=np.minimum(low,np.floor(local.min(0)/spacing_mm)*spacing_mm-3*spacing_mm)
    high=np.maximum(high,np.ceil(local.max(0)/spacing_mm)*spacing_mm+3*spacing_mm)
    shape=np.rint((high-low)/spacing_mm).astype(int)+1
    count=math.prod(shape.tolist())
    if count>max_grid_voxels:
        raise ValueError('union grid budget exceeded')
    grid=Grid(tuple(int(x) for x in shape[::-1]),(spacing_mm,)*3,tuple(low.tolist()),'internal-neck-frame')
    volume=voxelize([Surface(1,0,'estimated',local,f,grid.frame_id,'temporary sac closure')],
                    grid,max_bytes=256*1024**2)
    sac_occupancy=volume.foreground.copy()
    del volume
    parent_occupancy=np.zeros_like(sac_occupancy)
    flat=parent_occupancy.reshape(-1)
    for start in range(0,count,8192):
        ids=np.arange(start,min(start+8192,count))
        xyz=np.array(np.unravel_index(ids,grid.shape_zyx)).T[:,::-1]*spacing_mm+low
        world=xyz@basis.T+center
        flat[ids] = _parent_field(world,points,radii)<=0
    occupancy=parent_occupancy | sac_occupancy
    if any(np.any(np.take(occupancy,i,axis=d)) for d in range(3) for i in (0,-1)):
        raise ValueError('union reaches grid boundary')
    _,components=label(occupancy)
    if components!=1:
        raise ValueError('sampled union lumen disconnected')
    vertices,faces,_,_=marching_cubes(occupancy.astype(np.float32),.5,spacing=(spacing_mm,)*3,
                                     allow_degenerate=False)
    origin=label_union_faces(vertices,faces,parent_occupancy,sac_occupancy,spacing_mm)
    vertices=(vertices[:,::-1]+low)@basis.T+center
    mesh=trimesh.Trimesh(vertices=vertices,faces=faces,process=False)
    if mesh.volume<0:
        faces=faces[:,::-1]
        mesh=trimesh.Trimesh(vertices=vertices,faces=faces,process=False)
    if not mesh.is_volume or len(mesh.split(only_watertight=False))!=1:
        raise ValueError('union surface is not one closed volume')
    return vertices,faces,dict(schema='vv-toolbox.surface-neck-union/1',status='CANDIDATE',
        case_revision=spec['case_revision'],edge_id=edge['id'],frame=case['frame'],
        spacing_mm=spacing_mm,grid_shape_xyz=shape.tolist(),voxel_count=count,
        attachment=loft['attachment'],temporary_cap_sample_count=len(probes),
        surface_origin=origin,
        checks=dict(sampled_cap_burial='PASS',sampled_lumen_connectivity='PASS',
                    single_closed_surface='PASS',neck_dimensions='NOT RUN',
                    smooth_junction='NOT RUN',context_collision='NOT RUN',clinical_validity='NOT RUN'),
        limitation='Binary sampled union; temporary cap is only sample-checked. Original patch rim is not exact after remeshing. Not accepted anatomy or a clinically validated lesion.')
