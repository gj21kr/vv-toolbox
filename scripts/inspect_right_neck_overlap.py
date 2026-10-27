"""Diagnose the fixed failed witness without changing its acceptance criterion."""
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh

from vv_toolbox.case_io import load_case
from vv_toolbox.estimated_tube_volume import cap_estimated_neck
from vv_toolbox.surface_indexing import exact_vertex_index_copy
from vv_toolbox.voxel_output import _inside


def main():
    pid='estimated_right_carotid_neck'
    evidence=json.loads(Path('docs/evidence/contour-bridge-attachments-corners.json').read_text())
    record=json.loads(Path('docs/evidence/atlas-neck-volume-case.json').read_text())
    case,revision=load_case(record['derived_case_file'])
    source=next(p for p in case['surface_parts'] if p['part_id']=='FJ3564')
    mesh,_=exact_vertex_index_copy(trimesh.Trimesh(source['vertices_mm'],source['faces'],process=False))
    sections=json.loads(Path('docs/evidence/neck-source-contours.json').read_text())
    profile=next(r['profile'] for r in sections['rows'] if r['part_id']==pid
                 and r['end']==0 and r['plane_definition']=='endpoint_tangent_normal')
    path=Path('exports/neck-contour-candidates-corners')/(pid+'.npz')
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    if digest!=evidence['candidate_file_sha256'][pid]:
        raise ValueError('Candidate identity mismatch')
    with np.load(path,allow_pickle=False) as data:
        closed=cap_estimated_neck(dict(vertices=data['vertices'],faces=data['faces'],
            metadata=dict(kind='estimated-neck-connector',original_atlas_geometry=False)),
            max_planarity_mm=.001,cap_method='planar-earcut')
    bridge=trimesh.Trimesh(closed['vertices'],closed['faces'],process=False)
    offsets=np.array([0.,.01,.05,.1,.25,.5,1.])
    points=np.asarray(profile['origin_mm'])+offsets[:,None]*np.asarray(profile['normal'])
    source_inside=_inside(points,mesh.triangles,1e-8)
    bridge_inside=_inside(points,bridge.triangles,1e-8)
    source_distance=trimesh.proximity.closest_point(mesh,points)[1]
    bridge_distance=trimesh.proximity.closest_point(bridge,points)[1]
    rows=[dict(offset_mm=float(offset),point_mm=point.tolist(),
               inside_source=bool(si),inside_bridge=bool(bi),
               source_boundary_distance_mm=float(sd),bridge_boundary_distance_mm=float(bd))
          for offset,point,si,bi,sd,bd in zip(offsets,points,source_inside,bridge_inside,
                                           source_distance,bridge_distance)]
    result=dict(case_revision=revision,candidate_sha256=digest,rows=rows,
                fixed_025mm_witness_unchanged=True,
                scope='Diagnostic line samples only, not full overlap volume or union',
                live_scene_changed=False)
    Path('docs/evidence/right-neck-overlap-diagnostic.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__':
    main()
