"""Record a transported engineering frame for the previously parallel direction."""
import json
from pathlib import Path
import numpy as np
from vv_toolbox.case_io import load_case
from vv_toolbox.saccular_frame import propose_saccular_frame
from vv_toolbox.saccular import saccular_spec
from vv_toolbox.saccular_surface import build_saccular_candidate

ROOT=Path(__file__).resolve().parents[1]


def main():
    path=ROOT/'exports/atlas-case-inspection/all-arterial.snapshot.json'
    before=path.read_bytes()
    case,revision=load_case(path)
    prior=json.loads((ROOT/'docs/evidence/atlas-saccular-candidates.json').read_text())
    if revision!=prior['case_revision']:
        raise ValueError('source changed')
    edge=next(e for e in case['edges'] if e['id']=='FJ1692M:e0')
    station=float(np.linalg.norm(np.diff(edge['centerline_mm'],axis=0),axis=1).sum()/2)
    frame=propose_saccular_frame(case,edge['id'],station,[1,0,0],search_mm=8.)
    spec=saccular_spec(case,lesion_id='manual-left-mca-transport',edge_id=edge['id'],region='mca',
        station_mm=station,**{k:frame[k] for k in ('neck_center_mm','outward_normal','width_direction')},
        neck_width_mm=2.,neck_depth_mm=1.,height_perpendicular_mm=5.,
        dome_width_mm=4.,dome_depth_mm=3.,blending_extent_mm=.5)
    report=dict(frame=frame,specification=spec,context_edge_count=len(case['edges']),
                status='FAIL',surface_published=False,app_applied=False)
    try:
        build_saccular_candidate(case,spec,spacing_mm=.15,max_grid_voxels=2_000_000)
        report.update(status='CANDIDATE',surface_published=False,
                      note='generation only; surface not saved by diagnostic')
    except ValueError as error:
        report['reason']=str(error)
    report['input_unchanged']=path.read_bytes()==before
    if not report['input_unchanged']:
        raise ValueError('source changed')
    (ROOT/'docs/evidence/left-mca-saccular-frame.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='specification'}))


if __name__=='__main__':
    main()
