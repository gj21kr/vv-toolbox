"""Bounded-memory implicit vessel union with shared slab-boundary vertices."""
import numpy as np
from scipy.ndimage import gaussian_filter
from skimage.measure import marching_cubes
from scipy.spatial import cKDTree
from scipy.interpolate import PchipInterpolator


def _is_aortic_trunk(name):
    return name.startswith(("abdominal_aorta","aortic_arch")) or name in ("thoracic_aorta","distal_arch","ascending_aorta")


def _endpoint_radius(edge,node):
    if edge.radius_profile_mm is None:
        return edge.radius_mm
    return float(edge.radius_profile_mm[0 if node==edge.start else -1])


def _minimum_radius(graph):
    return min(float(np.min(edge.radius_profile_mm)) if edge.radius_profile_mm is not None else edge.radius_mm for edge in graph.segments)


def _arterial_junctions(graph):
    fillets={}
    for node in graph.nodes:
        incident=[edge for edge in graph.segments if node in (edge.start,edge.end)]
        if len(incident)<3 or node=='aortic_bifurcation':
            continue
        smallest=min(_endpoint_radius(edge,node) for edge in incident)
        largest=max(_endpoint_radius(edge,node) for edge in incident)
        # Local ostial fillet only; do not give unrelated arms a common radius.
        fillets[node]=(min(3.,.7*smallest),largest,largest+4*smallest)
    return fillets


def _aortic_radius_profiles(graph):
    """One non-overshooting C1 caliber profile across the entire trunk."""
    edges=[edge for edge in graph.segments if _is_aortic_trunk(edge.name)]
    if not edges:
        return {}
    ends={edge.end for edge in edges}
    starts=[edge for edge in edges if edge.start not in ends]
    if len(starts)!=1 or len({edge.start for edge in edges})!=len(edges):
        return {}
    by_start={edge.start:edge for edge in edges}
    ordered=[]
    edge=starts[0]
    while edge is not None and len(ordered)<len(edges):
        ordered.append(edge)
        edge=by_start.get(edge.end)
    if len(ordered)!=len(edges):
        return {}
    arc=[np.r_[0,np.cumsum(np.linalg.norm(np.diff(edge.points,axis=0),axis=1))] for edge in ordered]
    offsets=np.r_[0,np.cumsum([values[-1] for values in arc])]
    positions=np.r_[0,[(offsets[i]+offsets[i+1])/2 for i in range(len(ordered))],offsets[-1]]
    values=np.array([ordered[0].radius_mm]+[edge.radius_mm for edge in ordered]+[ordered[-1].radius_mm])
    profile=PchipInterpolator(positions,values)
    return {edge.name:profile(offsets[i]+arc[i]) for i,edge in enumerate(ordered)}


def _brachiocephalic_taper(graph,edge,radii,arc):
    """Taper only the parent outlet; daughter calibers and arch inlet stay fixed."""
    node='brachiocephalic'
    if edge.name!='brachiocephalic' or edge.end!=node:
        return radii
    daughters=[_endpoint_radius(other,node) for other in graph.segments if other.start==node and other.name!=edge.name]
    if len(daughters)<2:
        return radii
    target=float(np.linalg.norm(daughters))
    transition=min(.6*arc[-1],max(12.,4*edge.radius_mm))
    distance=arc[-1]-arc
    weight=np.clip(1-distance/transition,0,1)
    weight=weight*weight*(3-2*weight)
    return radii+(target-edge.radius_mm)*weight


def _venous_junctions(graph):
    """Choose continuation geometrically, never from radius or edge ordering."""
    connections={node:[] for node in graph.nodes}
    for edge in graph.segments:
        for node,tangent in ((edge.start,edge.points[1]-edge.points[0]),(edge.end,edge.points[-2]-edge.points[-1])):
            connections[node].append((edge,tangent/np.linalg.norm(tangent)))
    continuation={}
    fillets={}
    for node,items in connections.items():
        if len(items)<2:
            continue
        pairs=[(float(np.dot(a[1],b[1])),a[0].name,b[0].name,a[0],b[0]) for i,a in enumerate(items) for b in items[i+1:]]
        cosine,_,_,a,b=min(pairs,key=lambda item:item[:3])
        if len(items)>=3:
            if cosine<-.90:
                common=(_endpoint_radius(a,node)+_endpoint_radius(b,node))/2
                continuation[node]={a.name:common,b.name:common}
            else:
                # A genuine Y has no straight continuation. Treat all arms equally
                # instead of letting an arbitrary near-tie privilege one side.
                common=float(np.mean([_endpoint_radius(edge,node) for edge,_ in items]))
                continuation[node]={edge.name:common for edge,_ in items}
        if len(items)>=3 or cosine>-.98:
            minimum=min(_endpoint_radius(edge,node) for edge,_ in items)
            maximum=max(_endpoint_radius(edge,node) for edge,_ in items)
            # Millimeter fillet support follows vessel caliber, not voxel/sample count.
            fillets[node]=(min(3.0,.65*minimum),1.25*maximum,2.5*maximum)
    return continuation,fillets


def _capsule_field(capsules,origin,spacing,offset,extent,padding):
    field=np.full(tuple(extent),padding,dtype=np.float32)
    for a,b,r,s in capsules:
        low=np.maximum(np.floor((np.minimum(a,b)-max(r,s)-padding-origin)/spacing).astype(int)-offset,0)
        high=np.minimum(np.ceil((np.maximum(a,b)+max(r,s)+padding-origin)/spacing).astype(int)-offset+1,extent)
        if np.any(high<=low):
            continue
        x,y,z=np.ogrid[low[0]:high[0],low[1]:high[1],low[2]:high[2]]
        dx=(x+offset[0])*spacing+origin[0]-a[0]
        dy=(y+offset[1])*spacing+origin[1]-a[1]
        dz=(z+offset[2])*spacing+origin[2]-a[2]
        direction=b-a
        t=np.clip((dx*direction[0]+dy*direction[1]+dz*direction[2])/np.dot(direction,direction),0,1)
        distance=np.sqrt((dx-t*direction[0])**2+(dy-t*direction[1])**2+(dz-t*direction[2])**2)-(r+t*(s-r))
        region=tuple(slice(int(l),int(h)) for l,h in zip(low,high))
        np.minimum(field[region],distance,out=field[region])
    return field


def network_mesh(graph, spacing=None):
    """Fuse swept centerlines into one display surface, including closed terminal ends.

    0.45 mm spacing resolves the minimum supported 0.6 mm radius. Slab extraction
    bounds temporary fields; smoothing is deliberately subvoxel to retain terminals.
    This is a visualization mesh, not a verified CFD or contact domain.
    """
    graph.validate()
    if spacing is None:
        spacing = min(0.45*max(1.0, graph.parameters.get("radius_scale",1.0)),_minimum_radius(graph)*0.70)
    if not np.isfinite(spacing) or not 0.2 <= spacing <= _minimum_radius(graph)*0.75+1e-10:
        raise ValueError("spacing must be >=0.2 mm and <=75% of minimum radius")
    venous=graph.parameters.get('circulation') in ('systemic','portal')
    continuation,fillets=_venous_junctions(graph) if venous else ({},_arterial_junctions(graph))
    arterial_profiles={} if venous else _aortic_radius_profiles(graph)
    incident = {key: [] for key in graph.nodes}
    trunk_incident = {key: [] for key in graph.nodes}
    def is_trunk(name):
        return _is_aortic_trunk(name)
    for edge in graph.segments:
        incident[edge.start].append(_endpoint_radius(edge,edge.start))
        incident[edge.end].append(_endpoint_radius(edge,edge.end))
        if is_trunk(edge.name):
            trunk_incident[edge.start].append(_endpoint_radius(edge,edge.start))
            trunk_incident[edge.end].append(_endpoint_radius(edge,edge.end))
    capsules = []
    capsule_groups={}
    for edge in graph.segments:
        t = np.linspace(0, 1, len(edge.points))
        explicit_profile=edge.radius_profile_mm is not None
        radii = (edge.radius_profile_mm if explicit_profile else arterial_profiles.get(edge.name,np.full(len(t), edge.radius_mm, dtype=float))).copy()
        arc = np.r_[0,np.cumsum(np.linalg.norm(np.diff(edge.points,axis=0),axis=1))]
        for node, weight in [(edge.start, np.maximum(1-t/0.3, 0)), (edge.end, np.maximum(1-(1-t)/0.3, 0))]:
            # A side branch must not interrupt the trunk's radius continuity.
            neighbors = trunk_incident[node] if is_trunk(edge.name) and len(trunk_incident[node]) == 2 else incident[node]
            if explicit_profile or edge.name in arterial_profiles:
                continue
            if len(neighbors) == 2:
                smooth = weight*weight*(3-2*weight)
                radii += (np.mean(neighbors)-edge.radius_mm)*smooth
            elif edge.name in continuation.get(node,{}):
                distance=arc if node==edge.start else arc[-1]-arc
                transition=min(.45*arc[-1],max(12.0,4*edge.radius_mm))
                weight=np.clip(1-distance/transition,0,1)
                radii+=(continuation[node][edge.name]-edge.radius_mm)*weight*weight*(3-2*weight)
        # Authored illustrative Y transition, not a physiological fit.
        bifurcation = "aortic_bifurcation"
        if not explicit_profile and bifurcation in (edge.start,edge.end):
            iliac_radii = [e.radius_mm for e in graph.segments if e.name in ("left_common_iliac","right_common_iliac")]
            junction_radius = float(np.linalg.norm(iliac_radii))
            arc = np.r_[0,np.cumsum(np.linalg.norm(np.diff(edge.points,axis=0),axis=1))]
            distance = arc if edge.start == bifurcation else arc[-1]-arc
            transition_length = 40.0 if edge.name == "abdominal_aorta" else 30.0
            weight = np.clip(1-distance/transition_length,0,1)
            smooth = weight*weight*(3-2*weight)
            radii += (junction_radius-edge.radius_mm)*smooth
        if not venous and not explicit_profile:
            radii=_brachiocephalic_taper(graph,edge,radii,arc)
        group=[(edge.points[i], edge.points[i+1], radii[i], radii[i+1]) for i in range(len(t)-1)]
        capsules.extend(group)
        capsule_groups[edge.name]=([edge],group)
    if not venous and arterial_profiles:
        # Never blend identical-radius adjacent arch fragments against each other:
        # their complete union is the envelope side branches are attached to.
        trunk_edges=[]
        trunk_capsules=[]
        for name in arterial_profiles:
            group_edges,group_capsules=capsule_groups.pop(name)
            trunk_edges.extend(group_edges)
            trunk_capsules.extend(group_capsules)
        capsule_groups={"_aortic_trunk":(trunk_edges,trunk_capsules),**capsule_groups}
    padding = max(4*spacing,max((value[0] for value in fillets.values()),default=0)+2*spacing)
    lower = np.min([np.minimum(a,b)-max(r,s)-padding for a,b,r,s in capsules], axis=0)
    upper = np.max([np.maximum(a,b)+max(r,s)+padding for a,b,r,s in capsules], axis=0)
    origin = np.floor(lower/spacing)*spacing
    shape = np.ceil((upper-origin)/spacing).astype(int)+1
    vertices, faces = [], []
    count = 0
    slab = 48
    # Gaussian halo means adjacent slab fields have identical boundary values.
    halo = 3
    for z0 in range(0, int(shape[2])-1, slab):
        z1 = min(z0+slab, int(shape[2])-1)
        loz, hiz = max(0, z0-halo), min(int(shape[2])-1, z1+halo)
        candidates = [(a,b,r,s) for a,b,r,s in capsules if min(a[2],b[2])-max(r,s)-padding <= origin[2]+hiz*spacing and max(a[2],b[2])+max(r,s)+padding >= origin[2]+loz*spacing]
        if not candidates:
            continue
        lowxy = np.floor((np.min([np.minimum(a,b)[:2]-max(r,s)-padding for a,b,r,s in candidates], axis=0)-origin[:2])/spacing).astype(int)
        highxy = np.ceil((np.max([np.maximum(a,b)[:2]+max(r,s)+padding for a,b,r,s in candidates], axis=0)-origin[:2])/spacing).astype(int)
        offset = np.array([*lowxy, loz])
        extent = np.array([*(highxy-lowxy+1), hiz-loz+1])
        if not fillets:
            field=_capsule_field(candidates,origin,spacing,offset,extent,padding)
        else:
            field=np.full(tuple(extent),padding,dtype=np.float32)
            for group_edges,group in capsule_groups.values():
                selected=[(a,b,r,s) for a,b,r,s in group if min(a[2],b[2])-max(r,s)-padding <= origin[2]+hiz*spacing and max(a[2],b[2])+max(r,s)+padding >= origin[2]+loz*spacing]
                if not selected:
                    continue
                low=np.maximum(np.floor((np.min([np.minimum(a,b)-max(r,s)-padding for a,b,r,s in selected],axis=0)-origin)/spacing).astype(int)-offset,0)
                high=np.minimum(np.ceil((np.max([np.maximum(a,b)+max(r,s)+padding for a,b,r,s in selected],axis=0)-origin)/spacing).astype(int)-offset+1,extent)
                branch_offset=offset+low
                branch_extent=high-low
                branch=_capsule_field(selected,origin,spacing,branch_offset,branch_extent,padding)
                region=tuple(slice(int(l),int(h)) for l,h in zip(low,high))
                existing=field[region]
                k=np.zeros_like(branch)
                nodes={node for edge in group_edges for node in (edge.start,edge.end)}
                if not venous and all(edge.name in arterial_profiles for edge in group_edges):
                    nodes=set()
                for node in nodes:
                    if node not in fillets:
                        continue
                    width,inner,outer=fillets[node]
                    x,y,z=np.ogrid[:branch_extent[0],:branch_extent[1],:branch_extent[2]]
                    delta=origin+branch_offset*spacing-graph.nodes[node]
                    radial=np.sqrt((x*spacing+delta[0])**2+(y*spacing+delta[1])**2+(z*spacing+delta[2])**2)
                    weight=np.clip((outer-radial)/(outer-inner),0,1)
                    np.maximum(k,width*weight*weight*(3-2*weight),out=k)
                # One blend per vessel; adding more centerline samples cannot inflate a junction.
                h=np.maximum(1-np.abs(existing-branch)/np.maximum(k,1e-12),0)
                np.minimum(existing,branch,out=existing)
                existing-=k*.25*h*h
        field = gaussian_filter(field, sigma=0.65, mode="nearest", truncate=3)
        field = field[:,:,z0-loz:z1-loz+1]
        if field.min() >= 0:
            continue
        v,f,_,_ = marching_cubes(field, level=0, spacing=(spacing,)*3, allow_degenerate=False)
        v += origin+np.array([*lowxy,z0])*spacing
        vertices.append(v)
        faces.append(f+count)
        count += len(v)
    if not vertices:
        raise ValueError("No surface generated")
    vertices = np.concatenate(vertices)
    faces = np.concatenate(faces)
    # Distance welding, not coordinate rounding: equal seam points can straddle bins.
    parent = np.arange(len(vertices))
    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for a,b in cKDTree(vertices).query_pairs(0.001, output_type="ndarray"):
        a,b = root(a),root(b)
        parent[max(a,b)] = min(a,b)
    inverse = np.array([root(i) for i in range(len(vertices))])
    faces = inverse[faces]
    faces = faces[(faces[:,0]!=faces[:,1]) & (faces[:,1]!=faces[:,2]) & (faces[:,0]!=faces[:,2])]
    indices, inverse = np.unique(faces, return_inverse=True)
    vertices = vertices[indices]
    faces = inverse.reshape(-1,3)
    return vertices.astype(np.float32), faces.astype(np.uint32)
