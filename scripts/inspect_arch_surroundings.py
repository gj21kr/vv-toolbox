"""Compare surrounding-vessel contacts before and after explicit arch synthesis."""
import hashlib
import json
from pathlib import Path

from vv_toolbox.case_io import load_case
from vv_toolbox.geometry_quality import screen_nonincident_clearance

ROOT = Path(__file__).resolve().parents[1]


def main():
    paths = [ROOT/'exports/synthetic-neck-case/case.snapshot.json',
             ROOT/'exports/synthetic-arch-carotid-case/case.snapshot.json']
    raw = [p.read_bytes() for p in paths]
    baseline, baseline_revision = load_case(paths[0])
    candidate, revision = load_case(paths[1])
    local_path = ROOT/'docs/evidence/arch-junction-surface.json'
    local_raw = local_path.read_bytes()
    local = json.loads(local_raw)
    if revision != local['case_revision']:
        raise ValueError('Local junction inspection is stale')
    candidate_focus = local['selected_edge_ids']
    baseline_focus = ['FJ3411:e0','FJ3483:e0','estimated_L_carotid_gap','FJ1682M:e0']
    child_ids = {'synthetic_arch_before_LCCA','synthetic_arch_after_LCCA'}
    bridge_id = 'estimated_arch_to_LCCA'

    def normalized(edge_id):
        return 'FJ3411:e0' if edge_id in child_ids else edge_id

    def inspect(case, focus):
        selected = [e['id'] for e in case['edges'] if e['centerline_mm'] is not None]
        screen = screen_nonincident_clearance(case, selected, focus_edge_ids=focus,
            margin_mm=1.2, max_segment_pairs=2_000_000)
        if screen.get('reason') == 'pair_budget_exhausted':
            raise ValueError('Surroundings screen incomplete: budget exhausted')
        outside = []
        for contact in screen['potential_contacts']:
            if all(e in focus for e in contact['edges']):
                continue
            outside.append({**contact,'normalized_pair':sorted(normalized(e) for e in contact['edges'])})
        return screen, outside

    before, old_contacts = inspect(baseline, baseline_focus)
    after, new_contacts = inspect(candidate, candidate_focus)
    old_pairs = {tuple(c['normalized_pair']) for c in old_contacts}
    new_pairs = {tuple(c['normalized_pair']) for c in new_contacts}
    if any(p.read_bytes()!=b for p,b in zip(paths,raw)):
        raise ValueError('Input snapshot changed')
    report = dict(schema='vv-toolbox.arch-surroundings/1',baseline_revision=baseline_revision,
        candidate_revision=revision,margin_mm=1.2,pair_budget=2_000_000,
        local_junction_report_sha256=hashlib.sha256(local_raw).hexdigest(),
        baseline_screen=before,candidate_screen=after,
        baseline_surrounding_contacts=old_contacts,candidate_surrounding_contacts=new_contacts,
        new_surrounding_pairs=[list(p) for p in sorted(new_pairs-old_pairs)],
        persistent_surrounding_pairs=[list(p) for p in sorted(new_pairs&old_pairs)],
        no_longer_detected_pairs=[list(p) for p in sorted(old_pairs-new_pairs)],
        bridge_surrounding_contacts=[c for c in new_contacts if bridge_id in c['edges']],
        inputs_unchanged=True,
        missing_geometry_ids={label:[e['id'] for e in case['edges'] if e['centerline_mm'] is None]
                              for label,case in [('baseline',baseline),('candidate',candidate)]},
        source_coverage_limitation='Coverage is limited to imported case geometry; source parts missing before case import are not tested.',
        comparison_policy='Normalize only the two split arch children to their preserved parent identity; exclude within-focus pairs from surroundings delta, retaining complete raw screens.',
        selected_junction_region_status=local['region_clearance']['status'],
        surrounding_clearance_status='UNKNOWN' if new_contacts else 'PASS',
        shared_node_contacts='Not screened here; selected local junction region inspection is separate.',
        final_mesh_collision='NOT RUN',anatomical_acceptance='UNKNOWN',default_adoption='NOT ACCEPTED')
    target=ROOT/'docs/evidence/arch-surroundings.json'
    target.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(baseline_pairs=len(old_pairs),candidate_pairs=len(new_pairs),
        new_pairs=report['new_surrounding_pairs'],persistent=len(new_pairs&old_pairs),
        no_longer_detected=report['no_longer_detected_pairs'],
        new_bridge_contacts=report['bridge_surrounding_contacts'],
        before_checks=before['checked_segment_pairs'],after_checks=after['checked_segment_pairs'])))


if __name__=='__main__':
    main()
