"""Measure oriented polyline transitions without assigning anatomy or limits."""
import numpy as np

from .case_contract import validate_case


def measure_route_junctions(case, route):
    validate_case(case)
    ids, nodes = route.get("edges"), route.get("nodes")
    if not isinstance(ids, list) or not ids or not isinstance(nodes, list) or len(nodes) != len(ids)+1:
        raise ValueError("Explicit route edges and node sequence required")
    edges = {e["id"]: e for e in case["edges"]}
    oriented = []
    for index, ident in enumerate(ids):
        if ident not in edges:
            raise ValueError("Unknown route edge")
        edge = edges[ident]
        endpoints = (nodes[index], nodes[index+1])
        if endpoints == (edge["start"], edge["end"]):
            reverse = False
        elif endpoints == (edge["end"], edge["start"]):
            reverse = True
        else:
            raise ValueError("Route node sequence does not match edge")
        if edge["centerline_mm"] is None:
            raise ValueError("Route geometry required")
        points, radii = np.asarray(edge["centerline_mm"]), np.asarray(edge["radii_mm"])
        oriented.append((points[::-1] if reverse else points, radii[::-1] if reverse else radii))
    rows = []
    for index, ((a, ra), (b, rb)) in enumerate(zip(oriented, oriented[1:])):
        incoming, outgoing = a[-1]-a[-2], b[1]-b[0]
        na, nb = np.linalg.norm(incoming), np.linalg.norm(outgoing)
        if na <= 1e-12 or nb <= 1e-12:
            raise ValueError("Nondegenerate local tangent required")
        cosine = np.clip(np.dot(incoming, outgoing)/(na*nb), -1., 1.)
        rows.append(dict(node_id=nodes[index+1], incoming_edge=ids[index], outgoing_edge=ids[index+1],
                         turn_angle_deg=float(np.degrees(np.arccos(cosine))),
                         radius_jump_mm=float(abs(rb[0]-ra[-1])),
                         position_gap_mm=float(np.linalg.norm(b[0]-a[-1]))))
    return dict(measurement_status="PASS", acceptance_status="UNKNOWN", rows=rows,
                scope="Adjacent source polyline segments along the supplied traversal",
                anatomical_validation="NOT RUN", acceptance_limits="NOT SET")
