"""Record exact branch-patch interfaces and their neighboring source owners."""
import hashlib
import json
from pathlib import Path

import numpy as np

from vv_toolbox.patch_interfaces import inspect_patch_interfaces


def main():
    root = Path('docs/evidence')
    patch = json.loads((root/'brachiocephalic-source-patch.json').read_text())
    union = json.loads((root/'femoral-anterior-union.json').read_text())
    source = Path('exports/femoral-anterior-union/candidate.npz')
    artifact = Path(patch['artifact'])
    if (hashlib.sha256(source.read_bytes()).hexdigest() != patch['source_surface_sha256']
            or union['output_sha256'] != patch['source_surface_sha256']
            or hashlib.sha256(artifact.read_bytes()).hexdigest() != patch['artifact_sha256']):
        raise ValueError('Patch/source identity mismatch')
    with np.load(source,allow_pickle=False) as data, np.load(artifact,allow_pickle=False) as part:
        if not np.array_equal(data['vertices'][data['faces'][part['source_face_ids']]], part['vertices'][part['faces']]):
            raise ValueError('Patch triangle mismatch')
        result = inspect_patch_interfaces(data['faces'], part['source_face_ids'])
    lineage = union['face_lineage']
    for loop in result['loops']:
        counts = {}
        for edge in loop['edges']:
            names = [lineage['source_names'][lineage['face_source_indices'][fid]]
                     for fid in edge['complement_face_ids']]
            edge['complement_source_owners'] = names
            for name in names:
                counts[name] = counts.get(name,0)+1
        loop['complement_owner_edge_counts'] = counts
    result.update(source_surface_sha256=patch['source_surface_sha256'],
        patch_sha256=patch['artifact_sha256'], source_modified=False, live_scene_changed=False)
    (root/'brachiocephalic-patch-interfaces.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(status=result['status'], edges=result['boundary_edge_count'],
        loops=[r['complement_owner_edge_counts'] for r in result['loops']])))


if __name__ == '__main__':
    main()
