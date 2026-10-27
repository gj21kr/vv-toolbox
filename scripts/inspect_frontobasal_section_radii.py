"""Bind noncircular section radius measurements to the saved smoothed path."""
import hashlib
import json
from pathlib import Path
import numpy as np
from vv_toolbox.section_radius_profile import section_radius_profile


def main():
    root=Path(__file__).resolve().parents[1]
    prior=json.loads((root/'docs/evidence/frontobasal-smoothing.json').read_text())
    path=root/prior['artifact']
    if hashlib.sha256(path.read_bytes()).hexdigest()!=prior['sha256']:raise ValueError('Path hash mismatch')
    with np.load(path,allow_pickle=False) as data:
        count=len(data['candidate_points_mm'])
    profile=section_radius_profile(prior['source_sections'],count)
    measured=[r for r in profile['stations'] if r['status']=='MEASURED']
    summary={key:[min(r[key] for r in measured),max(r[key] for r in measured)]
             for key in ['area_equivalent_radius_mm','center_boundary_distance_mm']}
    result=dict(schema='vv-toolbox.frontobasal-section-radii/1',parent_artifact_sha256=prior['sha256'],
        source_case_revision=prior['source_case_revision'],atlas_archive_sha256=prior['atlas_archive_sha256'],
        profile=profile,measurement_ranges=summary,app_applied=False)
    (root/'docs/evidence/frontobasal-section-radii.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(profile['measured_count'],json.dumps(summary),flush=True)


if __name__=='__main__':main()
