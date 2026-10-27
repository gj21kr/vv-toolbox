"""Build and check a derived full Atlas case, preserving the captured parent."""
import json
from pathlib import Path

import numpy as np
import trimesh

from vv_toolbox.case_io import load_case,save_case,case_digest
from vv_toolbox.neck_volume_case import derive_neck_volumes
from vv_toolbox.surface_indexing import exact_vertex_index_copy


def main():
    parent,parent_revision=load_case('exports/atlas-case-estimates-ui/case.snapshot.json')
    derived=derive_neck_volumes(parent,max_planarity_mm=.001)
    revision=case_digest(derived)
    folder=Path('exports/atlas-neck-volume-case');folder.mkdir(parents=True,exist_ok=True)
    path=folder/(revision+'.snapshot.json')
    if path.exists():
        if load_case(path)[1]!=revision:
            raise ValueError('Existing derived case mismatch')
    else:
        save_case(path,derived)
    reloaded,_=load_case(path)
    original={p['part_id']:p for p in parent['surface_parts']}
    ready=0;source_preserved=0
    for p in reloaded['surface_parts']:
        mesh,_=exact_vertex_index_copy(trimesh.Trimesh(p['vertices_mm'],p['faces'],process=False))
        if not (mesh.is_volume and mesh.is_winding_consistent and np.all(mesh.area_faces>0)):
            raise ValueError('Derived part fails topology: '+p['part_id'])
        ready+=1
        if p['provenance']=='source':
            if p!=original[p['part_id']]:
                raise ValueError('Original registered source part changed')
            source_preserved+=1
    if derived['edges']!=parent['edges'] or derived['nodes']!=parent['nodes']:
        raise ValueError('Derivation changed graph')
    result=dict(status='PASS',parent_revision=parent_revision,derived_revision=revision,
                topology_ready_parts=ready,original_source_parts_preserved=source_preserved,
                graph_unchanged=True,derived_case_file=path.as_posix(),
                source_lumen_union='NOT RUN',all_surface_self_contact='NOT RUN',
                whole_case_masks='NOT RUN',active_scene_changed=False)
    Path('docs/evidence/atlas-neck-volume-case.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__':
    main()
