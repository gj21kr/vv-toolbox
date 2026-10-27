"""Read-only inspection preview, never a declaration of accepted anatomy."""
import hashlib
from io import BytesIO
import json
from pathlib import Path

import numpy as np


CANDIDATE_ID = "femoral-anterior-solid-union"


def load_access_union_preview(root):
    root = Path(root)
    evidence = root / "docs/evidence"
    report = json.loads((evidence / "femoral-anterior-union.json").read_text())
    raw = (root / "exports/femoral-anterior-union/candidate.npz").read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if (report["status"] != "CANDIDATE" or report["output_sha256"] != digest
            or report["lineage_check"]["status"] != "PASS"
            or report["union"]["boundary_components"] != 1
            or report["union"]["self_contact"]["status"] != "NO_CONTACT_DETECTED"):
        raise ValueError("Access union geometry does not match completed surface evidence")
    with np.load(BytesIO(raw), allow_pickle=False) as data:
        vertices, faces = data["vertices"].copy(), data["faces"].copy()
    if (vertices.ndim != 2 or vertices.shape[1] != 3 or not np.isfinite(vertices).all()
            or faces.ndim != 2 or faces.shape[1] != 3 or not len(faces)
            or not np.issubdtype(faces.dtype, np.integer)
            or faces.min() < 0 or faces.max() >= len(vertices)
            or report["lineage_check"]["faces"] != len(faces)):
        raise ValueError("Invalid access union geometry")
    lineage = report["face_lineage"]
    names = lineage["source_names"]
    owners = np.asarray(lineage["face_source_indices"])
    original_faces = np.asarray(lineage["source_face_indices"])
    if (not names or len(set(names)) != len(names)
            or owners.shape != (len(faces),) or original_faces.shape != owners.shape
            or not np.issubdtype(owners.dtype, np.integer)
            or not np.issubdtype(original_faces.dtype, np.integer)
            or owners.min() < 0 or owners.max() >= len(names) or original_faces.min() < 0):
        raise ValueError("Complete access union source ownership required")
    audit = dict(self_contact="NO_CONTACT_DETECTED", lineage_faces=len(faces),
                 source_count=len(names), centerline_status="NOT RUN",
                 checked_paths=0, checked_segments=0, context_status="NOT RUN",
                 context_neighbors=0, contacts=[], unknown=[],
                 four_access_routes="NOT RUN")
    for filename, key in (("femoral-anterior-paths.json", "union_sha256"),
                          ("femoral-anterior-context.json", "candidate_sha256")):
        path = evidence / filename
        if not path.exists():
            continue
        inspection = json.loads(path.read_text())
        if (inspection[key] != digest
                or inspection["source_case_revision"] != report["source_case_revision"]):
            raise ValueError("Access union inspection identity mismatch")
        if inspection["status"] not in ("PASS", "FAIL", "UNKNOWN", "RUNNING"):
            raise ValueError("Invalid access union inspection status")
        if key == "union_sha256":
            if set(inspection["source_names"]) != set(names):
                raise ValueError("Access union path scope mismatch")
            if (inspection["status"] == "PASS"
                    and (not inspection["rows"]
                         or {r["part_id"] for r in inspection["rows"]} != set(names)
                         or any(r["status"] != "PASS" for r in inspection["rows"]))):
                raise ValueError("Completed path inspection lacks source coverage")
            audit.update(centerline_status=inspection["status"],
                         checked_paths=len(inspection["rows"]),
                         checked_segments=sum(r.get("segment_count", 0) for r in inspection["rows"]))
        else:
            if (inspection["neighbor_count"] != len(inspection["rows"])
                    or set(inspection["excluded_union_sources"]) != set(names)
                    or (inspection["status"] == "PASS"
                        and (inspection["remaining_contacts"] or inspection["unknown"]))):
                raise ValueError("Access union context scope mismatch")
            audit.update(context_status=inspection["status"],
                         context_neighbors=inspection["neighbor_count"],
                         contacts=inspection["remaining_contacts"], unknown=inspection["unknown"])
    graph_edges, graph_summary = [], None
    graph_record = evidence / "access-sample-graph.json"
    if graph_record.exists():
        from .case_io import load_case
        from .access_routes import inspect_route
        record = json.loads(graph_record.read_text())
        graph_path = (root / record["graph_file"]).resolve()
        if not graph_path.is_relative_to(root.resolve()):
            raise ValueError("Candidate graph must stay within workspace")
        graph, revision = load_case(graph_path)
        if (graph["model_kind"] != "synthetic"
                or record["surface_sha256"] != digest or record["source_revision"] != report["source_case_revision"]
                or revision != record["derived_revision"]
                or graph["candidate_surface_reference"]["sha256"] != digest
                or graph["declared_sample_graph"]["source_revision"] != record["source_revision"]):
            raise ValueError("Candidate graph identity mismatch")
        rows = []
        for route in record["routes"]:
            checked = inspect_route(graph, route["start"], route["end"], route["required_edges"])
            if checked["status"] != route["status"] or checked["edges"] != route["edges"]:
                raise ValueError("Candidate graph route evidence mismatch")
            rows.append(dict(femoral_side=route["femoral_side"], carotid_side=route["carotid_side"],
                             target=route["target"], status=checked["status"],
                             edge_count=len(checked["edges"]),
                             unresolved_edges=len(checked.get("unresolved_edges", []))))
        graph_edges = graph["edges"]
        graph_summary = dict(revision=revision, nodes=len(graph["nodes"]), edges=len(graph_edges),
                             routes=rows, scope=record["scope"],
                             status="PASS" if rows and all(r["status"] == "PASS" for r in rows) else "UNKNOWN")
    return dict(vertices_mm=vertices, faces=faces, edges=graph_edges, face_lineage=lineage,
                source_centerlines={},
                summary=dict(id=CANDIDATE_ID, title="대퇴–전방순환 통합 · 검토 후보",
                    revision=report["source_case_revision"], surface_sha256=digest,
                    vertices=len(vertices), triangles=len(faces), read_only=True,
                    edge_ids=names, centerlines_available=bool(graph_edges), selected_source=None,
                    selectable_sources=[dict(id=name, label=name) for name in names],
                    scope="원본과 분리된 합성 표면 · 전체 ACA/MCA 원위 분지와 구간 라벨은 미완성",
                    access_union=audit, access_graph=graph_summary, anatomy="UNKNOWN", smoothness="NOT RUN"))
