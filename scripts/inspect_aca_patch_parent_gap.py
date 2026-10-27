"""Measure exact saved candidate rim distances to its original Atlas parent."""
import hashlib
import json
from pathlib import Path
import numpy as np
import trimesh
from vv_toolbox.atlas import load_atlas


def main():
    root=Path(__file__).resolve().parents[1]
    prior=json.loads((root/'docs/evidence/aca-direction-candidates.json').read_text())
    atlas=load_atlas()
    if atlas.metadata['sha256']!=prior['atlas_archive_sha256']:raise ValueError('Atlas changed')
    parts={p['id']:p for p in atlas.meshes};rows=[]
    targets=[r for r in prior['attempts'] if r['status']=='NO_OTHER_SURFACE_CONTACT_DETECTED']
    for row in targets:
        path=root/row['artifact'];before=path.read_bytes()
        if hashlib.sha256(before).hexdigest()!=row['artifact_sha256']:raise ValueError('Patch changed')
        with np.load(path,allow_pickle=False) as data:
            vertices=data['vertices_mm'];meta=json.loads(str(data['metadata']))
        part=parts[row['parent_part_id']]
        mesh=trimesh.Trimesh(vertices=part['vertices'],faces=part['faces'],process=False)
        original_is_volume=bool(mesh.is_volume)
        unique,inverse=np.unique(np.asarray(part['vertices']),axis=0,return_inverse=True)
        normalized_faces=inverse[np.asarray(part['faces'])]
        if not np.array_equal(unique[normalized_faces],np.asarray(part['vertices'])[np.asarray(part['faces'])]):
            raise ValueError('Exact-index normalization changed source triangles')
        mesh=trimesh.Trimesh(vertices=unique,faces=normalized_faces,process=False)
        rim=vertices[:meta['boundary_vertex_count']]
        closest,distances,face_ids=trimesh.proximity.closest_point(mesh,rim)
        inside=mesh.contains(vertices).tolist() if mesh.is_volume else None
        result=dict(junction_id=row['junction_id'],direction_name=row['direction_name'],
            artifact_sha256=row['artifact_sha256'],parent_part_id=row['parent_part_id'],parent_name=part['name'],
            parent_is_volume=bool(mesh.is_volume),rim_sample_count=len(rim),rim_distances_mm=distances.tolist(),
            raw_parent_is_volume=original_is_volume,normalization='exact coordinate duplicate indices only; triangle coordinates unchanged',
            closest_parent_points_mm=closest.tolist(),closest_parent_face_ids=face_ids.tolist(),
            minimum_rim_distance_mm=float(distances.min()),maximum_rim_distance_mm=float(distances.max()),
            median_rim_distance_mm=float(np.median(distances)),
            candidate_vertex_count=len(vertices),inside_parent_vertex_count=sum(inside) if inside is not None else None,
            vertex_containment_scope='All candidate vertices only, not whole triangles or closed volume',
            attachment='UNKNOWN',accepted_for_generation=False,input_unchanged=path.read_bytes()==before)
        if not result['input_unchanged']:raise RuntimeError('Patch changed during inspection')
        rows.append(result)
        print(json.dumps({k:v for k,v in result.items() if k not in ('rim_distances_mm','closest_parent_points_mm','closest_parent_face_ids')}),flush=True)
    report=dict(schema='vv-toolbox.aca-patch-parent-gap/1',atlas_archive_sha256=atlas.metadata['sha256'],
        case_revision=prior['case_revision'],rows=rows,app_applied=False,accepted_for_generation=False,
        limitation='Nearest points are measurements, not new boundary vertices or attachment approval.')
    (root/'docs/evidence/aca-patch-parent-gap.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')


if __name__=='__main__':main()
