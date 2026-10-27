"""Source-mesh voxel medial paths; inter-part proximity is never anatomical proof."""
import hashlib
import json
from itertools import product
from pathlib import Path
import numpy as np
from scipy.ndimage import distance_transform_edt, gaussian_filter1d
from scipy.spatial import cKDTree
from skimage.morphology import skeletonize
import trimesh

VERSION='voxel-lee-1'
SMOOTHING_VERSION='anchored-gaussian-arclength-1'


def smooth_edge(edge):
    """Smooth voxel steps with fixed graph anchors and bounded displacement.

    Keep the raw extraction cache unchanged. Radii remain interpolated source
    estimates, not newly measured clearances at the smoothed coordinates.
    """
    if edge.get('provenance')!='source-mesh-voxel-medial':return edge
    points=np.asarray(edge['points'],dtype=float);radii=np.asarray(edge['radii'],dtype=float)
    distance=np.r_[0.,np.cumsum(np.linalg.norm(np.diff(points,axis=0),axis=1))]
    keep=np.r_[True,np.diff(distance)>1e-9]
    if keep.sum()<4 or distance[-1]<=1e-8:return edge
    pitch=float(edge['pitch']);length=distance[-1]
    count=max(4,min(8192,int(np.ceil(length/max(pitch*.35,.03)))+1))
    t=np.linspace(0.,length,count);step=t[1]-t[0]
    raw=np.column_stack([np.interp(t,distance[keep],points[keep,i]) for i in range(3)])
    radius=np.interp(t,distance[keep],radii[keep])
    curve=gaussian_filter1d(raw,sigma=max(.5,1.5*pitch/step),axis=0,mode='nearest')
    # Subtract endpoint drift smoothly without moving the graph junctions.
    fraction=t/length
    curve-=(1-fraction[:,None])*(curve[0]-raw[0])+fraction[:,None]*(curve[-1]-raw[-1])
    delta=curve-raw;norm=np.linalg.norm(delta,axis=1)
    limit=np.minimum(1.5*pitch,.35*radius)
    delta*= (np.tanh(norm/np.maximum(limit,1e-9))*limit/np.maximum(norm,1e-12))[:,None]
    curve=raw+delta;curve[0]=points[0];curve[-1]=points[-1]
    return dict(edge,points=curve.tolist(),radii=radius.tolist(),smoothing=dict(method=SMOOTHING_VERSION,
        max_displacement=float(np.linalg.norm(curve-raw,axis=1).max()),surface_containment_validated=False))


def _paths(mask,transform,pitch,part):
    skeleton=skeletonize(mask,method='lee')
    ijk=np.argwhere(skeleton)
    if len(ijk)<2:raise ValueError('No resolvable medial path at admitted voxel pitch')
    lookup={tuple(p):i for i,p in enumerate(ijk)}
    offsets=[np.array(x) for x in product((-1,0,1),repeat=3) if x!=(0,0,0)]
    adjacency=[{lookup[tuple(p+d)] for d in offsets if tuple(p+d) in lookup} for p in ijk]
    radius=distance_transform_edt(mask)[tuple(ijk.T)]*pitch
    points=trimesh.transform_points(ijk,transform)
    critical={i for i,n in enumerate(adjacency) if len(n)!=2}
    # Every pure cycle needs one anchor, but disconnected components stay apart.
    unseen=set(range(len(ijk)));components=0
    while unseen:
        todo=[next(iter(unseen))];component=set()
        while todo:
            i=todo.pop()
            if i in component:continue
            component.add(i);todo.extend(adjacency[i]-component)
        unseen-=component;components+=1
        if not component&critical:critical.add(min(component))
    groups=[];pending=set(critical)
    while pending:
        first=min(pending);group={first};todo=[first]
        # Merge a voxel junction cluster, not terminal nodes.
        while todo:
            i=todo.pop()
            if len(adjacency[i])<=2:continue
            for j in adjacency[i]&pending:
                if len(adjacency[j])>2 and j not in group:group.add(j);todo.append(j)
        groups.append(group);pending-=group
    node_of={};nodes=[]
    for group in groups:
        ident=f"{part['id']}:n{len(nodes)}";indices=sorted(group)
        nodes.append(dict(id=ident,part_id=part['id'],point=points[indices].mean(0).tolist(),
                          radius=float(radius[indices].max()),kind='junction' if any(len(adjacency[i])>2 for i in group) else 'terminal' if len(adjacency[indices[0]])==1 else 'cycle'))
        for i in indices:node_of[i]=len(nodes)-1
    visited=set();edges=[]
    for initial,ni in sorted(node_of.items()):
        for following in sorted(adjacency[initial]):
            key=tuple(sorted((initial,following)))
            if key in visited or node_of.get(following)==ni:continue
            visited.add(key);walk=[initial,following];previous,current=initial,following
            while current not in node_of:
                choices=adjacency[current]-{previous}
                if not choices:break
                nxt=min(choices);visited.add(tuple(sorted((current,nxt))))
                walk.append(nxt);previous,current=current,nxt
            if current not in node_of:continue
            nj=node_of[current];curve=points[walk].copy();curve[0]=nodes[ni]['point'];curve[-1]=nodes[nj]['point']
            radii=radius[walk].copy();radii[0]=nodes[ni]['radius'];radii[-1]=nodes[nj]['radius']
            if np.linalg.norm(np.diff(curve,axis=0),axis=1).sum()<pitch*.1:continue
            edges.append(dict(id=f"{part['id']}:e{len(edges)}",part_id=part['id'],layer=part['layer'],start=nodes[ni]['id'],end=nodes[nj]['id'],
                              points=curve.tolist(),radii=radii.tolist(),provenance='source-mesh-voxel-medial',pitch=pitch))
    if not edges:raise ValueError('Skeleton did not yield a path')
    return nodes,edges,components


def extract_part(part):
    mesh=trimesh.Trimesh(vertices=np.array(part['vertices'],copy=True),faces=np.array(part['faces'],copy=True),process=True)
    # Weld duplicate OBJ vertices on the copy. Never cap arbitrary open surfaces.
    if not mesh.is_watertight:raise ValueError('Non-watertight source after duplicate-vertex welding')
    radius=max(.1,2*abs(mesh.volume)/max(mesh.area,1e-8))
    pitch=max(.12,min(.8,radius/3))
    extents=mesh.extents
    while np.prod(np.ceil(extents/pitch)+5)>1500000 or max(extents/pitch)>650:pitch*=1.2
    voxels=mesh.voxelized(pitch,method='subdivide',max_iter=10).fill()
    mask=np.pad(voxels.matrix,1)
    transform=voxels.transform.copy();transform[:3,3]-=pitch
    nodes,edges,components=_paths(mask,transform,pitch,part)
    return dict(nodes=nodes,edges=edges,part=dict(id=part['id'],layer=part['layer'],status='EXTRACTED',
        method='Watertight welded mesh, filled surface voxelization, Lee thinning, junction-cluster graph',
        pitch=float(pitch),components=components,estimated_radius=radius,
        quality='COARSE' if pitch>radius*.6 else 'VOXEL_APPROXIMATION',voxels=int(mask.size)))


def _estimated(part):
    m=part['metadata'];pid=part['id'];nodes=[];edges=[]
    if 'graph' in m:
        g=m['graph'];raw=g['nodes']
        nodes=[dict(id=pid+':'+key,part_id=pid,point=value,kind='authored') for key,value in raw.items()]
        for e in g['segments']:
            edges.append(dict(id=pid+':'+e['id'],part_id=pid,layer=part['layer'],start=pid+':'+e['start'],end=pid+':'+e['end'],points=e['points_mm'],
                              radii=e.get('radius_profile_mm') or [e['radius_mm']]*len(e['points_mm']),provenance='authored-estimated'))
    else:
        p=m['centerline'];nodes=[dict(id=pid+':'+str(i),part_id=pid,point=p[j],kind='authored') for i,j in enumerate((0,-1))]
        edges=[dict(id=pid+':e0',part_id=pid,layer=part['layer'],start=nodes[0]['id'],end=nodes[1]['id'],points=p,radii=m['radius_profile'],provenance='authored-estimated')]
    return dict(nodes=nodes,edges=edges,part=dict(id=pid,layer=part['layer'],status='AUTHORED_ESTIMATE',method='Existing authored graph; not extracted from source'))


def proximity_links(nodes,edges):
    """Endpoint-to-path candidates, within a layer. Never merge source nodes."""
    links=[];seen=set();node_by={n['id']:n for n in nodes}
    for layer in sorted({e['layer'] for e in edges}):
        paths=[e for e in edges if e['layer']==layer]
        if not paths:continue
        points=np.concatenate([e['points'] for e in paths]);tree=cKDTree(points)
        owners=np.concatenate([np.full(len(e['points']),i) for i,e in enumerate(paths)])
        radii=np.concatenate([e['radii'] for e in paths]);max_radius=min(20.,float(max(radii)))
        for e in paths:
            for end,idx in [('start',0),('end',-1)]:
                n=node_by[e[end]]
                if n['kind'] not in ('terminal','authored'):continue
                p=np.asarray(n['point']);r=float(e['radii'][idx]);best={}
                for j in tree.query_ball_point(p,min(25.,r+max_radius+2)):
                    other=paths[owners[j]]
                    if other['part_id']==e['part_id']:continue
                    distance=float(np.linalg.norm(p-points[j]));gap=distance-r-float(radii[j])
                    if gap>2.:continue
                    if other['part_id'] not in best or distance<best[other['part_id']][0]:best[other['part_id']]=(distance,j,other,gap)
                for distance,j,other,gap in sorted(best.values(),key=lambda x:x[0])[:3]:
                    # Candidate target is an actual sampled path point, not an
                    # arbitrary terminal of a long neighboring vessel.
                    key=(n['id'],other['part_id'])
                    if key in seen:continue
                    seen.add(key);target=f"candidate:{len(links)}"
                    nodes.append(dict(id=target,part_id=other['part_id'],point=points[j].tolist(),kind='candidate_attachment'))
                    links.append(dict(id=f'link{len(links)}',start=n['id'],end=target,part_a=e['part_id'],part_b=other['part_id'],target_edge=other['id'],
                                      target_point=points[j].tolist(),status='candidate',distance=distance,surface_gap_proxy=gap,layer=layer))
    return links


def build_atlas_centerlines(atlas,estimated_parts=(),*,cache_dir=None,progress=None):
    result=dict(schema='vv-toolbox.atlas-centerlines/1',algorithm=VERSION,nodes=[],edges=[],parts=[],units='original atlas units (mm assumed)',
                atlas_sha256=getattr(atlas,'metadata',{}).get('sha256'),clinical_validation=False,
                extraction_parameters=dict(min_pitch=.12,preferred_max_pitch=.8,max_voxels=1500000,max_axis_voxels=650),
                limitations='Voxel medial approximations, not annotated anatomical centerlines. Inter-part proximity links are unverified candidates, not blood-flow connections. Failed source parts remain listed; no straight-line substitutes.')
    cache=Path(cache_dir) if cache_dir else None
    if cache:cache.mkdir(parents=True,exist_ok=True)
    parts=[p for p in atlas.meshes if p['layer']!='context']
    for i,p in enumerate(parts):
        key=hashlib.sha256(VERSION.encode()+p['id'].encode()+p['vertices'].tobytes()+p['faces'].tobytes()).hexdigest()
        path=cache/(key+'.json') if cache else None
        try:
            if path and path.exists():item=json.loads(path.read_text())
            else:
                item=extract_part(p)
                if path:path.write_text(json.dumps(item,allow_nan=False),encoding='utf-8')
        except (ValueError,RuntimeError,IndexError) as error:
            item=dict(nodes=[],edges=[],part=dict(id=p['id'],layer=p['layer'],status='UNRESOLVED',reason=str(error)))
        item['part']['geometry_algorithm_sha256']=key
        result['nodes'].extend(item['nodes']);result['edges'].extend(item['edges']);result['parts'].append(item['part'])
        if progress:progress(i+1,len(parts))
    for p in estimated_parts:
        item=_estimated(p);result['nodes'].extend(item['nodes']);result['edges'].extend(item['edges']);result['parts'].append(item['part'])
    result['edges']=[smooth_edge(edge) for edge in result['edges']]
    result['smoothing']=SMOOTHING_VERSION
    result['links']=proximity_links(result['nodes'],result['edges'])
    from .atlas_topology import build_reference_topology
    result['reference_topology']=build_reference_topology([*parts,*estimated_parts],result['links'])
    result['summary']=dict(source_parts=len(parts),extracted=sum(p['status']=='EXTRACTED' for p in result['parts']),unresolved=sum(p['status']=='UNRESOLVED' for p in result['parts']),
                           authored_parts=len(estimated_parts),nodes=len(result['nodes']),edges=len(result['edges']),candidate_links=len(result['links']))
    return result
