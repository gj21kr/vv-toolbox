"""Exercise estimated-neck capture using the live graph and pinned source atlas."""
import json
from pathlib import Path
from urllib.request import urlopen

import numpy as np

from vv_toolbox.atlas import load_atlas
from vv_toolbox.atlas_neck import build_neck_repairs
from vv_toolbox.case_app_service import CaseWorkspace


def get(path):
    with urlopen('http://127.0.0.1:8093'+path, timeout=30) as response:
        return json.load(response)


def main():
    before = get('/api/state')
    if before['busy'] or before.get('interval_preview_busy') or before['atlas_modifications'] or before.get('atlas_interval_edits'):
        raise ValueError('An idle unmodified reference scene is required')
    graph = get('/api/atlas-centerlines')
    atlas = load_atlas()
    neck, _ = build_neck_repairs(atlas)
    parts = [*atlas.meshes, *neck]
    store = CaseWorkspace('exports/atlas-case-estimates/not-written.json')
    status = store.update(dict(action='prepare_current',version=0), preview=graph,
                          metadata=atlas.metadata, surface_parts=parts)
    sources = {p['id']:p for p in parts}
    for p in store.case['surface_parts']:
        if not all(np.array_equal(p[key],sources[p['part_id']][source_key])
                   for key,source_key in [('vertices_mm','vertices'),('faces','faces')]):
            raise ValueError('Capture changed source/estimated surface arrays')
    capture = store.case['inspection']['atlas_scene_capture']
    expected = {p['id'] for p in neck if p['layer']=='arterial'}
    if set(capture['estimated_parts']) != expected or len(expected)!=4:
        raise ValueError('Estimated arterial coverage differs')
    if get('/api/state')['generation'] != before['generation']:
        raise ValueError('Live source changed during capture')
    result = dict(status='PASS',scope='Current implementation service with live graph and regenerated pinned Atlas parts',
                  summary=status['summary'],estimated_parts=capture['estimated_parts'],
                  omitted_arterial_parts=capture['omitted_arterial_parts'],
                  exact_surface_arrays=True,live_workspace_modified=False,
                  browser='NOT RUN',lumen_union='NOT RUN',anatomical_connectivity='NOT RUN')
    Path('docs/evidence/atlas-case-estimate-capture.json').write_text(
        json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result))


if __name__=='__main__':
    main()
