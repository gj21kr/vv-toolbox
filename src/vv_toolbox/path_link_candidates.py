"""Explicit path-pair sample links, without inferring anatomical connectivity."""
import numpy as np
from scipy.spatial import cKDTree


def enumerate_path_links(first, second):
    """Keep one nearest sampled-point proposal for every supplied path pair.

    This is not a continuous closest-polyline solver, and no proposal is an
    approved graph edge. Sorting and first-index tie breaking are deterministic.
    """
    prepared = []
    for paths in (first, second):
        if not isinstance(paths, dict) or not paths:
            raise ValueError("Explicit nonempty path maps required")
        group = {}
        for name, points in paths.items():
            points = np.asarray(points, dtype=float)
            if (not isinstance(name, str) or not name
                    or points.ndim != 2 or points.shape[1] != 3 or len(points) < 2
                    or not np.isfinite(points).all()):
                raise ValueError("Named finite 3D paths required")
            group[name] = points
        prepared.append(group)
    rows = []
    for aid, a in sorted(prepared[0].items()):
        for bid, b in sorted(prepared[1].items()):
            distances, _ = cKDTree(b).query(a)
            i = int(np.argmin(distances))
            # Resolve equal-distance neighbors independently of tree ordering.
            squared = np.sum((b-a[i])**2, axis=1)
            j = int(np.argmin(squared))
            rows.append(dict(first_edge=aid, second_edge=bid,
                             first_index=i, second_index=j,
                             points_mm=[a[i].tolist(), b[j].tolist()],
                             distance_mm=float(np.sqrt(squared[j])),
                             connection_status="UNADJUDICATED",
                             method="nearest-sampled-point-per-explicit-path-pair/1"))
    return rows
