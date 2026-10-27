"""Open sac patch from a recomputed nonplanar neck; not a parent-lumen union."""
import math
import numpy as np
import trimesh
from .surface_neck import propose_surface_neck
from .saccular_surface import _parent_field


def build_surface_neck_loft(case,spec,*,ray_half_span_mm,ray_step_mm,rings=96,refine_neck=False):
    if type(rings) is not int or not 8<=rings<=1024:
        raise ValueError('rings must be an integer between 8 and 1024')
    proposal=propose_surface_neck(case,spec,ray_half_span_mm=ray_half_span_mm,
                                 ray_step_mm=ray_step_mm,refine_chords=refine_neck)
    p,neck=spec['parameters'],spec['neck']
    h=p['height_perpendicular_mm']
    offsets=np.asarray(proposal['normal_offsets_mm'])
    # z(u)=u+offset*(1-u/h)^2 has positive derivative under this condition.
    if 2*max(0.,float(offsets.max()))>=h:
        raise ValueError('neck displacement prevents monotone loft height')
    theta=np.asarray(proposal['angles_radians'])
    z=np.linspace(0,h,rings+1)[:-1]
    axes=[]
    for key in ('width','depth'):
        a,r=p[f'dome_{key}_mm']/2,p[f'neck_{key}_mm']/2
        q=math.sqrt(max(0.,1-(r/a)**2))
        c=h/(1+q)
        axes.append(a*np.sqrt(np.maximum(0.,1-((z-c*q)/c)**2)))
    local=np.stack([axes[0][:,None]*np.cos(theta)[None,:],
                    axes[1][:,None]*np.sin(theta)[None,:],
                    z[:,None]+(1-z[:,None]/h)**2*offsets[None,:]],axis=-1)
    basis=np.column_stack([neck['width_axis'],neck['depth_axis'],neck['normal']])
    vertices=local.reshape(-1,3)@basis.T+np.asarray(neck['center_mm'])
    n=len(offsets)
    vertices[:n]=proposal['curve_mm']  # Exact shared attachment boundary.
    tip=len(vertices)
    vertices=np.vstack([vertices,np.asarray(neck['center_mm'])+h*np.asarray(neck['normal'])])
    faces=[]
    for row in range(rings-1):
        for i in range(n):
            j=(i+1)%n
            a,b,c,d=row*n+i,row*n+j,(row+1)*n+i,(row+1)*n+j
            faces.extend([[a,b,c],[b,d,c]])
    for i in range(n):
        faces.append([(rings-1)*n+i,(rings-1)*n+(i+1)%n,tip])
    faces=np.asarray(faces,dtype=np.int64)
    mesh=trimesh.Trimesh(vertices=vertices,faces=faces,process=False)
    if not mesh.is_winding_consistent:
        raise ValueError('loft winding is inconsistent')
    if len(mesh.split(only_watertight=False))!=1 or np.any(mesh.area_faces<=0):
        raise ValueError('loft is disconnected or degenerate')
    counts=np.bincount(mesh.edges_unique_inverse)
    boundary=mesh.edges_unique[counts==1]
    if len(boundary)!=n or set(boundary.ravel())!=set(range(n)) or np.any(counts>2):
        raise ValueError('loft must have only the original neck boundary')
    edge=next(e for e in case['edges'] if e['id']==p['edge_id'])
    baseline=_parent_field(vertices[n:],np.asarray(edge['centerline_mm']),
                           np.asarray(edge['radii_mm']))
    inside=int(np.count_nonzero(baseline < -1e-6))
    return vertices,faces,dict(schema='vv-toolbox.surface-neck-loft/1',status='CANDIDATE',
        case_revision=spec['case_revision'],attachment=proposal,rings=rings,
        boundary_vertex_count=n,triangle_count=len(faces),
        parent_interior_vertex_count=inside,
        parent_field_min_mm=float(baseline.min()),
        checks=dict(boundary_identity='PASS',single_patch='PASS',
                    sampled_parent_separation='FAIL' if inside else 'PASS',
                    closed_lumen='NOT RUN',triangle_collision='NOT RUN',
                    smooth_parent_junction='NOT RUN',clinical_validity='NOT RUN'),
        limitation='Open sac patch only; no parent excision, lumen union, mask or accepted lesion. Vertex clearance is not triangle collision clearance.')
