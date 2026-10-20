"""Rebuild native-source graph and measure vertex proximity, without editing anatomy.

Run in the project dependency container. Surface vertex proximity is not lumen
continuity or an anatomical branch determination.
"""
import json
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
from vv_toolbox.atlas import load_atlas, ROOT
from vv_toolbox.atlas_centerlines import build_atlas_centerlines

atlas = load_atlas()
graph = build_atlas_centerlines(atlas, cache_dir=ROOT / 'centerline-cache')
out = Path('exports/connection-audit')
out.mkdir(parents=True, exist_ok=True)
(out / 'source-graph.json').write_text(json.dumps(graph), encoding='utf-8')
parts = {p['id']: p for p in atlas.meshes}
selected = 'FJ1718'
neighbors = sorted({l['part_b'] if l['part_a'] == selected else l['part_a']
                    for l in graph['links'] if selected in (l['part_a'], l['part_b'])})
rows = []
for pid in neighbors:
    a, b = parts[selected]['vertices'], parts[pid]['vertices']
    distances, indices = cKDTree(b).query(a)
    i = int(np.argmin(distances))
    rows.append(dict(id=pid, name=parts[pid]['name'],
                     minimum_vertex_distance=float(distances[i]),
                     selected_vertex=a[i].tolist(), neighbor_vertex=b[indices[i]].tolist()))
report = dict(scope='Native atlas only; authored neck estimates and user deformations excluded',
              summary=graph['summary'], selected=selected, neighbors=rows,
              limitations='Nearest vertex distance is sampling-dependent, not triangle clearance, intersection or lumen continuity. Units are original atlas units, assumed mm.')
(out / 'geometry.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))
