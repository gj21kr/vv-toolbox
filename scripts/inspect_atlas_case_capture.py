"""Compare the browser-downloaded case with every represented source mesh."""
import hashlib
import json
from pathlib import Path

import numpy as np

from vv_toolbox.atlas import load_atlas
from vv_toolbox.case_io import load_case


def main():
    path = Path('exports/atlas-case-capture-ui/case.snapshot.json')
    case, revision = load_case(path)
    atlas = load_atlas()
    sources = {p['id']: p for p in atlas.meshes if p['layer'] == 'arterial'}
    checked = []
    for p in case['surface_parts']:
        source = sources[p['part_id']]
        if not (np.array_equal(p['vertices_mm'], source['vertices'])
                and np.array_equal(p['faces'], source['faces'])):
            raise ValueError(f"Downloaded geometry mismatch: {p['part_id']}")
        checked.append(p['part_id'])
    if len(set(checked)) != len(checked):
        raise ValueError('Duplicate captured parts')
    missing = sorted(set(sources) - set(checked))
    declared = case['inspection']['atlas_scene_capture']['omitted_arterial_parts']
    if not set(missing) <= set(declared):
        raise ValueError('Unreported source surface omission')
    result = dict(status='PASS', scope='Exact source array comparison for all captured arterial parts',
                  archive_sha256=atlas.metadata['sha256'], case_revision=revision,
                  file_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                  source_arterial_parts=len(sources), captured_parts=len(checked),
                  vertices=sum(len(p['vertices_mm']) for p in case['surface_parts']),
                  triangles=sum(len(p['faces']) for p in case['surface_parts']),
                  missing_source_parts=missing, all_declared_omissions=declared,
                  anatomical_validation='NOT RUN', masks='NOT RUN')
    Path('docs/evidence/atlas-case-capture-geometry.json').write_text(
        json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
