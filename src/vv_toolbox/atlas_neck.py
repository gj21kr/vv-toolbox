"""Clearly estimated neck display connectors anchored to unchanged atlas sections."""
import json
import numpy as np
from scipy.interpolate import CubicHermiteSpline, CubicSpline
from scipy.spatial import ConvexHull
from .model import tube_mesh, Segment, VesselGraph
from .surface import network_mesh
from .clearance import _clearance
from itertools import combinations


def _pair_report(edges):
    pairs=[]
    for a,b in combinations(edges,2):
        if {a.start,a.end}&{b.start,b.end}:continue
        pairs.append(dict(vessel_a=a.name,vessel_b=b.name,clearance_mm=_clearance(a,b)))
    pairs.sort(key=lambda item:item['clearance_mm'])
    return dict(minimum_clearance_mm=pairs[0]['clearance_mm'] if pairs else None,
                potential_collisions=[p for p in pairs if p['clearance_mm']<=0],pairs=pairs)


def _separate_jugulars(edges,arterial_parts):
    arteries=[Segment(p['id'],p['id']+'_start',p['id']+'_end',np.array(p['metadata']['centerline']),
                      1.,np.array(p['metadata']['radius_profile'])) for p in arterial_parts]
    before=_pair_report(arteries+edges);adjustments=[]
    for side,sign in [('right',-1),('left',1)]:
        index=next(i for i,e in enumerate(edges) if e.name==side+'_internal_jugular_extension')
        original=edges[index];t=np.linspace(0,1,len(original.points));envelope=np.sin(np.pi*t)**2
        # Outward/anterior bow in the atlas frame. The squared sine keeps
        # endpoint position and analytic tangent fixed while allowing the
        # lower cervical segment to clear the carotid near its IJV anchor.
        direction=np.array([sign,-1.,0.])/np.sqrt(2.)
        def candidate(amplitude):
            points=original.points.copy()+amplitude*envelope[:,None]*direction
            points[[0,-1]]=original.points[[0,-1]]
            return Segment(original.name,original.start,original.end,points,original.radius_mm,original.radius_profile_mm)
        others=[e for e in arteries+edges if e.name!=original.name and not {e.start,e.end}&{original.start,original.end}]
        def clearance(amplitude):return min(_clearance(candidate(amplitude),e) for e in others)
        amplitude=0.
        if clearance(0)<1.:
            bracket=next((float(a) for a in range(1,31) if clearance(a)>=1.),None)
            if bracket is None:raise ValueError('Bounded IJV separation unavailable without moving source anchors')
            low,high=bracket-1,bracket
            for _ in range(16):
                mid=(low+high)/2
                if clearance(mid)>=1.:high=mid
                else:low=mid
            amplitude=high
            edges[index]=candidate(amplitude)
        adjustments.append(dict(side=side,bow_amplitude_source_units=amplitude,direction=direction.tolist(),
                                maximum_allowed=30.,anchors_moved=False,radii_changed=False))
    after=_pair_report(arteries+edges)
    if after['minimum_clearance_mm'] is not None and after['minimum_clearance_mm']<1.:
        raise ValueError('Estimated overlay fails minimum cross-vessel capsule clearance')
    return dict(status='CLEAR_CAPSULE_PROXY',required_margin=1.,before=before,after=after,adjustments=adjustments,
                method='Exact polyline segment distance minus maximum endpoint radii per capsule; shared graph junction pairs excluded',
                limitations='Not an exact triangle surface intersection or original-atlas collision proof; rendered fillets are excluded')


def _venous_overlay(atlas,by_id,arterial_parts):
    """Authored named sinus graph, scaled by head bounds, anchored only at IJVs."""
    anchors={side:_terminal(by_id[element],True) for side,element in [('right','FJ3585'),('left','FJ3485')]}
    floor=max(a['center'][2] for a in anchors.values())+20
    head=[m['vertices'][m['vertices'][:,2]>floor] for m in atlas.meshes if m['layer']=='arterial']
    head=[v for v in head if len(v)]
    if not head:raise ValueError('Head vascular bounds unavailable')
    vertices=np.concatenate(head);low,high=vertices.min(0),vertices.max(0)
    width=float(high[0]-low[0]);depth=float(high[1]-low[1]);height=float(high[2]-low[2]);cx=float((high[0]+low[0])/2)
    if min(width,depth,height)<10:raise ValueError('Head vascular bounds degenerate')
    posterior=float(high[1]);top=float(high[2])
    nodes={'confluence':np.array([cx,posterior,top-.30*height]),
           'sagittal_crown':np.array([cx,posterior-.40*depth,top+5]),
           'sagittal_anterior':np.array([cx,posterior-.85*depth,top-.1*height]),
           'straight_anterior':np.array([cx,posterior-.45*depth,top-.35*height])}
    edges=[]
    def chain(names,ids,radii,start_axis=None):
        points=np.array([nodes[n] for n in names]);q=np.r_[0,np.cumsum(np.linalg.norm(np.diff(points,axis=0),axis=1))]
        bc=((1,start_axis),'natural') if start_axis is not None else 'natural'
        spline=CubicSpline(q,points,axis=0,bc_type=bc)
        for i,id in enumerate(ids):
            t=np.linspace(0,1,64);curve=spline(q[i]+t*(q[i+1]-q[i]));curve[0],curve[-1]=points[i],points[i+1]
            radius=radii[i]+(radii[i+1]-radii[i])*(3*t*t-2*t*t*t)
            edges.append(Segment(id,names[i],names[i+1],curve,float(np.mean(radius)),radius))
    for side,sign in [('right',-1),('left',1)]:
        a=anchors[side]
        nodes[side+'_ijv_anchor']=a['center'].copy()
        nodes[side+'_jugular_bulb']=np.array([cx+sign*.32*width,posterior-.35*depth,top-.68*height])
        nodes[side+'_sigmoid']=np.array([cx+sign*.42*width,posterior-.10*depth,top-.48*height])
        nodes[side+'_transverse']=np.array([cx+sign*.40*width,posterior,top-.28*height])
        chain([side+'_ijv_anchor',side+'_jugular_bulb',side+'_sigmoid',side+'_transverse','confluence'],
              [side+'_internal_jugular_extension',side+'_sigmoid_lower',side+'_sigmoid_upper',side+'_transverse_sinus'],
              [a['radius'],3.5,3.5,3.5,3.5],a['axis'])
    chain(['sagittal_anterior','sagittal_crown','confluence'],['superior_sagittal_anterior','superior_sagittal_posterior'],[2.5,3.5,3.5])
    chain(['straight_anterior','confluence'],['straight_sinus'],[2.5,3.5])
    separation=_separate_jugulars(edges,arterial_parts)
    graph=VesselGraph(nodes,edges,{'circulation':'systemic','radius_scale':1.},provenance={'kind':'estimated-atlas-overlay','anatomy_validated':False})
    graph.validate()
    v,f=network_mesh(graph,spacing=.6)
    metadata=dict(kind='estimated-cerebral-venous-network',original_atlas_geometry=False,source_meshes_modified=False,
                  anatomy_validated=False,clinical_use=False,source_endpoint_ids=['FJ3585','FJ3485'],
                  method='IJV terminal section anchors; authored normalized sinus landmarks scaled to atlas head vascular bounds; clamped cubic chains and smooth radius profiles; fused display surface',
                  head_bounds=[low.tolist(),high.tolist()],anchor_axes={side:a['axis'].tolist() for side,a in anchors.items()},
                  graph=json.loads(graph.to_json()),
                  separation=separation,
                  limits='Only lower IJV anchors are source-derived. Every upper jugular/sinus node, topology and radius is an explicit estimate; no recovered source upper target, registration, source union or clinical validation.')
    return dict(id='estimated_cerebral_venous_network',name='Estimated jugular and cerebral venous network',layer='systemic_venous',vertices=v,faces=f,metadata=metadata)


def _section(mesh,z):
    vertices=np.asarray(mesh['vertices'],float)
    triangles=vertices[np.asarray(mesh['faces'])]
    points=[]
    for a,b in ((0,1),(1,2),(2,0)):
        p,q=triangles[:,a],triangles[:,b]
        dz=q[:,2]-p[:,2]
        selected=(np.abs(dz)>1e-10)&((p[:,2]-z)*(q[:,2]-z)<=0)
        t=(z-p[selected,2])/dz[selected]
        points.extend(p[selected]+t[:,None]*(q[selected]-p[selected]))
    points=np.unique(np.round(points,8),axis=0)
    if len(points)<3:raise ValueError('Cannot identify a terminal cross section')
    hull=ConvexHull(points[:,:2]);polygon=points[hull.vertices]
    x,y=polygon[:,0],polygon[:,1]
    cross=x*np.roll(y,-1)-np.roll(x,-1)*y
    area=cross.sum()/2
    center=np.array([np.sum((x+np.roll(x,-1))*cross)/(6*area),np.sum((y+np.roll(y,-1))*cross)/(6*area),z])
    return center,float(abs(area))


def _terminal(mesh,upper):
    vertices=np.asarray(mesh['vertices'],float);low,high=vertices[:,2].min(),vertices[:,2].max()
    inset=min(1.5,(high-low)*.05);window=min(6.,(high-low)*.2)
    z=high-inset if upper else low+inset
    center,area=_section(mesh,z)
    inner,_=_section(mesh,z-window if upper else z+window)
    axis=center-inner if upper else inner-center
    axis/=np.linalg.norm(axis)
    radius=float(np.sqrt(area*abs(axis[2])/np.pi))
    if not np.isfinite(radius) or radius<=0:raise ValueError('Invalid terminal radius')
    return dict(center=center,axis=axis,radius=radius,inset=inset,window=window)


def _repair(source,target,side,kind):
    a,b=_terminal(source,True),_terminal(target,False)
    # A vertebral takeoff is an estimated branch insertion, not continuation of
    # the full subclavian caliber. Only the target's radius is transferred there.
    if kind=='vertebral':
        a['radius']=b['radius']
        a['axis']=b['axis'].copy()
    length=float(np.linalg.norm(b['center']-a['center']))
    if length<=a['radius']+b['radius']:raise ValueError('No resolvable neck gap')
    spline=CubicHermiteSpline([0.,1.],np.array([a['center'],b['center']]),
                             np.array([a['axis'],b['axis']])*length)
    t=np.linspace(0,1,96);points=spline(t)
    radii=a['radius']+(b['radius']-a['radius'])*(3*t*t-2*t*t*t)
    vertices,faces=tube_mesh(points,1.,sides=24)
    vertices=(points[:,None,:]+(vertices.reshape(len(points),24,3)-points[:,None,:])*radii[:,None,None]).reshape(-1,3).astype(np.float32)
    metadata=dict(kind='estimated-neck-connector',source_endpoint_ids=[source['id'],target['id']],
                  method='Terminal z-plane triangle sections, area-equivalent radii, local section-centroid axes, cubic Hermite bridge',
                  source_meshes_modified=False,anatomy_validated=False,clinical_use=False,original_atlas_geometry=False,
                  attachment='Estimated subclavian branch insertion' if kind=='vertebral' else 'Estimated common-to-internal carotid continuation; bifurcation omitted',
                  endpoint_centers=[a['center'].tolist(),b['center'].tolist()],endpoint_axes=[a['axis'].tolist(),b['axis'].tolist()],
                  endpoint_radii=[a['radius'],b['radius']],section_insets=[a['inset'],b['inset']],
                  centerline=points.tolist(),radius_profile=radii.tolist(),
                  limits='Open display tube overlaps source terminal sections; no Boolean lumen union, source cap removal, contact or clinical validation. Coordinates and radii use original atlas units.')
    return dict(id=f'estimated_{side}_{kind}_neck',name=f'Estimated {side} {kind} neck connector',layer='arterial',vertices=vertices,faces=faces,metadata=metadata)


def build_neck_repairs(atlas):
    """Return additional estimated parts plus missing-target report; never mutate atlas."""
    by_id={mesh['id']:mesh for mesh in atlas.meshes};parts=[];missing=[]
    for side,common,internal,subclavian,vertebral in [('right','FJ3564','FJ1682','FJ3579','FJ1725'),('left','FJ3483','FJ1682M','FJ3479','FJ1725M')]:
        for kind,start,end in [('carotid',common,internal),('vertebral',subclavian,vertebral)]:
            if start not in by_id or end not in by_id:
                missing.append(dict(side=side,kind=kind,status='MISSING_SOURCE',endpoint_ids=[start,end]));continue
            try:parts.append(_repair(by_id[start],by_id[end],side,kind))
            except (ValueError,ArithmeticError) as error:
                missing.append(dict(side=side,kind=kind,status='FIT_UNAVAILABLE',reason=str(error)))
        missing.append(dict(side=side,kind='internal_jugular_to_sigmoid',status='MISSING_IDENTIFIED_UPPER_TARGET',
                            lower_element='FJ3585' if side=='right' else 'FJ3485',
                            reason='No identified ipsilateral sigmoid sinus mesh in this atlas selection; abdominal sigmoid vein is not a substitute'))
    if all(element in by_id for element in ('FJ3585','FJ3485')):
        try:
            parts.append(_venous_overlay(atlas,by_id,parts))
            for entry in missing:
                if entry.get('kind')=='internal_jugular_to_sigmoid':entry['display_resolution']='FILLED_BY_ESTIMATED_NETWORK; original upper source remains missing'
        except (ValueError,ArithmeticError) as error:
            missing.append(dict(kind='cerebral_venous_estimate',status='FIT_UNAVAILABLE',reason=str(error)))
    limitations='User-authorized estimates, not recovered original anatomy. Estimated venous display does not resolve missing original upper-source coverage. Subclavian insertion is a fitted superior section, not a source-annotated vertebral ostium.'
    return parts,dict(status='ESTIMATED_PARTIAL_REPAIR' if parts else 'UNAVAILABLE',estimated_parts=len(parts),
                      original_meshes_modified=False,missing=missing,unresolved=missing,
                      method='Source triangle cross-section centroids and local axes; cubic Hermite centerlines with smoothstep radius taper',
                      parts=[dict(id=p['id'],name=p['name'],layer=p['layer'],
                                  bounds_source=[p['vertices'].min(0).tolist(),p['vertices'].max(0).tolist()],
                                  **p['metadata']) for p in parts],
                      limits=limitations,limitations=limitations)
