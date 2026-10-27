"""Locate contacting dome faces relative to the fixed design neck plane."""
import hashlib
import json
from pathlib import Path
import numpy as np
import trimesh
from vv_toolbox.atlas import load_atlas
from vv_toolbox.voxel_output import _inside


def main():
    root=Path(__file__).resolve().parents[1]
    comparison=json.loads((root/'docs/evidence/aca-union-surroundings.json').read_text())
    unions=json.loads((root/'docs/evidence/aca-source-cut-sac-unions.json').read_text())
    item=next(r for r in unions['rows'] if r['parent_part_id']=='FJ1654')
    row=next(r for r in comparison['rows'] if r['parent_part_id']=='FJ1654')
    path=root/item['artifact']
    if hashlib.sha256(path.read_bytes()).hexdigest()!=item['sha256'] or row['artifact_sha256']!=item['sha256']:
        raise ValueError('Candidate identity mismatch')
    with np.load(path,allow_pickle=False) as data:
        v=data['vertices_mm'];f=data['faces'];meta=json.loads(str(data['metadata']))
    neck=meta['specification']['neck'];center=np.asarray(neck['center_mm']);normal=np.asarray(neck['normal'])
    pairs=next(c for c in row['checks'] if c['part_id']=='FJ1690')['dome_contact_pairs']
    ids=np.unique(np.asarray(pairs)[:,0]);heights=(v[f[ids]]-center)@normal
    rim_heights=(v[meta['opening']['neck_boundary_vertex_ids']]-center)@normal
    atlas=load_atlas()
    if atlas.metadata['sha256']!=unions['atlas_archive_sha256']:raise ValueError('Atlas identity mismatch')
    part=next(p for p in atlas.meshes if p['id']=='FJ1690')
    points,inverse=np.unique(np.asarray(part['vertices'],float),axis=0,return_inverse=True)
    faces=inverse[np.asarray(part['faces'])]
    if not trimesh.Trimesh(vertices=points,faces=faces,process=False).is_volume:
        raise ValueError('Closed oriented neighbor required for containment sampling')
    rim_inside=_inside(v[meta['opening']['neck_boundary_vertex_ids']],points[faces],1e-8)
    report=dict(schema='vv-toolbox.contact-face-height/1',artifact_sha256=item['sha256'],
        part_id='FJ1654',other_part_id='FJ1690',contact_face_count=len(ids),
        contact_face_height_range_mm=[float(heights.min()),float(heights.max())],
        rim_height_range_mm=[float(rim_heights.min()),float(rim_heights.max())],
        requested_dome_height_mm=meta['specification']['parameters']['height_perpendicular_mm'],
        atlas_archive_sha256=atlas.metadata['sha256'],
        rim_samples_inside_or_on_neighbor=np.flatnonzero(rim_inside).tolist(),
        rim_sample_count=len(rim_inside),rim_containment_tolerance_mm=1e-8,
        interpretation='All vertices of contacting dome faces are below the design neck plane, in the warped rim region.',
        limitation='Face-vertex height bounds, not exact intersection points or clinical lesion location.')
    (root/'docs/evidence/right-aca-contact-height.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
