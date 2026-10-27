"""Create a bounded separate MCA baseline; no old sac specification is reused."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import numpy as np
from vv_toolbox.case_io import load_case, save_case
from vv_toolbox.centerline_regularization import smooth_synthetic_centerlines
from vv_toolbox.radius_regularization import smooth_synthetic_radii

ROOT=Path(__file__).resolve().parents[1]


def measures(edge):
    p,r=np.array(edge['centerline_mm']),np.array(edge['radii_mm'])
    d=np.diff(p,axis=0)
    lengths=np.linalg.norm(d,axis=1)
    unit=d/lengths[:,None]
    angles=np.degrees(np.arccos(np.clip(np.sum(unit[1:]*unit[:-1],axis=1),-1,1)))
    return dict(length_mm=float(lengths.sum()),turn_p95_deg=float(np.percentile(angles,95)),
                radius_total_variation_mm=float(np.abs(np.diff(r)).sum()),
                radius_range_mm=[float(r.min()),float(r.max())])


def main():
    source=ROOT/'exports/atlas-case-inspection/all-arterial.snapshot.json'
    original=source.read_bytes()
    case,revision=load_case(source)
    parent='FJ1692:e0'
    baseline=deepcopy(case)
    baseline.update(case_id='mca-profile-baseline',model_kind='synthetic',
        generation=dict(seed=0,generator_version='explicit-source-fork-1',
                        config=dict(parent_case_revision=revision)))
    # Engineering limits fixed before execution, not clinical error tolerances.
    config=dict(sigma_mm=.6,sample_spacing_mm=.1)
    report=dict(source_case_revision=revision,edge_id=parent,configuration=dict(
        **config,max_displacement_mm=.3,max_radius_change_mm=.3),app_applied=False,
        anatomy='UNKNOWN',junction_continuity='NOT RUN',surface_collision='NOT RUN')
    try:
        moved=smooth_synthetic_centerlines(baseline,[parent],**config,
            max_displacement_mm=.3,case_id='mca-centerline-regularized')
        result=smooth_synthetic_radii(moved,[parent],**config,
            max_change_mm=.3,case_id='mca-profile-regularized')
        source_edge=next(e for e in case['edges'] if e['id']==parent)
        target_edge=next(e for e in result['edges'] if e['id']==parent)
        unchanged=(case['nodes']==result['nodes'] and
            [e for e in case['edges'] if e['id']!=parent]==
            [e for e in result['edges'] if e['id']!=parent])
        if not unchanged:
            raise ValueError('non-target geometry changed')
        out=ROOT/'exports/mca-profile-regularization/case.snapshot.json'
        expected=load_case(out)[1] if out.exists() else None
        derived_revision=save_case(out,result,expected_revision=expected)
        report.update(status='CANDIDATE',case_revision=derived_revision,
            before=measures(source_edge),after=measures(target_edge),
            centerline_metrics=result['centerline_regularization']['metrics'],
            radius_metrics=result['radius_regularization']['metrics'],
            other_edges_and_nodes_unchanged=unchanged,
            artifact_sha256=hashlib.sha256(out.read_bytes()).hexdigest(),
            sac_regeneration='NOT RUN; old neck/specification belongs to original revision')
    except ValueError as error:
        report.update(status='FAIL',reason=str(error))
    report['source_unchanged']=source.read_bytes()==original
    if not report['source_unchanged']:
        raise ValueError('source changed')
    (ROOT/'docs/evidence/mca-profile-regularization.json').write_text(
        json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps(report))


if __name__=='__main__':
    main()
