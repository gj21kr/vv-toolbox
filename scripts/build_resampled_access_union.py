"""Separate full access union with only the estimated right neck replaced."""
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh

from vv_toolbox.case_io import load_case
from vv_toolbox.estimated_tube_volume import cap_estimated_neck
from vv_toolbox.solid_union import build_solid_union
from vv_toolbox.union_lineage import verify_face_lineage


def main():
    root=Path('docs/evidence')
    read=lambda name:json.loads((root/name).read_text())
    parent=read('femoral-anterior-union.json');replacement=read('resampled-right-neck-volume.json')
    case,revision=load_case(read('atlas-neck-volume-case.json')['derived_case_file'])
    if revision!=parent['source_case_revision'] or revision!=replacement['source_case_revision']:
        raise ValueError('Source case mismatch')
    path=Path(replacement['artifact'])
    if hashlib.sha256(path.read_bytes()).hexdigest()!=replacement['artifact_sha256']:
        raise ValueError('Replacement identity mismatch')
    parts={p['part_id']:p for p in case['surface_parts']}
    report=dict(status='RUNNING',source_case_revision=revision,parent_sha256=parent['output_sha256'],
        replacement_sha256=replacement['artifact_sha256'],replaced_source='estimated_right_carotid_neck',
        prepared_sources=[],live_scene_changed=False,centerline_containment='NOT RUN',whole_context='NOT RUN')
    output=root/'resampled-access-union.json'

    def save():
        tmp=output.with_suffix('.json.tmp');tmp.write_text(json.dumps(report,indent=2)+'\n');tmp.replace(output)

    save();sources={}
    for name in parent['face_lineage']['source_names']:
        if name=='estimated_right_carotid_neck':
            with np.load(path,allow_pickle=False) as data:
                mesh=trimesh.Trimesh(data['vertices'],data['faces'],process=False)
        elif name.startswith('estimated_'):
            original=Path('exports/neck-contour-candidates-corners')/(name+'.npz')
            with np.load(original,allow_pickle=False) as data:
                closed=cap_estimated_neck(dict(vertices=data['vertices'],faces=data['faces'],
                    metadata=dict(kind='estimated-neck-connector',original_atlas_geometry=False)),
                    max_planarity_mm=.001,cap_method='planar-earcut')
            mesh=trimesh.Trimesh(closed['vertices'],closed['faces'],process=False)
        else:
            part=parts[name];mesh=trimesh.Trimesh(part['vertices_mm'],part['faces'],process=False)
        sources[name]=mesh;report['prepared_sources'].append(name);save()
    print(json.dumps(dict(prepared=len(sources))),flush=True)
    try:
        merged,audit=build_solid_union(sources,precision='float64')
        lineage=audit['face_lineage'];check=verify_face_lineage(merged,sources,lineage)
        if check['status']!='PASS':raise ValueError('Replacement input lineage not verified')
        folder=Path('exports/resampled-access-union');folder.mkdir(parents=True,exist_ok=True)
        artifact=folder/'candidate.npz';np.savez_compressed(artifact,vertices=merged.vertices,faces=merged.faces)
        report.update(status='CANDIDATE',union=audit,face_lineage=lineage,lineage_check=check,
            artifact=str(artifact),output_sha256=hashlib.sha256(artifact.read_bytes()).hexdigest(),
            lineage_scope='Exact inputs for this union; right neck is the separately resampled estimate')
    except ValueError as error:
        report.update(status='FAIL',reason=str(error))
    save();print(json.dumps(dict(status=report['status'],reason=report.get('reason'))),flush=True)


if __name__=='__main__':
    main()
