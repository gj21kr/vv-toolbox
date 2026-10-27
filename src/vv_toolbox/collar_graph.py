"""Graph-only collar replacement preserving both source tails and all incidences."""
from copy import deepcopy

import numpy as np

from .case_contract import validate_case
from .case_io import case_digest
from .collar_link import build_radius_collar


def replace_with_collar(case, *, link_id, incoming_id, outgoing_id,
                        incoming_reverse, outgoing_reverse, collar_mm,
                        expected_revision, case_id):
    validate_case(case)
    if case_digest(case) != expected_revision:
        raise ValueError("Source revision mismatch")
    if "surface_parts" in case:
        raise ValueError("Graph-only source required; surface ownership needs separate mapping")
    if (type(incoming_reverse) is not bool or type(outgoing_reverse) is not bool
            or len({link_id, incoming_id, outgoing_id}) != 3):
        raise ValueError("Distinct edges and explicit traversal directions required")
    edges = {e["id"]: e for e in case["edges"]}
    if any(e not in edges for e in (link_id, incoming_id, outgoing_id)):
        raise ValueError("Unknown replacement edge")
    link = edges[link_id]
    if link["geometry_kind"] != "estimated":
        raise ValueError("Only an estimated link may be replaced")
    paths, radii, nodes = [], [], []
    for ident, reverse in ((incoming_id, incoming_reverse), (outgoing_id, outgoing_reverse)):
        edge = edges[ident]
        points = np.asarray(edge["centerline_mm"], dtype=float)
        radius = np.asarray(edge["radii_mm"], dtype=float)
        paths.append(points[::-1] if reverse else points)
        radii.append(radius[::-1] if reverse else radius)
        nodes.append((edge["end"], edge["start"]) if reverse else (edge["start"], edge["end"]))
    if {nodes[0][1], nodes[1][0]} != {link["start"], link["end"]}:
        raise ValueError("Replacement must join the same source incidences")
    candidate = build_radius_collar(*paths, *radii, collar_mm=collar_mm)
    result = deepcopy(case)
    result.update(case_id=case_id, model_kind="synthetic")
    result["edges"] = [e for e in result["edges"] if e["id"] not in (link_id, incoming_id, outgoing_id)]
    fragment_ids, anchor_ids = [], []
    for side, ident, points, radius, ends in zip(
        ("incoming", "outgoing"), (incoming_id, outgoing_id), paths, radii, nodes
    ):
        binding = candidate["report"][side+"_anchor"]
        index, fraction = binding["interval_index"], binding["fraction"]
        point = candidate["points_mm"][0 if side == "incoming" else -1]
        value = float((1-fraction)*radius[index]+fraction*radius[index+1])
        nid = f"collar:{link_id}:{side}"
        if nid in result["nodes"]:
            raise ValueError("Generated node collision")
        result["nodes"][nid] = dict(kind="junction", evidence_status="synthetic_estimate",
                                    position_mm=point.tolist())
        anchor_ids.append(nid)
        parts = [(np.vstack([points[:index+1], point]), np.r_[radius[:index+1], value], ends[0], nid),
                 (np.vstack([point, points[index+1:]]), np.r_[value, radius[index+1:]], nid, ends[1])]
        ids = []
        for number, (p, r, start, end) in enumerate(parts):
            keep = np.r_[True, np.any(np.diff(p, axis=0) != 0, axis=1)]
            p, r = p[keep], r[keep]
            new_id = f"{ident}::collar:{number}"
            if new_id in edges:
                raise ValueError("Generated edge collision")
            fragment = deepcopy(edges[ident])
            fragment.pop("sample_graph_origin", None)
            fragment.update(id=new_id, start=start, end=end,
                centerline_mm=p.tolist(), radii_mm=r.tolist(),
                collar_origin=dict(parent_edge=ident, parent_revision=expected_revision,
                                   side=side, part=number, source_anchor=binding))
            result["edges"].append(fragment)
            ids.append(new_id)
        fragment_ids.append(ids)
    new_link = deepcopy(link)
    new_link.update(start=anchor_ids[0], end=anchor_ids[1],
                    centerline_mm=candidate["points_mm"].tolist(),
                    radii_mm=candidate["radii_mm"].tolist())
    result["edges"].append(new_link)
    result["generation"] = dict(seed=0, generator_version="preserved-tail-collar/1",
        config=dict(parent_revision=expected_revision, collar_mm=collar_mm, replaced_link=link_id))
    # The old declarations describe the parent snapshot, not the new graph.
    parent_declaration = result.pop("declared_sample_graph", None)
    result["collar_graph"] = dict(parent_revision=expected_revision, parent_declaration=parent_declaration,
        fragments=fragment_ids, anchors=anchor_ids, link_id=link_id,
        preserved_old_nodes=True, original_surface_modified=False,
        anatomy="UNKNOWN", branch_geometry_acceptance="NOT RUN",
        construction=candidate["report"])
    validate_case(result)
    return result
