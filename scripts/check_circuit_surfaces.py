"""Conservative boundary-separation check on the actual default display meshes."""
from itertools import combinations
import json
import numpy as np
from scipy.spatial import cKDTree
from vv_toolbox import generate
from vv_toolbox.veins import generate_veins
from vv_toolbox.surface import network_mesh


def main():
    veins = generate_veins(imv_drainage='superior_mesenteric', transverse_dominance='left',
        vessel_parameters={'ven_inferior_mesenteric': {'radius_scale': 1.05, 'tortuosity': .3}})
    graphs = {'arterial': generate(absent_communicators=['left_pcom']), **veins.graphs}
    meshes = {}
    for name, graph in graphs.items():
        vertices, faces = network_mesh(graph)
        # Every triangle point is within this distance of any of its vertices.
        diameter = max(float(np.linalg.norm(vertices[faces[:, i]] - vertices[faces[:, j]], axis=1).max())
                       for i, j in ((0, 1), (1, 2), (2, 0)))
        meshes[name] = vertices, diameter
    results = []
    for (a, (va, da)), (b, (vb, db)) in combinations(meshes.items(), 2):
        nearest = float(cKDTree(va).query(vb, workers=-1)[0].min())
        lower_bound = nearest - da - db
        results.append(dict(layers=[a, b], minimum_vertex_distance_mm=nearest,
                            surface_distance_lower_bound_mm=lower_bound,
                            status='PASS' if lower_bound > 0 else 'INCONCLUSIVE'))
    print(json.dumps(results, indent=2))
    # This tests boundary intersection, not containment, anatomical fidelity or all edits.
    if any(row['status'] != 'PASS' for row in results):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
