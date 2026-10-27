"""Audit all loaded arterial source parts and import their available medial paths."""
import hashlib
import json
import re
from pathlib import Path

from vv_toolbox.atlas import load_atlas
from vv_toolbox.atlas_case import build_atlas_case


def main():
    root = Path(__file__).resolve().parents[1]
    atlas = load_atlas()  # Verifies every pinned input fingerprint.
    preview_path = root / 'reference-data/bodyparts3d/centerlines-preview.json'
    raw = preview_path.read_bytes()
    preview = json.loads(raw)
    source_parts = {p['id']: p for p in atlas.metadata['parts'] if p['layer'] == 'arterial'}
    preview_parts = {p['id']: p for p in preview['parts']}
    bindings, inventory = {}, []
    for ident, part in sorted(source_parts.items()):
        name = part['name']
        sides = set(re.findall(r'\b(left|right)\b', name.lower()))
        side = {'left': 'L', 'right': 'R'}[next(iter(sides))] if len(sides) == 1 else 'unknown'
        paths = [e for e in preview['edges'] if e['part_id'] == ident]
        row = {'part_id': ident, 'source_name': name, 'obj_sha256': part['sha256'],
               'side_from_name': side, 'preview_status': preview_parts.get(ident, {}).get('status', 'ABSENT'),
               'edge_ids': [e['id'] for e in paths], 'anatomical_segments': 'unresolved'}
        inventory.append(row)
        if ident in preview_parts:
            bindings[ident] = {'artery': name, 'side': side,
                'identity_refs': [f"BodyParts3D element {ident}; OBJ SHA256 {part['sha256']}"]}
    case = build_atlas_case(preview, bindings,
        source={'id': 'bp3d', 'sha256': atlas.metadata['sha256'], 'license_ref': 'BodyParts3D CC BY 4.0'},
        extraction_source={'id': 'bp3d-preview', 'sha256': hashlib.sha256(raw).hexdigest(),
                           'license_ref': 'BodyParts3D derived medial preview'},
        frame={'id': 'bodyparts3d_native_LPS', 'units': 'mm', 'axes': 'LPS',
               'origin': 'unchanged BodyParts3D native origin', 'confirmed': True},
        case_id='bp3d-arterial-inventory', base_model_id='bodyparts3d-4.0')
    case['frame']['evidence_ref'] = 'docs/CEREBRAL_LANDMARK_INSPECTION.md'
    output = root / 'exports/atlas-case-inspection/all-arterial-case.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(case, indent=2) + '\n', encoding='utf-8')
    # These are source identity slots, not asserted anatomical edges.
    slots = {
        'L.femoral': 'FJ2074', 'R.femoral': 'FJ2143',
        'L.external_iliac': 'FJ3466', 'R.external_iliac': 'FJ3567',
        'L.common_iliac': 'FJ3464', 'R.common_iliac': 'FJ3565',
        'abdominal_aorta': 'FJ1932', 'descending_thoracic_aorta': 'FJ1931',
        'aortic_arch': 'FJ3411', 'brachiocephalic': 'FJ3417',
        'L.common_carotid': 'FJ3483', 'R.common_carotid': 'FJ3564',
        'L.internal_carotid': 'FJ1682M', 'R.internal_carotid': 'FJ1682',
        'L.ACA_source': 'FJ1654M', 'R.ACA_source': 'FJ1654',
        'L.MCA_sphenoid_source': 'FJ1692M', 'R.MCA_sphenoid_source': 'FJ1692'}
    rows = {r['part_id']: r for r in inventory}
    report = {'scope': 'all selected source arterial parts; not all human arteries',
        'status': 'PASS', 'source_sha256': atlas.metadata['sha256'],
        'preview_sha256': hashlib.sha256(raw).hexdigest(),
        'case_sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
        'source_part_count': len(inventory), 'imported_edge_count': len(case['edges']),
        'imported_node_count': len(case['nodes']),
        'parts_without_paths': [r['part_id'] for r in inventory if not r['edge_ids']],
        'unknown_side_count': sum(r['side_from_name'] == 'unknown' for r in inventory),
        'candidate_links_not_traversable': len(case['inspection']['candidate_links']),
        'rejected_extraction_edges': [{k: r[k] for k in ('edge_id', 'part_id', 'reason')}
                                     for r in case['inspection']['rejected_extraction_edges']],
        'route_slots': {key: rows.get(ident, {'part_id': ident, 'preview_status': 'SOURCE_ABSENT'})
                        for key, ident in slots.items()},
        'route_status': 'UNKNOWN: inter-part anatomical attachments not adjudicated',
        'parts': inventory,
        'input_bytes_unchanged': raw == preview_path.read_bytes()}
    (root / 'docs/evidence/arterial-coverage.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k not in ('parts', 'route_slots')}))


if __name__ == '__main__':
    main()
