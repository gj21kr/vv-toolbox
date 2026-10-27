"""Validate source-face partitions before stitching a replacement opening."""
import json
from pathlib import Path
import numpy as np
from vv_toolbox.atlas import load_atlas
from vv_toolbox.triangle_neck_cut import partition_triangle
from vv_toolbox.mesh_neck_opening import build_neck_opening


def area(v):
    return sum(np.linalg.norm(np.cross(v[i]-v[0],v[i+1]-v[0]))/2 for i in range(1,len(v)-1))


def main():
    root=Path(__file__).resolve().parents[1]
    prior=json.loads((root/'docs/evidence/aca-mesh-rims.json').read_text())
    atlas=load_atlas()
    if atlas.metadata['sha256']!=prior['atlas_archive_sha256']:raise ValueError('Source changed')
    parts={p['id']:p for p in atlas.meshes};rows=[]
    for row in prior['rows']:
        part=parts[row['parent_part_id']];neck=row['specification']['neck']
        _,_,opening=build_neck_opening(part['vertices'],part['faces'],neck['curve_mm'],neck['normal'])
        center=np.asarray(neck['center_mm']);basis=np.column_stack([neck['width_axis'],neck['depth_axis']])
        polygon=(np.asarray(neck['curve_mm'])-center)@basis
        source=np.asarray(part['vertices'],dtype=float)[np.asarray(part['faces'])];checks=[]
        for index in opening['removed_source_face_ids']:
            tri=source[index];inside,outside=partition_triangle((tri-center)@basis,polygon)
            pieces=([inside] if len(inside) else [])+outside
            original=area(tri);cut=sum(area(b@tri) for b in pieces)
            normal=np.cross(tri[1]-tri[0],tri[2]-tri[0]);normal/=np.linalg.norm(normal)
            deviation=max(float(np.max(np.abs((b@tri-tri[0])@normal))) for b in pieces)
            if abs(original-cut)>1e-9 or deviation>1e-9:raise ValueError('Partition changed source surface')
            checks.append(dict(source_face_id=index,source_area_mm2=original,
                area_residual_mm2=abs(original-cut),plane_deviation_mm=deviation,
                outside_piece_count=len(outside)))
        rows.append(dict(part_id=part['id'],status='PASS',faces=checks))
        print(part['id'],len(checks),'PASS',flush=True)
    report=dict(schema='vv-toolbox.aca-triangle-cuts/1',case_revision=prior['case_revision'],
        atlas_archive_sha256=atlas.metadata['sha256'],rows=rows,
        scope='Individual source-face partitions only',stitched_opening='NOT RUN',
        closed_union='NOT RUN',accepted_for_generation=False)
    (root/'docs/evidence/aca-triangle-cuts.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')


if __name__=='__main__':main()
