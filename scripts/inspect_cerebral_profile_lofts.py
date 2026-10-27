"""Create and inspect open noncircular candidates on every frozen source profile."""
import hashlib
import argparse
import json
from pathlib import Path

import numpy as np
import trimesh

from vv_toolbox.atlas import load_atlas
from vv_toolbox.profile_loft import loft_source_profiles


def main(*, smoothed=False, tangent_half_window_mm=None):
    root=Path(__file__).resolve().parents[1]
    index_path=root/'docs/evidence'/('cerebral-smoothed-section-profiles.json' if smoothed else 'cerebral-source-section-profiles.json')
    if tangent_half_window_mm is not None:
        index_path=index_path.with_stem(index_path.stem+f'-window{tangent_half_window_mm:g}mm')
    index_raw=index_path.read_bytes();index=json.loads(index_raw)
    atlas=load_atlas();parts={p['id']:p for p in atlas.meshes}
    if atlas.metadata['sha256']!=index['atlas_archive_sha256']:
        raise ValueError('Atlas source mismatch')
    rows=[]
    for entry in index['rows']:
        raw=(root/entry['artifact']).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=entry['sha256']:raise ValueError('Profile hash mismatch')
        profiles=json.loads(raw);part=parts[profiles['source_part_id']]
        if profiles['source_case_revision']!=entry.get('case_revision',index['source_case_revision']):
            raise ValueError('Profile revision mismatch')
        source=trimesh.Trimesh(part['vertices'],part['faces'],process=False)
        triangles_hash=hashlib.sha256(np.asarray(source.triangles,dtype='<f8').tobytes()).hexdigest()
        if triangles_hash!=entry['original_triangle_sha256']:raise ValueError('Source triangles mismatch')
        row=dict(edge_id=entry['edge_id'],profile_sha256=entry['sha256'],status='UNKNOWN')
        try:
            candidate,metadata=loft_source_profiles(profiles['profiles'],samples=64)
        except ValueError as error:
            row.update(status='FAIL',reason=str(error))
        else:
            measures={}
            for name,points in [('vertices',candidate.vertices),('face_centroids',candidate.triangles_center)]:
                distances=[]
                for start in range(0,len(points),2048):
                    _,d,_=trimesh.proximity.closest_point(source,points[start:start+2048])
                    distances.extend(d.tolist())
                measures[name]=dict(count=len(distances),maximum_mm=float(np.max(distances)),
                                    p95_mm=float(np.percentile(distances,95)))
                if name=='face_centroids':
                    worst=np.argsort(distances)[-3:][::-1]
                    measures[name]['worst_samples']=[
                        dict(face_index=int(k),distance_mm=float(distances[k]),
                             position_mm=points[k].tolist(),
                             profile_indices=[profiles['profiles'][int(k)//128+j]['index'] for j in (0,1)])
                        for k in worst]
            payload=candidate.export(file_type='ply')
            digest=hashlib.sha256(payload).hexdigest()
            destination=root/'exports/cerebral-profile-lofts'/digest/'surface.ply'
            destination.parent.mkdir(parents=True,exist_ok=True)
            if destination.exists() and destination.read_bytes()!=payload:
                raise ValueError('Existing candidate differs')
            destination.write_bytes(payload)
            row.update(status='CANDIDATE',metadata=metadata,triangles=len(candidate.faces),
                       source_distance_samples=measures,sha256=digest,
                       artifact=destination.relative_to(root).as_posix())
        rows.append(row)
        print(json.dumps(dict(edge_id=row['edge_id'],status=row['status'],
                             distances=row.get('source_distance_samples'))),flush=True)
    report=dict(scope='Open interior profile loft candidates; no tube/junction acceptance',
                centerline_group='smoothed' if smoothed else 'source',
                tangent_half_window_mm=tangent_half_window_mm,
                source_profile_index_sha256=hashlib.sha256(index_raw).hexdigest(),
                atlas_archive_sha256=atlas.metadata['sha256'],rows=rows,
                original_modified=False,continuous_surface_error='NOT RUN',
                self_intersection='NOT RUN',anatomical_validation='NOT RUN')
    output='cerebral-smoothed-profile-lofts.json' if smoothed else 'cerebral-profile-lofts.json'
    if tangent_half_window_mm is not None:
        output=output.replace('.json',f'-window{tangent_half_window_mm:g}mm.json')
    (root/'docs/evidence'/output).write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--smoothed',action='store_true')
    parser.add_argument('--tangent-window-mm',type=float)
    args=parser.parse_args()
    main(smoothed=args.smoothed,tangent_half_window_mm=args.tangent_window_mm)
