"""Matched source/edited sections; do not infer radius from vertex movement."""
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh

from vv_toolbox.case_io import load_case
from vv_toolbox.source_sections import extract_source_sections


def read_mesh(path,digest):
    if hashlib.sha256(path.read_bytes()).hexdigest()!=digest:
        raise ValueError('Geometry identity mismatch')
    with np.load(path,allow_pickle=False) as data:
        return trimesh.Trimesh(data['vertices'],data['faces'],process=False)


def main():
    edits=json.loads(Path('docs/evidence/carotid-radius-candidates.json').read_text())
    record=json.loads(Path('docs/evidence/atlas-neck-volume-case.json').read_text())
    case,revision=load_case(record['derived_case_file'])
    if edits['source_case_revision']!=revision:raise ValueError('Source revision mismatch')
    metadata=case['inspection']['atlas_scene_capture']['estimated_metadata']
    rows=[]
    for edit in edits['rows']:
        pid=edit['part_id']
        if edit['status']!='CANDIDATE':raise ValueError('Edited candidate unavailable')
        source=read_mesh(Path('exports/carotid-solid-union-diagnostic-float64-lineage')/(pid+'.npz'),edit['input_sha256'])
        changed=read_mesh(Path('exports/carotid-radius-candidates')/(pid+'.npz'),edit['output_sha256'])
        points=np.asarray(metadata[pid]['centerline'])
        arc=np.r_[0.,np.cumsum(np.linalg.norm(np.diff(points,axis=0),axis=1))]
        before=extract_source_sections(source,points)['profiles']
        after=extract_source_sections(changed,points)['profiles']
        sections=[]
        for a,b in zip(before,after):
            if a['index']!=b['index']:raise ValueError('Section station mismatch')
            index=a['index']
            central=bool(min(arc[index],arc[-1]-arc[index])>=2*edit['transition_mm'])
            row=dict(index=index,arclength_mm=float(arc[index]),central_region=central,
                     before_status=a['status'],after_status=b['status'])
            if a['status']==b['status']=='MEASURED':
                row.update(before_area_mm2=a['area_mm2'],after_area_mm2=b['area_mm2'],
                           equivalent_radius_ratio=b['area_equivalent_radius_mm']/a['area_equivalent_radius_mm'])
            sections.append(row)
        ratios=[s['equivalent_radius_ratio'] for s in sections if s['central_region']
                and 'equivalent_radius_ratio' in s]
        rows.append(dict(part_id=pid,input_sha256=edit['input_sha256'],output_sha256=edit['output_sha256'],
            requested_scale=edit['scale'],sections=sections,
            measured_pairs=sum('equivalent_radius_ratio' in s for s in sections),
            total_pairs=len(sections),central_measured=len(ratios),
            central_ratio_range=[min(ratios),max(ratios)] if ratios else None,
            central_max_absolute_scale_error=max(abs(r-edit['scale']) for r in ratios) if ratios else None))
        print(json.dumps({k:v for k,v in rows[-1].items() if k!='sections'}),flush=True)
    Path('docs/evidence/carotid-radius-sections.json').write_text(json.dumps(dict(
        source_case_revision=revision,rows=rows,
        central_region_definition='At least twice the declared transition length from both polyline ends',
        scope='Matched interior chord-normal sections; area-equivalent radius only',
        acceptance_threshold='NOT SET',continuous_interval_radius_bound='NOT RUN',
        anatomical_validation='NOT RUN',live_scene_changed=False),indent=2)+'\n')


if __name__=='__main__':
    main()
