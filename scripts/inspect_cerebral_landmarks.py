"""Inspect source landmark assets without assigning anatomical boundary points."""
import csv
import hashlib
import io
import json
import re
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'reference-data/bodyparts3d'
TARGETS = {'FJ1742': 'corpus callosum', 'FJ1748': 'left insula',
           'FJ1749': 'right insula', 'FJ1655': 'anterior communicating artery'}
TERMS = ['genu', 'rostrum', 'limen', 'circular sulcus', 'limiting sulcus',
         'operculum', 'opercular', 'lateral sulcus']


def inspect():
    manifest = json.loads((SOURCE / 'acquisition.json').read_text())
    inputs = {}
    for name in ['isa_BP3D_4.0_obj_99.zip', 'isa_element_parts.txt',
                 'isa_parts_list_e.txt', 'partof_parts_list_e.txt']:
        data = (SOURCE / name).read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if digest != manifest['files'][name]['sha256']:
            raise ValueError(f'Source fingerprint mismatch: {name}')
        inputs[name] = digest
    rows = list(csv.reader(io.StringIO((SOURCE / 'isa_element_parts.txt').read_text()), delimiter='\t'))
    result = {'schema': 'vv-toolbox.landmark-inventory/1', 'input_sha256': inputs,
              'boundary_coordinates_assigned': False, 'assets': [], 'term_matches': {}}
    with zipfile.ZipFile(SOURCE / 'isa_BP3D_4.0_obj_99.zip') as z:
        for element, expected_name in TARGETS.items():
            matches = [name for name in z.namelist() if Path(name).name == element + '.obj']
            if len(matches) != 1:
                raise ValueError(f'Expected one OBJ for {element}')
            raw = z.read(matches[0])
            vertices = [list(map(float, line.split()[1:4])) for line in raw.decode().splitlines()
                        if line.startswith('v ')]
            faces = sum(line.startswith('f ') for line in raw.decode().splitlines())
            concepts = [row[:2] for row in rows if len(row) >= 3 and row[2] == element and row[1] == expected_name]
            if not vertices or not concepts:
                raise ValueError(f'Missing geometry or exact concept: {element}')
            result['assets'].append({'element_id': element, 'name': expected_name,
                'concepts': concepts, 'obj_sha256': hashlib.sha256(raw).hexdigest(),
                'vertex_count': len(vertices), 'face_count': faces,
                'source_bounds': [[min(p[i] for p in vertices) for i in range(3)],
                                  [max(p[i] for p in vertices) for i in range(3)]],
                'units_status': 'not_verified', 'boundary_status': 'unresolved'})
    for name in ['isa_parts_list_e.txt', 'partof_parts_list_e.txt']:
        lines = (SOURCE / name).read_text().splitlines()
        result['term_matches'][name] = {term: [line for line in lines
            if re.search(r'\b' + re.escape(term) + r'\b', line, re.IGNORECASE)] for term in TERMS}
    return result


if __name__ == '__main__':
    result = inspect()
    output = ROOT / 'docs/evidence/cerebral-landmark-inventory.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'assets': len(result['assets']),
        'boundary_coordinates_assigned': result['boundary_coordinates_assigned'],
        'geometry_counts': [[a['element_id'], a['vertex_count'], a['face_count']] for a in result['assets']],
        'term_match_counts': {name: {term: len(matches) for term, matches in terms.items()}
                              for name, terms in result['term_matches'].items()}}))
