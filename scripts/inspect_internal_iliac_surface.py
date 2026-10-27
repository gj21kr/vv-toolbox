"""Inspect the explicit synthetic iliac compound junction without editing it."""
import hashlib
import json
from pathlib import Path

import numpy as np

from vv_toolbox.case_io import load_case
from vv_toolbox.case_surface import build_case_surface
from vv_toolbox.geometry_quality import screen_nonincident_clearance
from vv_toolbox.junction_regions import inspect_junction_regions

ROOT = Path(__file__).resolve().parents[1]


def main():
    path = ROOT / 'exports/synthetic-common-iliac-trunk/case.snapshot.json'
    original = path.read_bytes()
    case, revision = load_case(path)
    expected = json.loads((ROOT / 'docs/evidence/common-iliac-trunk-simplification.json').read_text())
    if revision != expected['case_revision']:
        raise ValueError('trunk inspection revision mismatch')
    edges = {e['id']: e for e in case['edges']}
    arms = [('synthetic_R_common_iliac_trunk', 'start'),
            ('R-EIA-retained', 'end'), ('FJ3569:e0', 'end')]
    connectors = ['R_iliac_continuation_before_IIA',
                  'R_iliac_continuation_after_IIA', 'estimated_R_internal_iliac_origin']
    spacing = .6
    # Freeze the same radius-based extent rule used by other local junctions.
    width = 3 * max(edges[e]['radii_mm'][0 if end == 'start' else -1]
                    for e, end in arms) + 2 * spacing
    portions = [dict(edge_id=e, endpoint=end, length_mm=width) for e, end in arms]
    for ident in connectors:
        p = np.asarray(edges[ident]['centerline_mm'])
        length = float(np.cumsum(np.linalg.norm(np.diff(p, axis=0), axis=1))[-1])
        portions.append(dict(edge_id=ident, endpoint='start', length_mm=length))
    selected = [p['edge_id'] for p in portions]
    regions = [dict(id='R-common-external-internal-iliac', case_sha256=revision,
        root_node_id=edges['estimated_R_internal_iliac_origin']['start'],
        rationale='Compound synthetic bifurcation: three bounded external arms and three internal connector edges',
        evidence_refs=['docs/INTERNAL_ILIAC_BRANCH.md',
                       'docs/evidence/common-iliac-trunk-simplification.json'], portions=portions)]
    local = inspect_junction_regions(case, selected, regions, margin_mm=2*spacing,
                                     max_segment_pairs=2_000_000)
    print(json.dumps(dict(stage='local', status=local.get('status'))), flush=True)
    surrounding = screen_nonincident_clearance(case,
        [e['id'] for e in case['edges'] if e['centerline_mm'] is not None],
        focus_edge_ids=selected, margin_mm=2*spacing, max_segment_pairs=2_000_000)
    if surrounding.get('reason') == 'pair_budget_exhausted':
        raise ValueError('surrounding inspection budget exhausted')
    output = ROOT / 'exports/internal-iliac-surface'
    output.mkdir(parents=True, exist_ok=True)
    try:
        v, f, metadata = build_case_surface(case, selected, spacing_mm=spacing,
                                           junction_regions=regions)
        artifact = output / 'surface.npz'
        np.savez_compressed(artifact, vertices_mm=v, faces=f,
                            metadata=np.array(json.dumps(metadata)))
        surface = dict(status='PASS', vertices=len(v), triangles=len(f), metadata=metadata,
                       sha256=hashlib.sha256(artifact.read_bytes()).hexdigest())
    except ValueError as error:
        surface = dict(status='FAIL', reason=str(error), surface_published=False)
    if path.read_bytes() != original:
        raise ValueError('input changed during inspection')
    report = dict(schema='vv-toolbox.internal-iliac-surface-inspection/1', case_revision=revision,
        selected_edge_ids=selected, junction_regions=regions, local_clearance=local,
        surrounding_screen=surrounding, surface=surface, input_unchanged=True,
        omitted_source_edge=expected['specification']['omit_edge_id'],
        anatomy='UNKNOWN', inside_junction_region_collision='NOT RUN',
        final_mesh_collision='NOT RUN', visual_review='NOT RUN', default_app_applied=False)
    (ROOT / 'docs/evidence/internal-iliac-surface-inspection.json').write_text(
        json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(surface={k: v for k, v in surface.items() if k != 'metadata'},
        surrounding_contact_count=len(surrounding['potential_contacts']))))


if __name__ == '__main__':
    main()
