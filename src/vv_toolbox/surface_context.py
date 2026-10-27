"""Conservative triangle-to-profile screening, with explicit overlap witnesses."""
import numpy as np
from .case_contract import validate_case
from .saccular_surface import _parent_field


def inspect_surface_artifact(case,path,*,parent_edge_id,expected_sha256):
    """Bind inspection to exact NPZ bytes and declared case frame/revision."""
    import hashlib
    import io
    import json
    from pathlib import Path
    from .case_io import case_digest, _unique_object
    revision=case_digest(case)
    raw=Path(path).read_bytes()
    actual=hashlib.sha256(raw).hexdigest()
    if actual != expected_sha256.lower():
        raise ValueError('surface artifact hash mismatch')
    with np.load(io.BytesIO(raw),allow_pickle=False) as data:
        if not {'vertices_mm','faces','metadata'} <= set(data.files):
            raise ValueError('surface artifact requires vertices_mm, faces and metadata')
        metadata=json.loads(str(data['metadata'].item()),object_pairs_hook=_unique_object)
        if not isinstance(metadata,dict) or metadata.get('case_revision') != revision:
            raise ValueError('surface case revision mismatch')
        if metadata.get('frame') != case['frame']:
            raise ValueError('surface coordinate frame mismatch')
        report=inspect_surface_context(case,data['vertices_mm'],data['faces'],parent_edge_id=parent_edge_id)
    report.update(case_revision=revision,artifact_sha256=actual,
                  provenance_scope='declared metadata and exact bytes; not independent geometry authenticity')
    return report


def _interior_witness(triangles,face_ids,points,radii,max_depth=3,max_samples=100000):
    """Bounded barycentric sampling; absence of a witness never proves separation."""
    pending=[(int(i),np.eye(3),0) for i in face_ids]
    sampled=0
    while pending and sampled < max_samples:
        face,bary,depth=pending.pop()
        weights=bary.mean(axis=0)
        point=weights@triangles[face]
        value=float(_parent_field(point[None,:],points,radii)[0])
        sampled+=1
        if value < -1e-6:
            return dict(face_index=face,barycentric=weights.tolist(),
                        position_mm=point.tolist(),profile_field_mm=value),sampled
        if depth < max_depth:
            a,b,c=bary
            ab,bc,ca=(a+b)/2,(b+c)/2,(c+a)/2
            pending.extend((face,np.array(child),depth+1) for child in
                           ((a,ab,ca),(ab,b,bc),(ca,bc,c),(ab,bc,ca)))
    return None,sampled


def refine_profile_separation(vertices,faces,points,radii,*,max_depth=8,max_cells=100000):
    """Prove triangle coverage by disjoint cells, or retain an unresolved result."""
    if type(max_depth) is not int or not 0<=max_depth<=12:
        raise ValueError('max_depth must be between 0 and 12')
    if type(max_cells) is not int or not 1<=max_cells<=1000000:
        raise ValueError('max_cells must be between 1 and 1000000')
    vertices=np.asarray(vertices,dtype=float);faces=np.asarray(faces)
    points=np.asarray(points,dtype=float);radii=np.asarray(radii,dtype=float)
    if (vertices.ndim!=2 or vertices.shape[1]!=3 or not np.isfinite(vertices).all()
            or faces.ndim!=2 or faces.shape[1]!=3 or not len(faces)
            or not np.issubdtype(faces.dtype,np.integer) or faces.min()<0 or faces.max()>=len(vertices)
            or points.ndim!=2 or points.shape[1]!=3 or len(points)<2
            or radii.shape!=(len(points),) or not np.isfinite(points).all()
            or not np.isfinite(radii).all() or np.any(radii<=0)):
        raise ValueError('valid triangles and profile required')
    delta=np.diff(points,axis=0)
    squared=np.sum(delta*delta,axis=1)
    if np.any(squared<=1e-24):
        raise ValueError('degenerate profile interval')
    triangles=vertices[faces]
    pending=[(i,np.eye(3),0) for i in range(len(faces))]
    unresolved=0;checked=0;minimum=np.inf
    while pending and checked<max_cells:
        face,bary,depth=pending.pop()
        cell=bary@triangles[face]
        center=cell.mean(axis=0)
        enclosing=np.linalg.norm(cell-center,axis=1).max()
        t=np.clip(np.sum((center-points[:-1])*delta,axis=1)/squared,0,1)
        bound=float(np.min(np.linalg.norm(center-points[:-1]-t[:,None]*delta,axis=1)
                            -np.maximum(radii[:-1],radii[1:]))-enclosing)
        checked+=1
        if bound>0:
            minimum=min(minimum,bound)
            continue
        field=float(_parent_field(center[None,:],points,radii)[0])
        if field < -1e-6:
            return dict(status='PROFILE_INTERIOR_WITNESS',checked_cells=checked,
                witness=dict(face_index=face,barycentric=bary.mean(axis=0).tolist(),
                             position_mm=center.tolist(),profile_field_mm=field))
        if depth==max_depth:
            unresolved+=1
        else:
            a,b,c=bary
            ab,bc,ca=(a+b)/2,(b+c)/2,(c+a)/2
            pending.extend((face,np.array(child),depth+1) for child in
                           ((a,ab,ca),(ab,b,bc),(ca,bc,c),(ab,bc,ca)))
    unresolved+=len(pending)
    return dict(status='UNKNOWN' if unresolved else 'SEPARATED_PROFILE',
                checked_cells=checked,unresolved_cells=unresolved,
                lower_bound_mm=float(minimum) if not unresolved else None,
                max_depth=max_depth,max_cells=max_cells)


def inspect_surface_context(case,vertices,faces,*,parent_edge_id):
    validate_case(case)
    vertices=np.asarray(vertices,dtype=float)
    faces=np.asarray(faces)
    if (vertices.ndim!=2 or vertices.shape[1]!=3 or not len(vertices)
            or not np.isfinite(vertices).all() or faces.ndim!=2 or faces.shape[1]!=3
            or not len(faces) or not np.issubdtype(faces.dtype,np.integer)
            or faces.min()<0 or faces.max()>=len(vertices)):
        raise ValueError('valid finite triangle surface required')
    if parent_edge_id not in {e['id'] for e in case['edges']}:
        raise ValueError('parent edge missing')
    parent=next(e for e in case['edges'] if e['id']==parent_edge_id)
    triangles=vertices[faces]
    used_ids=np.unique(faces)
    surface_vertices=vertices[used_ids]
    centers=triangles.mean(axis=1)
    enclosing=np.linalg.norm(triangles-centers[:,None,:],axis=2).max(axis=1)
    lo,hi=surface_vertices.min(axis=0),surface_vertices.max(axis=0)
    rows=[]
    excluded=0
    for edge in case['edges']:
        if edge['id']==parent_edge_id:
            continue
        if edge['centerline_mm'] is None:
            rows.append(dict(edge_id=edge['id'],status='UNKNOWN',reason='unresolved context geometry'))
            continue
        points,radii=np.asarray(edge['centerline_mm']),np.asarray(edge['radii_mm'])
        if np.any(lo>points.max(axis=0)+radii.max()) or np.any(hi<points.min(axis=0)-radii.max()):
            excluded+=1
            continue
        # Max-endpoint-radius capsules enclose the specified linear profile.
        # Distance to each capsule is 1-Lipschitz, so subtracting a triangle
        # enclosing radius yields a lower bound over that entire triangle.
        bound=np.full(len(centers),np.inf)
        for a,b,r0,r1 in zip(points,points[1:],radii,radii[1:]):
            delta=b-a
            t=np.clip((centers-a)@delta/(delta@delta),0,1)
            values=np.linalg.norm(centers-a-t[:,None]*delta,axis=1)-max(r0,r1)-enclosing
            bound=np.minimum(bound,values)
        minimum=float(bound.min())
        if minimum>0:
            rows.append(dict(edge_id=edge['id'],status='SEPARATED_PROFILE',lower_bound_mm=minimum))
            continue
        vertex_field=_parent_field(surface_vertices,points,radii)
        index=int(vertex_field.argmin())
        witness=None
        overlap=None
        if vertex_field[index]<-1e-6:
            witness=dict(vertex_index=int(used_ids[index]),position_mm=surface_vertices[index].tolist(),
                         profile_field_mm=float(vertex_field[index]))
            indices=np.flatnonzero(vertex_field < -1e-6)
            points_inside=surface_vertices[indices]
            overlap=dict(vertex_count=len(indices),
                         bounds_mm=[points_inside.min(axis=0).tolist(),points_inside.max(axis=0).tolist()],
                         baseline_parent_status='UNKNOWN')
            if parent['centerline_mm'] is not None:
                baseline=_parent_field(points_inside,np.asarray(parent['centerline_mm']),
                                       np.asarray(parent['radii_mm']))
                farthest=int(baseline.argmax())
                overlap.update(
                    baseline_parent_status='MEASURED',
                    baseline_inside_count=int(np.count_nonzero(baseline < -1e-6)),
                    baseline_surface_band_count=int(np.count_nonzero(np.abs(baseline) <= 1e-6)),
                    baseline_outside_count=int(np.count_nonzero(baseline > 1e-6)),
                    baseline_field_range_mm=[float(baseline.min()),float(baseline.max())],
                    farthest_outside_vertex_index=int(used_ids[indices[farthest]]),
                    farthest_outside_position_mm=points_inside[farthest].tolist())
        interior_samples=0
        if witness is None:
            witness,interior_samples=_interior_witness(
                triangles,np.flatnonzero(bound<=0),points,radii)
        rows.append(dict(edge_id=edge['id'],status='PROFILE_INTERIOR_WITNESS' if witness else 'UNKNOWN',
                         lower_bound_mm=minimum,witness=witness,overlap_vertices=overlap,
                         interior_samples=interior_samples,
                         reason='bound overlaps; not an original atlas mesh collision verdict'))
    return dict(schema='vv-toolbox.surface-context/1',parent_edge_id=parent_edge_id,
        context_edge_count=len(case['edges'])-1,aabb_separated_count=excluded,
        used_vertex_count=len(used_ids),unused_vertex_count=len(vertices)-len(used_ids),
        results=rows,status='SEPARATED_PROFILES' if all(r['status']=='SEPARATED_PROFILE' for r in rows) else 'REVIEW_REQUIRED',
        scope='candidate triangles versus declared centerline/radius profiles; parent excluded',
        original_mesh_collision='NOT RUN',anatomical_connection='UNKNOWN',
        interior_sampling=dict(max_depth=3,max_samples_per_edge=100000,
                               negative_result='UNKNOWN; finite samples do not prove separation'),
        limitation='A negative lower bound is inconclusive. Vertex counts depend on tessellation and are not overlap volume. Baseline exterior points can reflect meshing error as well as added geometry; intended junctions are not classified.')
