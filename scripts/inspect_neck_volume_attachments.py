"""Sample every cap against its declared source endpoint vessel; do not alter geometry."""
import json
from pathlib import Path

import numpy as np
import trimesh

from vv_toolbox.case_io import load_case
from vv_toolbox.surface_indexing import exact_vertex_index_copy
from vv_toolbox.voxel_output import _inside


def main():
    record=json.loads(Path('docs/evidence/atlas-neck-volume-case.json').read_text())
    case,revision=load_case(record['derived_case_file'])
    parts={p['part_id']:p for p in case['surface_parts']}
    capture=case['inspection']['atlas_scene_capture']['estimated_metadata']
    derivations=case['inspection']['neck_volume_derivation']['parts']
    rows=[]
    for pid,derivation in derivations.items():
        part=parts[pid];vertices=np.asarray(part['vertices_mm']);faces=np.asarray(part['faces'])
        centers=np.asarray(capture[pid]['endpoint_centers'])
        boundaries=derivation['boundaries']
        cap_centers=np.asarray([vertices[b['cap_center_vertex']] for b in boundaries])
        direct=np.linalg.norm(cap_centers-centers,axis=1).sum()
        reverse=np.linalg.norm(cap_centers-centers[::-1],axis=1).sum()
        order=[0,1] if direct<=reverse else [1,0]
        for boundary,end in zip(boundaries,order):
            target=capture[pid]['source_endpoint_ids'][end]
            if target not in parts:
                rows.append(dict(part_id=pid,target=target,status='UNKNOWN',reason='Target surface absent'))
                continue
            source=parts[target]
            mesh,_=exact_vertex_index_copy(trimesh.Trimesh(source['vertices_mm'],source['faces'],process=False))
            if not mesh.is_volume:
                rows.append(dict(part_id=pid,target=target,status='UNKNOWN',reason='Target not a closed volume'))
                continue
            cap=faces[np.any(faces==boundary['cap_center_vertex'],axis=1)]
            triangles=vertices[cap]
            probes=np.unique(np.concatenate([triangles.reshape(-1,3),
                triangles.mean(1),((triangles+np.roll(triangles,1,axis=1))/2).reshape(-1,3)]),axis=0)
            inside=_inside(probes,np.asarray(mesh.vertices)[mesh.faces],1e-8)
            # A separate interior witness checks volumetric overlap, not just cap contact.
            center=vertices[boundary['cap_center_vertex']]
            other=cap_centers[1-boundaries.index(boundary)]
            direction=(other-center)/np.linalg.norm(other-center)
            witness=center+.25*direction
            in_source=bool(_inside(witness[None,:],np.asarray(mesh.vertices)[mesh.faces],1e-8)[0])
            in_connector=bool(_inside(witness[None,:],vertices[faces],1e-8)[0])
            rows.append(dict(part_id=pid,target=target,
                cap_center_to_declared_endpoint_mm=float(np.linalg.norm(center-centers[end])),
                sampled_cap_coverage='PASS' if inside.all() else 'FAIL',
                cap_samples=len(probes),inside_source_samples=int(inside.sum()),
                outside_source_samples=int((~inside).sum()),
                witness_offset_mm=.25,interior_overlap_witness=in_source and in_connector,
                outside_example_mm=probes[np.flatnonzero(~inside)[:3]].tolist()))
    result=dict(status='INSPECTED',case_revision=revision,rows=rows,
                scope='Cap vertices, edge midpoints and face centers plus one interior witness per end',
                cap_coverage_pass=sum(r.get('sampled_cap_coverage')=='PASS' for r in rows),
                interior_overlap_pass=sum(r.get('interior_overlap_witness',False) for r in rows),
                continuous_overlap_volume='NOT RUN',anatomical_connection='NOT RUN',
                geometry_changed=False)
    Path('docs/evidence/neck-volume-attachments.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({**result,'rows':[{k:v for k,v in r.items() if k!='outside_example_mm'} for r in rows]}))


if __name__=='__main__':
    main()
