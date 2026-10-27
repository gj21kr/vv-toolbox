"""Materialize explicit sampled attachments in a separate graph-only case."""
from copy import deepcopy

from .case_contract import validate_case
from .case_io import case_digest


def build_declared_sample_graph(source, edge_ids, links, *, case_id, expected_revision):
    """Preserve every selected polyline sample and all local branches.

    Connections are declared synthetic hypotheses. Original unresolved evidence
    is not upgraded. The caller must bind containment evidence to the same mesh.
    """
    validate_case(source)
    if case_digest(source) != expected_revision:
        raise ValueError("Source revision mismatch")
    original = {e["id"]: e for e in source["edges"]}
    if (not isinstance(edge_ids, list) or not edge_ids or len(set(edge_ids)) != len(edge_ids)
            or any(e not in original or original[e]["centerline_mm"] is None for e in edge_ids)):
        raise ValueError("Unique selected source paths required")
    if not isinstance(case_id, str) or not case_id or case_id == source["case_id"]:
        raise ValueError("Distinct derived case ID required")
    if not isinstance(links, list) or not links:
        raise ValueError("Explicit link declarations required")
    cuts = {e: {0, len(original[e]["centerline_mm"])-1} for e in edge_ids}
    for link in links:
        if link.get("containment_status") != "PASS" or not link.get("evidence_ref"):
            raise ValueError("Inspected link declaration required")
        for prefix in ("first", "second"):
            eid, index = link.get(prefix+"_edge"), link.get(prefix+"_index")
            if eid not in cuts or type(index) is not int or not 0 <= index < len(original[eid]["centerline_mm"]):
                raise ValueError("Explicit source sample anchor required")
            cuts[eid].add(index)
    result = {key: deepcopy(source[key]) for key in ("schema", "base_model_id", "split", "frame", "sources")}
    result.update(case_id=case_id, model_kind="synthetic",
                  generation=dict(seed=0, generator_version="declared-sample-graph/1",
                                  config=dict(parent_revision=expected_revision, links=deepcopy(links))),
                  nodes={}, edges=[])
    anchors, fragments = {}, {}
    for eid in edge_ids:
        edge = original[eid]
        indices = sorted(cuts[eid])
        for index in indices:
            if index in (0, len(edge["centerline_mm"])-1):
                nid = edge["start"] if index == 0 else edge["end"]
                node = deepcopy(source["nodes"][nid])
            else:
                nid = f"sample:{eid}:{index}"
                if nid in source["nodes"]:
                    raise ValueError("Generated node ID collision")
                node = dict(kind="junction", evidence_status="synthetic_estimate",
                            position_mm=deepcopy(edge["centerline_mm"][index]),
                            source_anchor=dict(edge_id=eid, sample_index=index))
            if nid in result["nodes"] and result["nodes"][nid] != node:
                raise ValueError("Inconsistent shared node")
            result["nodes"][nid] = node
            anchors[eid, index] = nid
        fragments[eid] = []
        for first, last in zip(indices, indices[1:]):
            fragment = deepcopy(edge)
            ident = eid if len(indices) == 2 else f"{eid}::samples:{first}-{last}"
            if ident != eid and ident in original:
                raise ValueError("Generated edge ID collision")
            fragment.update(id=ident, start=anchors[eid, first], end=anchors[eid, last],
                            centerline_mm=deepcopy(edge["centerline_mm"][first:last+1]),
                            radii_mm=deepcopy(edge["radii_mm"][first:last+1]))
            fragment["sample_graph_origin"] = dict(edge_id=eid, first_index=first, last_index=last,
                                                  source_evidence_status=edge["evidence_status"])
            result["edges"].append(fragment)
            fragments[eid].append(ident)
    aliases = {}

    def canonical(node):
        while node in aliases:
            node = aliases[node]
        return node

    declarations = []
    for index, link in enumerate(links):
        a = (link["first_edge"], link["first_index"])
        b = (link["second_edge"], link["second_index"])
        na, nb = canonical(anchors[a]), canonical(anchors[b])
        pa, pb = result["nodes"][na]["position_mm"], result["nodes"][nb]["position_mm"]
        if pa == pb:
            if na != nb:
                aliases[nb] = na
            declarations.append(dict(kind="coincident_node_alias", first=na, second=nb,
                                     evidence_ref=link["evidence_ref"]))
            result["nodes"][na].update(kind="junction", evidence_status="synthetic_estimate")
        else:
            ident = f"declared-link:{index}"
            if ident in original:
                raise ValueError("Generated link ID collision")
            first, second = original[a[0]], original[b[0]]
            result["edges"].append(dict(id=ident, start=na, end=nb,
                anatomy=dict(artery="synthetic connection", side="unknown", segment="unassigned", branch_id=ident),
                source_ids=sorted(set(first["source_ids"]+second["source_ids"])),
                geometry_kind="estimated", evidence_status="synthetic_estimate",
                centerline_mm=deepcopy([pa, pb]),
                radii_mm=[first["radii_mm"][a[1]], second["radii_mm"][b[1]]],
                derivation=dict(method="declared-straight-sample-link/1", anchors=[list(a), list(b)],
                                evidence_ref=link["evidence_ref"], radius_envelope="NOT RUN")))
            declarations.append(dict(kind="straight_link", edge_id=ident, evidence_ref=link["evidence_ref"]))
    for edge in result["edges"]:
        edge["start"], edge["end"] = canonical(edge["start"]), canonical(edge["end"])
    used = {e[k] for e in result["edges"] for k in ("start", "end")}
    result["nodes"] = {n: v for n, v in result["nodes"].items() if n in used}
    result["declared_sample_graph"] = dict(
        source_revision=expected_revision, fragments=fragments, node_aliases=aliases,
        declarations=declarations, geometry_scope="Graph only; source polylines unchanged",
        source_surface_parts_attached=False, anatomical_validation="UNKNOWN",
        original_nodes={n: deepcopy(source["nodes"][n]) for n in source["nodes"] if n in used or n in aliases})
    validate_case(result)
    return result
