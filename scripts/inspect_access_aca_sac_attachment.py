"""Fixed engineering attachment probes on existing synthetic ACA junctions."""
import hashlib
import json
from pathlib import Path
import numpy as np
from vv_toolbox.case_io import load_case
from vv_toolbox.bifurcation_saccular import bifurcation_saccular_spec
from vv_toolbox.bifurcation_attachment import inspect_bifurcation_attachment
from vv_toolbox.bifurcation_clearance import inspect_bifurcation_clearance


def main():
    root=Path(__file__).resolve().parents[1]
    source=root/'exports/candidate-case-download/case.snapshot.json'
    before=source.read_bytes();case,revision=load_case(source)
    results=[]
    # Fixed targets, direction and dimensions, never optimized against outcomes.
    for junction in ('sample:FJ1654:e0:77','sample:FJ1654M:e0:91'):
        incident=[e for e in case['edges'] if junction in (e['start'],e['end'])]
        row=dict(junction_id=junction,surface_published=False)
        try:
            distances={e['id']:float(np.linalg.norm(np.diff(np.asarray(e['centerline_mm']),axis=0),axis=1).sum()/2)
                       for e in incident}
            radius=max(e['radii_mm'][0 if e['start']==junction else -1] for e in incident)
            normal=np.array([0.,-1.,0.])
            center=np.asarray(case['nodes'][junction]['position_mm'])+normal*radius
            spec=bifurcation_saccular_spec(case,lesion_id='engineering-'+junction,junction_id=junction,
                region='aca',outlet_distances_mm=distances,neck_center_mm=center.tolist(),
                outward_normal=normal.tolist(),width_direction=[1,0,0],neck_width_mm=2.,neck_depth_mm=1.,
                height_perpendicular_mm=5.,dome_width_mm=4.,dome_depth_mm=3.,blending_extent_mm=.5)
            attachment=inspect_bifurcation_attachment(case,spec,burial_margin_mm=.15)
            clearance=inspect_bifurcation_clearance(case,spec,margin_mm=.3)
            row.update(specification=spec,attachment=attachment,partial_context_clearance=clearance,
                       status=attachment['status'])
        except ValueError as error:row.update(status='FAIL',reason=str(error))
        results.append(row)
    if source.read_bytes()!=before:raise RuntimeError('Source snapshot changed')
    report=dict(schema='vv-toolbox.access-aca-sac-attachment/1',case_revision=revision,
        input_sha256=hashlib.sha256(before).hexdigest(),input_unchanged=True,edge_count=len(case['edges']),
        design='Fixed world anterior normal; maximum incident junction radius offset; half-length outlets; 2x1 neck, 4x3x5 dome, 0.5 blend mm',
        full_atlas_context=False,accepted_for_generation=False,geometry_generation='NOT RUN',
        anatomical_placement='UNKNOWN',attempts=results)
    (root/'docs/evidence/access-aca-sac-attachment.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    for row in results:
        print(json.dumps(dict(junction=row['junction_id'],status=row['status'],
            invaded_rim_count=len(row.get('attachment',{}).get('rim',{}).get('interior_indices',[])),
            unburied_count=len(row.get('attachment',{}).get('buried_rim',{}).get('insufficient_burial_indices',[])),
            partial_context_status=row.get('partial_context_clearance',{}).get('status'),
            reason=row.get('reason'))))


if __name__=='__main__':main()
