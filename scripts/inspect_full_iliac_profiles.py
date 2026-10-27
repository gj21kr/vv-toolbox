"""Inspect every sample of two fixed source paths; never omit failed sections."""
import hashlib
import argparse
import json
from pathlib import Path
import numpy as np
import trimesh
from matplotlib.path import Path as PolygonPath
from vv_toolbox.atlas import load_atlas
from vv_toolbox.case_io import load_case
from inspect_iliac_normal_sections import section_metrics

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plane',choices=['path-normal','axial'],default='path-normal')
    args=parser.parse_args()
    path=ROOT/'exports/synthetic-common-iliac-trunk/case.snapshot.json'
    raw=path.read_bytes();case,revision=load_case(path)
    atlas=load_atlas()
    if atlas.metadata['sha256']!=next(s['sha256'] for s in case['sources'] if s['id']=='bp3d'):
        raise ValueError('source mismatch')
    rows=[]
    for ident,source in [('R-EIA-retained','FJ3567'),('FJ3617:e0','FJ3617')]:
        edge=next(e for e in case['edges'] if e['id']==ident)
        part=next(p for p in atlas.meshes if p['id']==source)
        mesh=trimesh.Trimesh(part['vertices'],part['faces'],process=False)
        points=np.array(edge['centerline_mm']);arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(points,axis=0),axis=1))]
        samples=[]
        for index,point in enumerate(points):
            normal=np.array([np.interp(min(arc[-1],arc[index]+2),arc,points[:,k])-
                             np.interp(max(0,arc[index]-2),arc,points[:,k]) for k in range(3)])
            if args.plane=='axial':normal=np.array([0.,0.,1.])
            record=dict(index=index,position_mm=point.tolist(),arc_mm=float(arc[index]),
                        stored_radius_mm=edge['radii_mm'][index],frozen_endpoint=index in (0,1,len(points)-2,len(points)-1))
            if np.linalg.norm(normal)<1e-10:
                samples.append(dict(record,status='UNRESOLVED',reason='degenerate path chord'));continue
            normal/=np.linalg.norm(normal)
            u=np.cross(normal,np.eye(3)[int(np.argmin(abs(normal)))]);u/=np.linalg.norm(u)
            v=np.cross(normal,u);basis=np.array([u,v])
            section=mesh.section(plane_origin=point,plane_normal=normal)
            contours=[] if section is None else section.discrete
            record.update(normal=normal.tolist(),contour_count=len(contours))
            if len(contours)!=1:
                samples.append(dict(record,status='UNRESOLVED',reason='nonunique section'));continue
            xy=(contours[0]-point)@basis.T
            try:metrics=section_metrics(xy)
            except ValueError as error:
                samples.append(dict(record,status='UNRESOLVED',reason=str(error)));continue
            samples.append(dict(record,status='MEASURED',metrics=metrics,
                original_point_inside=bool(PolygonPath(xy).contains_point([0,0])),
                centroid_mm=(point+np.array(metrics['centroid_uv_mm'])@basis).tolist()))
        rows.append(dict(edge_id=ident,source_id=source,sample_count=len(points),samples=samples,
            source_mesh_sha256=hashlib.sha256(np.asarray(part['vertices']).tobytes()+np.asarray(part['faces']).tobytes()).hexdigest(),
            unresolved_indices=[r['index'] for r in samples if r['status']!='MEASURED'],
            measured_outside_indices=[r['index'] for r in samples if r['status']=='MEASURED' and not r['original_point_inside']]))
        print(json.dumps({k:v for k,v in rows[-1].items() if k not in ('samples','source_mesh_sha256')}),flush=True)
    if path.read_bytes()!=raw:raise ValueError('input changed')
    report=dict(schema='vv-toolbox.full-source-profile-inspection/1',case_revision=revision,
        source_archive_sha256=atlas.metadata['sha256'],plane_method=args.plane,half_chord_mm=2.,paths=rows,input_unchanged=True,
        candidate_created=False,anatomical_acceptance='UNKNOWN',
        limitation='Measurements at every stored station, not continuous interior containment; ambiguous sections are retained as unresolved.')
    suffix='' if args.plane=='path-normal' else '-axial'
    (ROOT/f'docs/evidence/full-iliac-source-profiles{suffix}.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
