"""Fixed manual sac designs on four Atlas-derived paths, with full case context."""
import hashlib
import json
from pathlib import Path

import numpy as np

from vv_toolbox.case_io import load_case
from vv_toolbox.saccular import saccular_spec
from vv_toolbox.saccular_surface import build_saccular_candidate

ROOT = Path(__file__).resolve().parents[1]


def main():
    path = ROOT/'exports/atlas-case-inspection/all-arterial.snapshot.json'
    before = path.read_bytes()
    case, revision = load_case(path)
    output = ROOT/'exports/atlas-saccular-candidates'
    output.mkdir(exist_ok=True)
    attempts = []
    # Fixed before execution; no search for a passing location or dimension.
    targets = [('FJ1654:e0','aca'), ('FJ1654M:e0','aca'),
               ('FJ1692:e0','mca'), ('FJ1692M:e0','mca')]
    for edge_id, region in targets:
        row = dict(edge_id=edge_id, region=region, status='FAIL', surface_published=False)
        try:
            edge = next(e for e in case['edges'] if e['id']==edge_id)
            points = np.asarray(edge['centerline_mm'])
            radii = np.asarray(edge['radii_mm'])
            lengths = np.linalg.norm(np.diff(points,axis=0),axis=1)
            stations = np.r_[0.,np.cumsum(lengths)]
            station = float(stations[-1]/2)
            index = min(int(np.searchsorted(stations,station,side='right')-1),len(lengths)-1)
            fraction = (station-stations[index])/lengths[index]
            anchor = points[index]+fraction*(points[index+1]-points[index])
            tangent = (points[index+1]-points[index])/lengths[index]
            # Lateral normal projected perpendicular to local tangent; explicitly
            # engineering placement, not inferred disease site or anatomical ostium.
            lateral = np.array([-1.,0,0]) if edge['anatomy']['side']=='R' else np.array([1.,0,0])
            normal = lateral-tangent*np.dot(lateral,tangent)
            if np.linalg.norm(normal)<1e-8:
                raise ValueError('lateral direction is parallel to local tangent')
            normal /= np.linalg.norm(normal)
            radius = radii[index]+fraction*(radii[index+1]-radii[index])
            spec = saccular_spec(case,lesion_id='manual-'+edge_id,edge_id=edge_id,
                region=region,station_mm=station,
                neck_center_mm=(anchor+radius*normal).tolist(),
                outward_normal=normal.tolist(),width_direction=tangent.tolist(),
                neck_width_mm=2.,neck_depth_mm=1.,height_perpendicular_mm=5.,
                dome_width_mm=4.,dome_depth_mm=3.,blending_extent_mm=.5)
            row.update(station_mm=station, local_radius_mm=float(radius),
                       specification=spec)
            vertices, faces, metadata = build_saccular_candidate(
                case,spec,spacing_mm=.15,max_grid_voxels=2_000_000)
            target = output/(edge_id.replace(':','-')+'.npz')
            np.savez_compressed(target,vertices_mm=vertices,faces=faces,
                                metadata=np.array(json.dumps(metadata)))
            row.update(status='CANDIDATE',surface_published=True,
                       vertices=len(vertices),triangles=len(faces),
                       surface_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
                       metadata=metadata)
        except (ValueError,StopIteration) as error:
            row['reason']=str(error) or 'target source edge missing'
        attempts.append(row)
        print(json.dumps({k:v for k,v in row.items() if k not in ('specification','metadata')}),flush=True)
    if path.read_bytes()!=before:
        raise RuntimeError('source snapshot changed')
    report = dict(schema='vv-toolbox.atlas-saccular-inspection/1',
        case_revision=revision,input_sha256=hashlib.sha256(before).hexdigest(),
        input_unchanged=True,context_edge_count=len(case['edges']),
        design='fixed mid-arc; projected lateral normal; manual engineering dimensions, not literature preset',
        spacing_mm=.15,max_grid_voxels=2_000_000,attempts=attempts,
        attempted_count=len(attempts),
        generated_count=sum(r['surface_published'] for r in attempts),
        anatomy='UNKNOWN',clinical_validity='NOT RUN',app_applied=False)
    (ROOT/'docs/evidence/atlas-saccular-candidates.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':
    main()
