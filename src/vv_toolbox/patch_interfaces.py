"""Source-index interface contracts for a protected surface patch."""
from collections import defaultdict

import numpy as np

from .patch_boundary import patch_boundary_loops


def inspect_patch_interfaces(faces, selected_faces):
    faces, selected = np.asarray(faces), np.asarray(selected_faces)
    loops = patch_boundary_loops(faces, selected)
    chosen = set(selected.tolist())
    uses = defaultdict(list)
    for fid, face in enumerate(faces):
        for a, b in zip(face, np.roll(face, -1)):
            a, b = int(a), int(b)
            uses[tuple(sorted((a, b)))].append((fid, a, b))
    results = []
    for loop in loops:
        rows = []
        for a, b in zip(loop, loop[1:]+loop[:1]):
            incident = uses[tuple(sorted((a,b)))]
            inside = [u for u in incident if u[0] in chosen]
            outside = [u for u in incident if u[0] not in chosen]
            paired = len(inside) == 1 and len(outside) == 1
            opposite = paired and inside[0][1:] == outside[0][:0:-1]
            rows.append(dict(vertex_ids=[a,b], selected_face_ids=[u[0] for u in inside],
                complement_face_ids=[u[0] for u in outside],
                status='PASS' if opposite else 'FAIL', opposite_winding=bool(opposite)))
        results.append(dict(vertex_ids=loop, edges=rows,
                            status='PASS' if all(r['status']=='PASS' for r in rows) else 'FAIL'))
    return dict(status='PASS' if results and all(r['status']=='PASS' for r in results) else 'UNKNOWN' if not results else 'FAIL',
        loops=results, boundary_edge_count=sum(len(r['edges']) for r in results),
        scope='Original mesh index pairing and opposite winding only',
        edited_geometry_compatibility='NOT RUN', anatomical_validation='NOT RUN')
