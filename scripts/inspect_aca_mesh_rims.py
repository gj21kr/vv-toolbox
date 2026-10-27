"""Original Atlas surface projection for the two noncrossing dome directions."""
import json
from pathlib import Path
from vv_toolbox.atlas import load_atlas
from vv_toolbox.mesh_rim_projection import project_rim_to_mesh


def main():
    root=Path(__file__).resolve().parents[1]
    prior=json.loads((root/'docs/evidence/aca-direction-candidates.json').read_text())
    atlas=load_atlas()
    if atlas.metadata['sha256']!=prior['atlas_archive_sha256']:raise ValueError('Atlas changed')
    parts={p['id']:p for p in atlas.meshes};rows=[]
    for row in prior['attempts']:
        if row['status']!='NO_OTHER_SURFACE_CONTACT_DETECTED':continue
        p=parts[row['parent_part_id']];neck=row['specification']['neck']
        result=project_rim_to_mesh(p['vertices'],p['faces'],neck['curve_mm'],neck['normal'],lower_mm=-5.,upper_mm=5.)
        rows.append(dict(junction_id=row['junction_id'],direction_name=row['direction_name'],parent_part_id=p['id'],
                         specification=row['specification'],projection=result))
        print(json.dumps(dict(junction=row['junction_id'],status=result['status'],resolved=result['resolved_sample_count'],
                             exit_counts=sorted(set(r['exit_count'] for r in result['samples'])))),flush=True)
    report=dict(schema='vv-toolbox.aca-mesh-rim-diagnostic/1',case_revision=prior['case_revision'],
                atlas_archive_sha256=atlas.metadata['sha256'],rows=rows,app_applied=False,accepted_for_generation=False)
    (root/'docs/evidence/aca-mesh-rims.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')


if __name__=='__main__':main()
