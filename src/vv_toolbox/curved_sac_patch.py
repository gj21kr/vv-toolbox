"""Open dome patch bounded by a verified projected rim; no lumen union."""
import numpy as np
import trimesh
from .bifurcation_rim_continuity import inspect_projected_rim
from .mesh_self_contact import inspect_self_contact


def build_curved_sac_patch(case,spec,projection,*,rim_tolerance_mm,axial_rings=32,max_contact_pairs=2000000):
    if type(axial_rings) is not int or not 4<=axial_rings<=256:
        raise ValueError('Axial rings must be an integer from 4 to 256')
    inspection=inspect_projected_rim(case,spec,projection,tolerance_mm=rim_tolerance_mm)
    if inspection['status']!='PASS':raise ValueError('Projected rim continuity did not pass')
    return _build_rim_patch(spec,np.asarray(projection['curve_mm']),inspection,
                            axial_rings=axial_rings,max_contact_pairs=max_contact_pairs)


def _build_rim_patch(spec,rim,inspection,*,axial_rings=32,max_contact_pairs=2000000):
    if type(axial_rings) is not int or not 4<=axial_rings<=256:
        raise ValueError('Axial rings must be an integer from 4 to 256')
    p,neck=spec['parameters'],spec['neck']
    center=np.asarray(neck['center_mm'])
    basis=np.column_stack([neck['width_axis'],neck['depth_axis'],neck['normal']])
    rim=np.asarray(rim);local=(rim-center)@basis
    h=p['height_perpendicular_mm']
    theta=np.arctan2(local[:,1]/p['neck_depth_mm'],local[:,0]/p['neck_width_mm'])
    profiles=[]
    for axis in ('width','depth'):
        a=p[f'dome_{axis}_mm']/2;r=p[f'neck_{axis}_mm']/2
        q=np.sqrt(max(0.,1-(r/a)**2));c=h/(1+q)
        profiles.append((a,c,c*q))
    levels=sorted(set(np.linspace(0,h,axial_rings+1)[:-1].tolist()+[v[2] for v in profiles]))
    rings=[]
    for z in levels:
        radii=[a*np.sqrt(max(0.,1-((z-mid)/c)**2)) for a,c,mid in profiles]
        heights=z+local[:,2]*(1-z/h)**2
        rings.append(np.column_stack([radii[0]*np.cos(theta),radii[1]*np.sin(theta),heights]))
    ring_array=np.asarray(rings)
    if np.any(np.diff(ring_array[:,:,2],axis=0)<=0) or np.any(ring_array[:,:,2]>=h):
        raise ValueError('Curved rim height causes a folded or overshooting dome')
    vertices=np.vstack([ring_array.reshape(-1,3),[0,0,h]])@basis.T+center
    vertices[:len(rim)]=rim  # Preserve the supplied boundary bit for bit.
    faces=[];n=len(rim)
    for layer in range(len(rings)-1):
        for i in range(n):
            a=layer*n+i;b=layer*n+(i+1)%n;c=a+n;d=b+n
            faces.extend([[a,b,c],[b,d,c]])
    apex=len(vertices)-1;last=(len(rings)-1)*n
    faces.extend([[last+i,last+(i+1)%n,apex] for i in range(n)])
    faces=np.asarray(faces,dtype=np.int64)
    mesh=trimesh.Trimesh(vertices=vertices,faces=faces,process=False)
    counts=np.bincount(mesh.edges_unique_inverse)
    boundary=mesh.edges_unique[counts==1]
    expected={tuple(sorted((i,(i+1)%n))) for i in range(n)}
    if (set(map(tuple,np.sort(boundary,axis=1)))!=expected or np.any(counts>2)
            or np.any(mesh.area_faces<=1e-12) or not mesh.is_winding_consistent
            or mesh.euler_number!=1):
        raise ValueError('Dome patch is not an oriented disk with exactly the declared rim')
    measured=np.r_[np.ptp((vertices-center)@basis,axis=0)[:2],np.max((vertices-center)@basis[:,2])]
    requested=np.array([p['dome_width_mm'],p['dome_depth_mm'],h])
    if not np.allclose(measured,requested,atol=1e-6,rtol=0):raise ValueError('Dome patch dimensions differ from requested dimensions')
    self_contact=inspect_self_contact(vertices,faces,max_pairs=max_contact_pairs)
    if self_contact['status']!='NO_CONTACT_DETECTED':
        raise ValueError('Dome patch self-contact inspection failed or is incomplete: '+self_contact['status'])
    return vertices,faces,dict(schema='vv-toolbox.curved-sac-patch/1',status='CANDIDATE',
        case_revision=spec['case_revision'],frame=spec['frame'].copy(),rim_inspection=inspection,
        boundary_vertex_count=n,axial_ring_count=len(rings),measured_width_depth_height_mm=measured.tolist(),
        requested_width_depth_height_mm=requested.tolist(),dimension_tolerance_mm=1e-6,
        self_contact=self_contact,
        closed_lumen=False,accepted_for_generation=False,
        limitation='Open dome disk only; no parent surface trimming or lumen union. '
                   'Boundary positions are preserved, not parent tangent continuity. No surrounding clearance check.')
