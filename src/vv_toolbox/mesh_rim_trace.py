"""Trace polygon-side projection planes across actual source triangles."""
import numpy as np
import trimesh


def trace_mesh_rim(vertices,faces,polygon,normal,*,tolerance_mm=1e-7):
    vertices=np.asarray(vertices,float);faces=np.asarray(faces);polygon=np.asarray(polygon,float)
    normal=np.asarray(normal,float)
    if type(tolerance_mm) not in (int,float) or not np.isfinite(tolerance_mm) or tolerance_mm<=0:
        raise ValueError('Positive finite trace tolerance required')
    mesh=trimesh.Trimesh(vertices=vertices,faces=faces,process=False)
    if not np.isfinite(polygon).all() or polygon.ndim!=2 or polygon.shape[1]!=3 or len(polygon)<3 or not np.isclose(np.linalg.norm(normal),1):
        raise ValueError('Finite polygon and unit direction required')
    triangles=mesh.triangles;front=mesh.face_normals@normal>1e-8
    rows=[];chain=[]
    for side,(a,b) in enumerate(zip(polygon,np.roll(polygon,-1,axis=0))):
        direction=b-a;direction=direction-normal*(direction@normal)
        length=np.linalg.norm(direction)
        if length<=tolerance_mm:raise ValueError('Degenerate projected polygon side')
        tangent=direction/length;plane=np.cross(tangent,normal)
        distances=(triangles-a)@plane
        candidates=np.flatnonzero(front&(distances.min(axis=1)<=0)&(distances.max(axis=1)>=0))
        segments=[];coplanar=False
        for ident in candidates:
            triangle=triangles[ident];d=distances[ident]
            if np.max(np.abs(d))<=1e-12:coplanar=True;continue
            hits=[]
            for j,k in ((0,1),(1,2),(2,0)):
                if d[j]==0:hits.append(triangle[j])
                if d[j]*d[k]<0:hits.append(triangle[j]+d[j]/(d[j]-d[k])*(triangle[k]-triangle[j]))
            if len(hits)<2:continue
            hits=np.unique(np.asarray(hits),axis=0)
            if len(hits)!=2:continue
            values=(hits-a)@tangent;order=np.argsort(values);values=values[order];hits=hits[order]
            if values[1]-values[0]<=1e-12:continue
            lo=max(0.,float(values[0]));hi=min(float(length),float(values[1]))
            if hi-lo<=1e-12:continue
            clipped=hits[0]+((np.array([lo,hi])-values[0])/(values[1]-values[0]))[:,None]*(hits[1]-hits[0])
            segments.append(dict(source_face_index=int(ident),side_range_mm=[lo,hi],points_mm=clipped.tolist()))
        segments.sort(key=lambda s:s['side_range_mm'][0])
        valid=bool(segments) and not coplanar
        if valid:
            valid=abs(segments[0]['side_range_mm'][0])<=tolerance_mm and abs(segments[-1]['side_range_mm'][1]-length)<=tolerance_mm
            for left,right in zip(segments,segments[1:]):
                valid=valid and abs(left['side_range_mm'][1]-right['side_range_mm'][0])<=tolerance_mm
                valid=valid and np.linalg.norm(np.asarray(left['points_mm'][1])-right['points_mm'][0])<=tolerance_mm
        rows.append(dict(side_index=side,status='PASS' if valid else 'UNKNOWN',segments=segments,coplanar_ambiguity=coplanar))
        chain.extend(segments)
    closed=all(r['status']=='PASS' for r in rows)
    if closed:
        closed=all(np.linalg.norm(np.asarray(a['points_mm'][1])-b['points_mm'][0])<=tolerance_mm for a,b in zip(chain,chain[1:]+chain[:1]))
    return dict(schema='vv-toolbox.mesh-rim-trace/1',status='CANDIDATE' if closed else 'UNKNOWN',
        sides=rows,segment_count=len(chain),closed_within_tolerance=bool(closed),tolerance_mm=tolerance_mm,
        accepted_for_generation=False,
        limitation='Front-facing triangle projection trace only. Multiple layers, gaps or coplanar ambiguity remain UNKNOWN. '
                   'No source faces removed, no lumen union or tangent continuity.')
