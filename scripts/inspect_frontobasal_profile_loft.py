"""Inspect a noncircular loft of every measured centered-path section."""
import hashlib
import json
from pathlib import Path
import numpy as np
import trimesh
from vv_toolbox.atlas import load_atlas
from vv_toolbox.profile_loft import loft_source_profiles
from vv_toolbox.mesh_self_contact import inspect_self_contact
from vv_toolbox.surface_indexing import exact_vertex_index_copy


def main():
    root=Path(__file__).resolve().parents[1]
    prior=json.loads((root/'docs/evidence/frontobasal-endpoint-sections.json').read_text())
    parent=json.loads((root/'docs/evidence/frontobasal-centering.json').read_text())
    if prior['parent_artifact_sha256']!=parent['sha256']:raise ValueError('Section binding mismatch')
    if hashlib.sha256((root/parent['artifact']).read_bytes()).hexdigest()!=parent['sha256']:raise ValueError('Path changed')
    atlas=load_atlas()
    if atlas.metadata['sha256']!=prior['atlas_archive_sha256']:raise ValueError('Atlas changed')
    p=next(p for p in atlas.meshes if p['id']=='FJ1690')
    source,_=exact_vertex_index_copy(trimesh.Trimesh(p['vertices'],p['faces'],process=False))
    mesh,meta=loft_source_profiles(prior['sections']['profiles'],samples=64)
    contact=inspect_self_contact(mesh.vertices,mesh.faces)
    summary={}
    for name,points in [('vertices',mesh.vertices),('face_centroids',mesh.triangles_center)]:
        distances=[]
        for start in range(0,len(points),128):
            _,d,_=trimesh.proximity.closest_point(source,points[start:start+128]);distances.extend(d.tolist())
        summary[name]=dict(count=len(points),maximum_surface_distance_mm=max(distances),median_surface_distance_mm=float(np.median(distances)))
    output=root/'exports/frontobasal-profile-loft.npz'
    with output.open('xb') as stream:
        np.savez_compressed(stream,vertices_mm=mesh.vertices,faces=mesh.faces,metadata=np.array(json.dumps(meta)))
    report=dict(schema='vv-toolbox.frontobasal-profile-loft/1',parent_path_sha256=parent['sha256'],
        atlas_archive_sha256=atlas.metadata['sha256'],artifact=str(output.relative_to(root)),
        sha256=hashlib.sha256(output.read_bytes()).hexdigest(),loft=meta,self_contact=contact,
        sampled_source_distance=summary,accepted_for_generation=False,
        limitation='Open lateral diagnostic surface. Sampled distances are not a whole-surface bound; no cap, branch seam or surrounding clearance acceptance.')
    (root/'docs/evidence/frontobasal-profile-loft.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(self_contact=contact['status'],pairs=len(contact['contact_pairs']),distance=summary)),flush=True)


if __name__=='__main__':main()
