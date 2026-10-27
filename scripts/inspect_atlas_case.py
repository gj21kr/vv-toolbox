"""Reproducible source import check; does not approve anatomical segments."""
import hashlib
import json
from pathlib import Path

from vv_toolbox.atlas import PINNED
from vv_toolbox.atlas_case import build_atlas_case


def main():
    root = Path(__file__).resolve().parents[1]
    source_root = root / 'reference-data/bodyparts3d'
    archive = source_root / 'isa_BP3D_4.0_obj_99.zip'
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    if digest != PINNED[archive.name]:
        raise ValueError('source archive fingerprint mismatch')
    raw = (source_root / 'centerlines-preview.json').read_bytes()
    preview_hash = hashlib.sha256(raw).hexdigest()
    bindings = {}
    for ident, artery, side in [('FJ1654', 'ACA', 'R'), ('FJ1654M', 'ACA', 'L'),
                                ('FJ1692', 'MCA', 'R'), ('FJ1692M', 'MCA', 'L')]:
        bindings[ident] = {'artery': artery, 'side': side,
                           'identity_refs': ['docs/CEREBRAL_SEGMENT_SPEC.md',
                                             'docs/CEREBRAL_LANDMARK_INSPECTION.md']}
    case = build_atlas_case(json.loads(raw), bindings,
        source={'id': 'bp3d', 'sha256': digest, 'license_ref': 'BodyParts3D CC BY 4.0'},
        extraction_source={'id': 'bp3d-preview', 'sha256': preview_hash,
                           'license_ref': 'BodyParts3D CC BY 4.0 derived medial preview'},
        frame={'id': 'bodyparts3d_native_LPS', 'units': 'mm', 'axes': 'LPS',
               'origin': 'unchanged BodyParts3D native origin', 'confirmed': True},
        case_id='bp3d-cerebral-import-inspection', base_model_id='bodyparts3d-4.0')
    case['frame']['evidence_ref'] = 'docs/CEREBRAL_LANDMARK_INSPECTION.md'
    output = root / 'exports/atlas-case-inspection/case.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(case, indent=2) + '\n', encoding='utf-8')
    report = {'scope': 'four source parts only; no anatomical route or segment approval',
              'status': 'PASS', 'source_sha256': digest, 'preview_sha256': preview_hash,
              'case_sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
              'parts': sorted(bindings), 'node_count': len(case['nodes']),
              'edge_count': len(case['edges']),
              'unresolved_edge_count': sum(e['evidence_status'] == 'unresolved' for e in case['edges']),
              'candidate_links_not_traversable': len(case['inspection']['candidate_links']),
              'missing_path_parts': case['inspection']['missing_path_parts'],
              'input_bytes_unchanged': raw == (source_root / 'centerlines-preview.json').read_bytes()}
    (root / 'docs/evidence/atlas-case-import.json').write_text(
        json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
