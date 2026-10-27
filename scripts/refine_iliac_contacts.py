"""Locate all flagged capsule pairs; negative sphere witnesses are model overlap."""
import hashlib
import json
from pathlib import Path
import numpy as np
from vv_toolbox.case_io import load_case
from vv_toolbox.geometry_quality import segment_closest_points

ROOT = Path(__file__).resolve().parents[1]


def main():
    source = ROOT/'docs/evidence/internal-iliac-surface-inspection.json'
    raw = source.read_bytes()
    audit = json.loads(raw)
    path = ROOT/'exports/synthetic-common-iliac-trunk/case.snapshot.json'
    snapshot = path.read_bytes()
    case, revision = load_case(path)
    if revision != audit['case_revision']:
        raise ValueError('stale contact audit')
    by_id = {e['id']:e for e in case['edges']}
    focus = set(audit['selected_edge_ids'])
    rows = []
    for contact in audit['surrounding_screen']['potential_contacts']:
        ids = contact['edges']
        edges = [by_id[e] for e in ids]
        p, q = [np.asarray(e['centerline_mm']) for e in edges]
        rp, rq = [np.asarray(e['radii_mm']) for e in edges]
        minimum_bound, best, count = float('inf'), None, 0
        for i in range(len(p)-1):
            for j in range(len(q)-1):
                distance, s, t, a, b = segment_closest_points(p[i],p[i+1],q[j],q[j+1])
                count += 1
                lower = distance-max(rp[i:i+2])-max(rq[j:j+2])
                minimum_bound = min(minimum_bound, lower)
                radii = [(1-s)*rp[i]+s*rp[i+1], (1-t)*rq[j]+t*rq[j+1]]
                gap = float(distance-sum(radii))
                if best is None or gap < best['sphere_gap_mm']:
                    best = dict(intervals=[i,j], fractions=[s,t], centers_mm=[a.tolist(),b.tolist()],
                                radii_mm=radii, center_distance_mm=distance, sphere_gap_mm=gap)
        rows.append(dict(edges=ids, scope='within_selected' if set(ids)<=focus else 'surrounding',
            anatomy=[e['anatomy'] for e in edges], interval_pairs_checked=count,
            minimum_capsule_bound_mm=float(minimum_bound), witness=best,
            status=('SWEPT_SPHERE_OVERLAP' if best['sphere_gap_mm'] < -1e-8 else
                    'SEPARATED_CAPSULES' if minimum_bound > 0 else 'UNKNOWN'),
            limitation='Negative witness proves overlap of interpolated-radius spheres only. Witness search is not the global minimum of variable-radius clearance. No source mesh or anatomy claim.'))
        print(json.dumps(dict(edges=ids, scope=rows[-1]['scope'], status=rows[-1]['status'],
                              sphere_gap_mm=best['sphere_gap_mm'])), flush=True)
    if source.read_bytes()!=raw or path.read_bytes()!=snapshot:
        raise ValueError('input changed during inspection')
    report = dict(schema='vv-toolbox.iliac-contact-refinement/1',case_revision=revision,
        input_report_sha256=hashlib.sha256(raw).hexdigest(), input_unchanged=True,
        pair_count=len(rows), pairs=rows, final_mesh_collision='NOT RUN',
        anatomical_connectivity='UNKNOWN', default_app_applied=False)
    (ROOT/'docs/evidence/iliac-contact-refinement.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':
    main()
