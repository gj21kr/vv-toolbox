"""Measure both source-region boundary loops without declaring either the neck."""
import hashlib
import json
from pathlib import Path
import numpy as np
from vv_toolbox.patch_boundary import patch_boundary_loops,vertices_to_closed_curve_distance

ROOT=Path(__file__).resolve().parents[1]


def main():
    source=json.loads((ROOT/'docs/evidence/mca-surface-origin.json').read_text())
    spec=json.loads((ROOT/'docs/evidence/regularized-mca-sac.json').read_text())['specification']
    path=ROOT/'exports/mca-surface-origin/surface.npz'
    raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=source['artifact_sha256']:
        raise ValueError('surface hash mismatch')
    with np.load(path,allow_pickle=False) as data:
        vertices,faces=data['vertices_mm'],data['faces']
        metadata=json.loads(str(data['metadata'].item()))
    if spec['case_revision']!=metadata['case_revision']:
        raise ValueError('case mismatch')
    labels=np.array(metadata['surface_origin']['face_labels'])
    design=np.array(metadata['attachment']['curve_mm'])
    neck=spec['neck'];center=np.array(neck['center_mm'])
    basis=np.column_stack([neck[k] for k in ('width_axis','depth_axis','normal')])
    rows=[]
    for label,name in [(0,'parent_side'),(1,'sac_side')]:
        loops=patch_boundary_loops(faces,np.flatnonzero(labels==label))
        if len(loops)!=1:
            raise ValueError('expected exactly one boundary per source region')
        ids=loops[0];curve=vertices[ids];local=(curve-center)@basis
        rows.append(dict(side=name,vertex_indices=ids,points_mm=curve.tolist(),
            projected_width_depth_mm=np.ptp(local[:,:2],axis=0).tolist(),
            perimeter_mm=float(np.linalg.norm(np.roll(curve,-1,axis=0)-curve,axis=1).sum()),
            boundary_vertices_to_design_max_mm=float(vertices_to_closed_curve_distance(curve,design).max()),
            design_vertices_to_boundary_max_mm=float(vertices_to_closed_curve_distance(design,curve).max())))
    result=dict(case_revision=source['case_revision'],artifact_sha256=source['artifact_sha256'],
        boundaries=rows,requested_width_depth_mm=[spec['parameters']['neck_width_mm'],
            spec['parameters']['neck_depth_mm']],neck_dimension_approval='UNKNOWN',
        input_unchanged=raw==path.read_bytes(),app_applied=False,
        limitation='Both sampled-source region boundaries retained. Vertex-to-segment distances are not continuous Hausdorff bounds.')
    (ROOT/'docs/evidence/mca-origin-boundaries.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps([{k:v for k,v in row.items() if k not in ('vertex_indices','points_mm')} for row in rows]))


if __name__=='__main__':
    main()
