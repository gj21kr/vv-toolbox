"""Materialize preserved-tail graph candidates and recheck all eight routes."""
import json
from pathlib import Path

from vv_toolbox.access_routes import inspect_route
from vv_toolbox.case_io import load_case, save_case, case_digest
from vv_toolbox.collar_graph import replace_with_collar


def components(case, restrict):
    neighbors = {n: set() for n in case["nodes"]}
    for edge in case["edges"]:
        neighbors[edge["start"]].add(edge["end"])
        neighbors[edge["end"]].add(edge["start"])
    pending, result = set(neighbors), set()
    while pending:
        stack, seen = [next(iter(pending))], set()
        while stack:
            node = stack.pop()
            if node in seen:
                continue
            seen.add(node)
            stack.extend(neighbors[node]-seen)
        pending -= seen
        result.add(frozenset(seen & restrict))
    return result


def main():
    root = Path("docs/evidence")
    record = json.loads((root / "access-sample-graph.json").read_text())
    graph, revision = load_case(record["graph_file"])
    if revision != record["derived_revision"]:
        raise ValueError("Source graph identity mismatch")
    incoming, outgoing = "FJ3417:e0::samples:2-155", "FJ3564:e0::samples:0-144"
    report = dict(status="UNKNOWN", parent_revision=revision, rows=[], live_scene_changed=False,
                  scope="Graph-only connectivity preservation; surface ownership and junction acceptance pending")
    for collar in (10, 20):
        candidate = replace_with_collar(graph, link_id="declared-link:10",
            incoming_id=incoming, outgoing_id=outgoing, incoming_reverse=True,
            outgoing_reverse=True, collar_mm=collar, expected_revision=revision,
            case_id=f"access-collar-{collar}mm")
        assert components(graph, set(graph["nodes"])) == components(candidate, set(graph["nodes"]))
        routes = []
        for route in record["routes"]:
            required = [incoming+"::collar:0" if e == incoming else
                        outgoing+"::collar:1" if e == outgoing else e for e in route["edges"]]
            checked = inspect_route(candidate, route["nodes"][0], route["nodes"][-1], required)
            if not checked.get("edges"):
                raise ValueError("Previously connected route lost")
            routes.append(dict(femoral_side=route["femoral_side"], carotid_side=route["carotid_side"],
                               target=route["target"], **checked))
        digest = case_digest(candidate)
        path = Path("exports/access-collar-graphs") / f"{digest}.snapshot.json"
        if path.exists():
            _, existing = load_case(path)
            if existing != digest:
                raise ValueError("Existing snapshot mismatch")
        else:
            save_case(path, candidate)
        report["rows"].append(dict(collar_mm=collar, graph_file=str(path), revision=digest,
            nodes=len(candidate["nodes"]), edges=len(candidate["edges"]),
            original_node_connectivity="PASS", routes=routes,
            surface_ownership="NOT RUN", branch_geometry_acceptance="NOT RUN"))
        print(json.dumps(dict(collar_mm=collar, nodes=len(candidate["nodes"]),
            edges=len(candidate["edges"]), connected_routes=len(routes))), flush=True)
    (root / "access-collar-graphs.json").write_text(json.dumps(report, indent=2)+"\n")


if __name__ == "__main__":
    main()
