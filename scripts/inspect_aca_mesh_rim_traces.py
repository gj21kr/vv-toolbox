"""Trace complete projected polygon sides on original ACA triangle surfaces."""
import json
from pathlib import Path
from vv_toolbox.atlas import load_atlas
from vv_toolbox.mesh_rim_trace import trace_mesh_rim


def main():
    root=Path(__file__).resolve().parents[1]
    prior=json.loads((root/'docs/evidence/aca-mesh-rims.json').read_text())
    atlas=load_atlas()
    if atlas.metadata['sha256']!=prior['atlas_archive_sha256']:raise ValueError('Atlas changed')
    parts={p['id']:p for p in atlas.meshes};rows=[]
    for row in prior['rows']:
        p=parts[row['parent_part_id']];neck=row['specification']['neck']
        trace=trace_mesh_rim(p['vertices'],p['faces'],neck['curve_mm'],neck['normal'])
        rows.append(dict(junction_id=row['junction_id'],parent_part_id=p['id'],trace=trace))
        print(json.dumps(dict(junction=row['junction_id'],status=trace['status'],segments=trace['segment_count'],
            unresolved_sides=[s['side_index'] for s in trace['sides'] if s['status']!='PASS'])),flush=True)
    report=dict(schema='vv-toolbox.aca-mesh-rim-traces/1',case_revision=prior['case_revision'],
                atlas_archive_sha256=atlas.metadata['sha256'],rows=rows,app_applied=False,accepted_for_generation=False)
    (root/'docs/evidence/aca-mesh-rim-traces.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')


if __name__=='__main__':main()
