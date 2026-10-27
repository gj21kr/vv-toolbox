"""Check the fixed fairing candidate without upgrading anatomical evidence."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh

from vv_toolbox.case_io import load_case
from vv_toolbox.centerline_containment import inspect_centerline_containment
from vv_toolbox.mesh_self_contact import inspect_self_contact


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--mode',choices=['self','paths'],required=True)
    mode=parser.parse_args().mode
    root=Path('docs/evidence')
    record=json.loads((root/'protected-neck-fairing.json').read_text())
    path=Path(record['artifact'])
    source=Path('exports/femoral-anterior-union/candidate.npz')
    if (hashlib.sha256(path.read_bytes()).hexdigest()!=record['artifact_sha256']
            or hashlib.sha256(source.read_bytes()).hexdigest()!=record['source_surface_sha256']):
        raise ValueError('Fairing identity mismatch')
    with np.load(path,allow_pickle=False) as data:
        mesh=trimesh.Trimesh(data['vertices'],data['faces'],process=False)
        free=data['free_vertex_ids'].copy()
    with np.load(source,allow_pickle=False) as data:
        before=trimesh.Trimesh(data['vertices'],data['faces'],process=False)
    if not np.array_equal(before.faces,mesh.faces):
        raise ValueError('Topology changed')
    report=dict(status='RUNNING',artifact_sha256=record['artifact_sha256'],
        source_surface_sha256=record['source_surface_sha256'],mode=mode,
        live_scene_changed=False,anatomical_validation='NOT RUN')
    output=root/f'protected-neck-fairing-{mode}.json'

    def save():
        temporary=output.with_suffix('.json.tmp')
        temporary.write_text(json.dumps(report,indent=2)+'\n')
        temporary.replace(output)

    if mode=='self':
        adjacency=before.face_adjacency
        changed=np.isin(before.faces,free).any(axis=1)
        local=changed[adjacency].any(axis=1)
        report['measured_face_pairs']=int(local.sum())
        for name,surface in [('before',before),('after',mesh)]:
            angles=np.degrees(surface.face_adjacency_angles[local])
            report[name]=dict(mean_degrees=float(angles.mean()),p95_degrees=float(np.percentile(angles,95)),
                              maximum_degrees=float(angles.max()))
        report['smoothness_acceptance']='NOT SET'
        save()
        contact=inspect_self_contact(mesh.vertices,mesh.faces)
        report.update(self_contact=contact,status=contact['status'])
        save()
        print(json.dumps(dict(status=report['status'],before=report['before'],after=report['after'])),flush=True)
    else:
        record_graph=json.loads((root/'access-sample-graph.json').read_text())
        graph,revision=load_case(record_graph['graph_file'])
        if revision!=record_graph['derived_revision'] or record_graph['surface_sha256']!=record['source_surface_sha256']:
            raise ValueError('Graph identity mismatch')
        report.update(graph_revision=revision,rows=[],expected_edges=len(graph['edges']))
        save()
        for edge in graph['edges']:
            result=inspect_centerline_containment(mesh,edge['centerline_mm'])
            report['rows'].append(dict(edge_id=edge['id'],**result))
            save()
        states=[r['status'] for r in report['rows']]
        report['status']='FAIL' if 'FAIL' in states else 'UNKNOWN' if 'UNKNOWN' in states else 'PASS'
        save()
        print(json.dumps(dict(status=report['status'],edges=len(states))),flush=True)


if __name__=='__main__':
    main()
