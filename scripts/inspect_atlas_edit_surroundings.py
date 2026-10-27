"""Compare MCA edit intersections with every other native arterial surface."""
import hashlib
import argparse
from copy import deepcopy
import json
from pathlib import Path
from urllib.request import urlopen
import numpy as np
import trimesh
from scipy.spatial import cKDTree
from vv_toolbox.atlas import load_atlas
from vv_toolbox.atlas_modification import deform_part
from vv_toolbox.mesh_pair_contact import inspect_pair_contact
from vv_toolbox.mesh_self_contact import inspect_self_contact

ROOT=Path(__file__).resolve().parents[1]


def boundary_angles(original,edited):
    before=trimesh.Trimesh(vertices=original['vertices'],faces=original['faces'],process=False)
    after=trimesh.Trimesh(vertices=edited['vertices'],faces=edited['faces'],process=False)
    pairs=before.face_adjacency
    fixed=np.all(original['vertices']==edited['vertices'],axis=1)
    vertices=original['faces'][pairs].reshape(-1,6)
    boundary=np.any(fixed[vertices],axis=1)&np.any(~fixed[vertices],axis=1)
    def summarize(values):
        return dict(count=len(values),max_deg=float(values.max()) if len(values) else None,
                    p95_deg=float(np.percentile(values,95)) if len(values) else None,
                    above_90=int(np.count_nonzero(values>90)))
    first=np.degrees(before.face_adjacency_angles)
    second=np.degrees(after.face_adjacency_angles)
    if not np.array_equal(pairs,after.face_adjacency):
        raise ValueError('Adjacency correspondence changed')
    return dict(fixed_vertices=int(fixed.sum()),moving_vertices=int((~fixed).sum()),
                before=summarize(first[boundary]),after=summarize(second[boundary]),
                newly_above_90_pairs=int(np.count_nonzero(boundary&(first<=90)&(second>90))),
                smoothness='UNKNOWN',
                scope='Pairs touching both exactly fixed and displaced source vertices; includes endpoint and optional protected-region boundaries',
                limitation='Face-normal angles are tessellation-dependent; no curvature or smoothness acceptance threshold established.')


def displacement_diagnostics(original,edited,contacts):
    v=np.asarray(original['vertices']);moved=np.asarray(edited['vertices']);faces=original['faces']
    delta=moved-v
    mesh=trimesh.Trimesh(vertices=v,faces=faces,process=False)
    links=mesh.edges_unique
    length=np.linalg.norm(v[links[:,1]]-v[links[:,0]],axis=1)
    strain=np.linalg.norm(delta[links[:,1]]-delta[links[:,0]],axis=1)/np.maximum(length,1e-15)
    implicated=sorted({face for pair in contacts for face in pair})
    triangles=[]
    for face in implicated:
        ids=faces[face];a=v[ids];b=moved[ids]
        na=np.cross(a[1]-a[0],a[2]-a[0]);nb=np.cross(b[1]-b[0],b[2]-b[0])
        triangles.append(dict(face_id=face,vertex_ids=ids.tolist(),
            original_mm=a.tolist(),edited_mm=b.tolist(),
            vertex_displacement_mm=np.linalg.norm(delta[ids],axis=1).tolist(),
            exactly_fixed=np.all(a==b,axis=1).tolist(),
            area_ratio=float(np.linalg.norm(nb)/np.linalg.norm(na)),
            normal_cosine=float(na@nb/(np.linalg.norm(na)*np.linalg.norm(nb)))))
    top=np.argsort(strain)[-10:][::-1]
    return dict(top_displacement_gradient_edges=[
        dict(vertex_ids=links[i].tolist(),source_length_mm=float(length[i]),
             displacement_difference_over_source_length=float(strain[i])) for i in top],
        contact_faces=triangles,
        interpretation='Large displacement differences identify local deformation concentration, not a proof of volume inversion. Normal changes also include valid rotations.')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--protect-contacts',action='store_true')
    parser.add_argument('--transition-width-mm',type=float,choices=[4.,8.])
    parser.add_argument('--anchor-blend',choices=['minimum','product'],default='minimum')
    parser.add_argument('--field-version',choices=['v1','v2','v3'],default='v1')
    parser.add_argument('--integration-steps',type=int,default=0)
    parser.add_argument('--radial-mode',choices=['tangent','polyline'],default='tangent')
    parser.add_argument('--subdivision-level',type=int,choices=[0,1,2],default=0)
    args=parser.parse_args()
    if args.transition_width_mm is not None and not args.protect_contacts:
        parser.error('transition width requires protected contacts')
    with urlopen('http://127.0.0.1:8093/api/export',timeout=30) as response:
        raw=response.read()
    bundle=json.loads(raw)
    if bundle['schema']!='vv-toolbox.atlas-workspace/1' or bundle['modifications']:
        raise ValueError('Unmodified atlas required')
    atlas=load_atlas()
    part=next(p for p in atlas.meshes if p['id']=='FJ1692')
    edges=[e for e in bundle['centerlines']['edges'] if e['part_id']==part['id']]
    parameters=dict(radius_scale=1.3,tortuosity=.3,torsion_deg=35.)
    protection=[]
    if args.protect_contacts:
        previous=json.loads((ROOT/'docs/evidence/atlas-mca-edit-surroundings.json').read_text())
        triangles=np.asarray(part['vertices'])[part['faces']]
        fingerprint=hashlib.sha256(np.asarray(triangles,dtype='<f8').tobytes()).hexdigest()
        if previous['surface_sha256']['before']!=fingerprint or previous['archive_sha256']!=atlas.metadata['sha256']:
            raise ValueError('Baseline contact evidence mismatch')
        face_ids=sorted({pair[0] for row in previous['results'] for pair in row['before']['contact_pairs']})
        contact_vertices=np.unique(part['faces'][face_ids])
        points=np.concatenate([np.asarray(e['points']) for e in edges])
        radii=np.concatenate([np.asarray(e['radii']) for e in edges])
        _,indices=cKDTree(points).query(part['vertices'][contact_vertices])
        for index in np.unique(indices):
            group=part['vertices'][contact_vertices[indices==index]]
            radius=max(float(radii[index]*1.5),float(np.linalg.norm(group-points[index],axis=1).max())+1e-8)
            protection.append(dict(center_mm=points[index].tolist(),radius_mm=radius))
            if args.transition_width_mm is not None:
                protection[-1]['transition_width_mm']=args.transition_width_mm
    source_vertex_count=len(part['vertices'])
    source_fingerprint=hashlib.sha256(np.asarray(part['vertices'][part['faces']],dtype='<f8').tobytes()).hexdigest()
    support=None
    attachment_vertices=contact_vertices if protection else np.array([],dtype=int)
    if args.subdivision_level:
        if not (args.protect_contacts and args.field_version=='v3' and args.radial_mode=='polyline'
                and args.integration_steps==32 and args.anchor_blend=='product' and args.transition_width_mm==8):
            parser.error('Subdivision comparison requires the frozen protected v3/polyline flow32 case')
        frozen=json.loads((ROOT/'docs/evidence/atlas-mca-protected-edit-surroundings-width8-product-v3-polyline-flow32.json').read_text())
        if (frozen['input_export_sha256']!=hashlib.sha256(raw).hexdigest()
                or frozen['surface_sha256']['before']!=source_fingerprint
                or frozen['protected_regions']!=protection or frozen['parameters']!=parameters):
            raise ValueError('Frozen subdivision source mismatch')
        support=frozen['deformation_method']['field_support_mm']
        part=deepcopy(part)
        descendants=np.asarray(face_ids)
        for _ in range(args.subdivision_level):
            part['vertices'],part['faces']=trimesh.remesh.subdivide(part['vertices'],part['faces'])
            descendants=(4*descendants[:,None]+np.arange(4)).reshape(-1)
        attachment_vertices=np.unique(part['faces'][descendants])
    edited,edited_edges=deform_part(part,edges,parameters,protected_regions=protection,anchor_blend=args.anchor_blend,field_version=args.field_version,
                                  radial_mode=args.radial_mode,integration_steps=args.integration_steps,field_support_mm=support)
    surfaces=[np.asarray(p['vertices'])[p['faces']] for p in (part,edited)]
    rows=[]
    for other in atlas.meshes:
        if other['layer']!='arterial' or other['id']==part['id']:
            continue
        triangles=np.asarray(other['vertices'])[other['faces']]
        row=dict(part_id=other['id'],name=other['name'])
        for name,mesh in zip(('before','after'),surfaces):
            if np.any(mesh.min(axis=(0,1))>triangles.max(axis=(0,1))+1e-8) or np.any(
                    triangles.min(axis=(0,1))>mesh.max(axis=(0,1))+1e-8):
                row[name]=dict(status='AABB_SEPARATED',complete=True,checked_pairs=0,contact_pairs=[])
            else:
                row[name]=inspect_pair_contact(mesh,triangles)
        row['contact_pair_ids_unchanged']=set(map(tuple,row['before']['contact_pairs']))==set(map(tuple,row['after']['contact_pairs']))
        rows.append(row)
    previous={r['part_id'] for r in rows if r['before']['status']=='CONTACT_DETECTED'}
    current={r['part_id'] for r in rows if r['after']['status']=='CONTACT_DETECTED'}
    report=dict(part_id=part['id'],parameters=parameters,
                subdivision_level=args.subdivision_level,
                source_surface_sha256=source_fingerprint,
                source_vertex_count=source_vertex_count,derived_vertex_count=len(part['vertices']),
                attachment_patch_vertex_count=len(attachment_vertices),
                attachment_patch_vertices_exact=bool(np.array_equal(
                    edited['vertices'][attachment_vertices],part['vertices'][attachment_vertices])),
                attachment_patch_max_displacement_mm=float(np.linalg.norm(
                    edited['vertices'][attachment_vertices]-part['vertices'][attachment_vertices],axis=1).max()) if len(attachment_vertices) else None,
                archive_sha256=atlas.metadata['sha256'],
                input_export_sha256=hashlib.sha256(raw).hexdigest(),
                surface_sha256={name:hashlib.sha256(np.asarray(mesh,dtype='<f8').tobytes()).hexdigest()
                                for name,mesh in zip(('before','after'),surfaces)},
                checked_other_arterial_parts=len(rows),results=rows,
                new_contact_parts=sorted(current-previous),removed_contact_parts=sorted(previous-current),
                persistent_contact_parts=sorted(current&previous),
                unresolved_parts=[r['part_id'] for r in rows if not r['before']['complete'] or not r['after']['complete']],
                containment='NOT RUN',anatomical_connection='UNKNOWN',live_workspace_modified=False,
                protected_regions=protection,
                anchor_blend=args.anchor_blend,
                field_version=args.field_version,
                deformation_method=edited['modification'],
                original_contact_vertices_exact=(bool(np.array_equal(
                    edited['vertices'][contact_vertices],part['vertices'][contact_vertices])) if protection else None),
                protection_basis='Original surface contact projected to source centerline samples; not anatomical approval' if protection else None,
                maximum_surface_displacement_mm=float(np.linalg.norm(edited['vertices']-part['vertices'],axis=1).max()),
                maximum_centerline_displacement_mm=max(float(np.linalg.norm(
                    np.asarray(changed['points'])-original['points'],axis=1).max())
                    for original,changed in zip(edges,edited_edges)),
                boundary_angles=boundary_angles(part,edited),
                self_contact=inspect_self_contact(edited['vertices'],edited['faces']),
                scope='Native atlas arterial surface intersections only. Estimated neck vessels, veins and volume containment excluded.')
    report['deformation_diagnostics']=displacement_diagnostics(
        part,edited,report['self_contact']['contact_pairs'])
    filename='atlas-mca-protected-edit-surroundings.json' if args.protect_contacts else 'atlas-mca-edit-surroundings.json'
    if args.transition_width_mm is not None:
        filename=filename.replace('.json',f'-width{args.transition_width_mm:g}.json')
    if args.anchor_blend!='minimum':
        filename=filename.replace('.json',f'-{args.anchor_blend}.json')
    if args.field_version!='v1':
        filename=filename.replace('.json',f'-{args.field_version}.json')
    if args.radial_mode!='tangent':
        filename=filename.replace('.json',f'-{args.radial_mode}.json')
    if args.integration_steps:
        filename=filename.replace('.json',f'-flow{args.integration_steps}.json')
    if args.subdivision_level:
        filename=filename.replace('.json',f'-subdiv{args.subdivision_level}.json')
    (ROOT/'docs/evidence'/filename).write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('results','protected_regions','deformation_diagnostics','deformation_method')}))
    print('protected regions',len(protection))


if __name__=='__main__':
    main()
