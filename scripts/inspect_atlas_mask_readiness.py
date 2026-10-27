"""Preflight every captured surface against the existing mask topology contract."""
import json
import math
from pathlib import Path

import numpy as np
import trimesh

from vv_toolbox.case_io import load_case
from vv_toolbox.surface_indexing import exact_vertex_index_copy


def ready(mesh):
    return bool(mesh.is_watertight and mesh.is_winding_consistent and mesh.is_volume
                and np.all(mesh.area_faces > 0))


def main():
    case, revision = load_case('exports/atlas-case-estimates-ui/case.snapshot.json')
    rows, low, high, cost = [], np.full(3,np.inf), np.full(3,-np.inf), 0
    for p in case['surface_parts']:
        v, f = np.asarray(p['vertices_mm']), np.asarray(p['faces'])
        mesh = trimesh.Trimesh(v,f,process=False)
        normalized, report = exact_vertex_index_copy(mesh)
        rows.append(dict(part_id=p['part_id'],provenance=p['provenance'],
                         raw_topology_ready=ready(mesh),exact_index_topology_ready=ready(normalized),
                         watertight=bool(normalized.is_watertight),
                         winding_consistent=bool(normalized.is_winding_consistent),
                         positive_volume=bool(normalized.is_volume),
                         zero_area_faces=report['zero_area_faces'],
                         triangle_coordinates_preserved=report['triangle_coordinate_bytes_preserved']))
        low=np.minimum(low,v.min(0)); high=np.maximum(high,v.max(0))
        cost += f.size*512+v.size*32
    # Fixed engineering probe, not a clinically recommended resolution.
    spacing=1.
    shape=np.ceil((high-low)/spacing).astype(np.int64)+3
    nvox=math.prod(int(n) for n in shape)
    estimated=nvox*(26+len(rows))+cost+8*1024**2
    result=dict(status='INSPECTED',case_revision=revision,surface_count=len(rows),
                raw_ready=sum(r['raw_topology_ready'] for r in rows),
                exact_index_ready=sum(r['exact_index_topology_ready'] for r in rows),
                remaining_parts=[r['part_id'] for r in rows if not r['exact_index_topology_ready']],
                probe_spacing_mm=spacing,probe_shape_xyz=shape.tolist(),
                existing_dense_memory_bound_bytes=estimated,
                default_budget_bytes=256*1024**2,
                full_masks='NOT RUN',self_contact='NOT RUN',rows=rows)
    Path('docs/evidence/atlas-mask-readiness.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='rows'}))


if __name__=='__main__':
    main()
