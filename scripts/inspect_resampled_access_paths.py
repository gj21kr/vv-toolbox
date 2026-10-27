"""Check every original access graph edge against the protected replacement union."""
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh

from vv_toolbox.case_io import load_case
from vv_toolbox.centerline_containment import inspect_centerline_containment


def main():
    root=Path('docs/evidence');read=lambda n:json.loads((root/n).read_text())
    surface=read('resampled-access-protected.json');parent=read('resampled-access-union.json')
    record=read('access-sample-graph.json');graph,revision=load_case(record['graph_file'])
    path=Path(surface['artifact'])
    if (hashlib.sha256(path.read_bytes()).hexdigest()!=surface['output_sha256']
            or surface['parent_sha256']!=parent['output_sha256']
            or parent['parent_sha256']!=record['surface_sha256']
            or revision!=record['derived_revision']):
        raise ValueError('Surface/graph ancestry mismatch')
    with np.load(path,allow_pickle=False) as data:
        mesh=trimesh.Trimesh(data['vertices'],data['faces'],process=False)
    report=dict(status='RUNNING',surface_sha256=surface['output_sha256'],graph_revision=revision,
        expected_edges=len(graph['edges']),rows=[],live_scene_changed=False,
        scope='Every original graph edge; radius and edited collar paths excluded')
    output=root/'resampled-access-paths.json'
    for edge in graph['edges']:
        result=inspect_centerline_containment(mesh,edge['centerline_mm'])
        report['rows'].append(dict(edge_id=edge['id'],**result))
        tmp=output.with_suffix('.json.tmp');tmp.write_text(json.dumps(report,indent=2)+'\n');tmp.replace(output)
    states=[r['status'] for r in report['rows']]
    report['status']='FAIL' if 'FAIL' in states else 'UNKNOWN' if 'UNKNOWN' in states else 'PASS'
    output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(status=report['status'],edges=len(states))),flush=True)


if __name__=='__main__':
    main()
