"""Synthetic bilateral ICA/ACA/ACom/proximal-MCA union; no boundary approval."""
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh

from vv_toolbox.case_io import load_case
from vv_toolbox.atlas import load_atlas
from vv_toolbox.atlas_topology import reference_junctions
from vv_toolbox.estimated_tube_volume import cap_estimated_neck
from vv_toolbox.solid_union import build_solid_union
from vv_toolbox.union_lineage import compose_face_lineage, verify_face_lineage


def read(name):
    return json.loads((Path('docs/evidence')/name).read_text())


def load_mesh(path, expected):
    path=Path(path)
    if hashlib.sha256(path.read_bytes()).hexdigest()!=expected:
        raise ValueError('Parent candidate geometry changed')
    with np.load(path,allow_pickle=False) as data:
        return trimesh.Trimesh(data['vertices'],data['faces'],process=False)


def main():
    case,revision=load_case(read('atlas-neck-volume-case.json')['derived_case_file'])
    parts={p['part_id']:p for p in case['surface_parts']}
    left=read('left-carotid-aca-acom-union.json')
    original=read('carotid-solid-union-diagnostic-float64-lineage.json')
    checks=read('carotid-union-lineage.json')
    if any(report['source_case_revision']!=revision for report in (left,original,checks)):
        raise ValueError('Case revisions differ')
    right=next(r for r in original['rows'] if r['part_id']=='estimated_right_carotid_neck')
    right_check=next(r for r in checks['rows'] if r['part_id']==right['part_id'])
    if (left['status']!='CANDIDATE' or left['lineage_check']['status']!='PASS'
            or right['status']!='CANDIDATE' or right_check['status']!='PASS'):
        raise ValueError('Validated parent candidates required')
    inputs={
        'left_parent':load_mesh('exports/carotid-aca-acom-junction/left.npz',left['output_sha256']),
        'right_parent':load_mesh('exports/carotid-solid-union-diagnostic-float64-lineage/estimated_right_carotid_neck.npz',
                                 right_check['union_sha256'])}
    leaves={}
    # Registered ICA terminal bifurcations and the ACom communication only.
    added=('FJ1654','FJ1692','FJ1692M')
    for pid in added:
        part=parts[pid]
        inputs[pid]=trimesh.Trimesh(part['vertices_mm'],part['faces'],process=False)
        leaves[pid]=inputs[pid]
    expected={}
    for row in original['rows']:
        expected.update(row['input_surfaces'])
    expected.update(read('left-carotid-aca-union.json')['union']['input_surfaces'])
    expected.update(left['union']['input_surfaces'])
    nested={'left_parent':left['face_lineage'],'right_parent':right['face_lineage']}
    relations={r['id']:r for r in reference_junctions(load_atlas().metadata['parts'])}
    required={'left_ica_terminal':{'FJ1682M','FJ1654M','FJ1692M'},
              'right_ica_terminal':{'FJ1682','FJ1654','FJ1692'},
              'acom':{'FJ1655','FJ1654','FJ1654M'}}
    for name,ids in required.items():
        mapped={pid for member in relations[name]['members'] for pid in member['part_ids']}
        if not ids<=mapped:
            raise ValueError('Reference relation identity mismatch')
    report=dict(source_case_revision=revision,parent_hashes=dict(
        left=left['output_sha256'],right=right_check['union_sha256']),
        added_sources=list(added),reference_relations=[dict(
            id=name,source_url=relations[name]['source_url'],specimen_status=relations[name]['specimen_status'])
            for name in required],
        specimen_connections='UNKNOWN',anatomical_segment_boundaries='UNKNOWN',
        whole_context='NOT RUN',centerline_containment='NOT RUN',live_scene_changed=False)
    try:
        merged,audit=build_solid_union(inputs)
        flat=compose_face_lineage(audit['face_lineage'],nested)
        for pid in flat['source_names']:
            if pid in leaves:
                continue
            if pid.startswith('estimated_'):
                with np.load(Path('exports/neck-contour-candidates-corners')/(pid+'.npz'),allow_pickle=False) as data:
                    closed=cap_estimated_neck(dict(vertices=data['vertices'],faces=data['faces'],
                        metadata=dict(kind='estimated-neck-connector',original_atlas_geometry=False)),
                        max_planarity_mm=.001,cap_method='planar-earcut')
                source=trimesh.Trimesh(closed['vertices'],closed['faces'],process=False)
            else:
                p=parts[pid];source=trimesh.Trimesh(p['vertices_mm'],p['faces'],process=False)
            digest=hashlib.sha256(np.asarray(source.vertices,dtype='<f8').tobytes()+
                                  np.asarray(source.faces,dtype='<i8').tobytes()).hexdigest()
            if digest!=expected[pid]['geometry_sha256']:
                raise ValueError('Parent original source hash mismatch')
            leaves[pid]=source
        check=verify_face_lineage(merged,leaves,flat)
        if check['status']!='PASS':
            raise ValueError('Original source face verification failed')
        folder=Path('exports/anterior-core-union');folder.mkdir(parents=True,exist_ok=True)
        path=folder/'candidate.npz'
        np.savez_compressed(path,vertices=merged.vertices,faces=merged.faces)
        report.update(status='CANDIDATE',union=audit,face_lineage=flat,lineage_check=check,
                      output_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    except ValueError as error:
        report.update(status='FAIL',reason=str(error))
    Path('docs/evidence/anterior-core-union.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('union','face_lineage','lineage_check')}),flush=True)


if __name__=='__main__':
    main()
