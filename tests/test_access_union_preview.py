import hashlib
import json

import numpy as np
import pytest
import trimesh

from vv_toolbox.access_union_preview import load_access_union_preview


def fixture(root):
    folder = root / "exports/femoral-anterior-union"
    folder.mkdir(parents=True)
    evidence = root / "docs/evidence"
    evidence.mkdir(parents=True)
    mesh = trimesh.creation.box()
    path = folder / "candidate.npz"
    np.savez_compressed(path, vertices=mesh.vertices, faces=mesh.faces)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    report = dict(status="CANDIDATE", output_sha256=digest, source_case_revision="fixture",
                  lineage_check=dict(status="PASS", faces=12),
                  union=dict(boundary_components=1, self_contact=dict(status="NO_CONTACT_DETECTED")),
                  face_lineage=dict(source_names=["source"], face_source_indices=[0]*12,
                                    source_face_indices=list(range(12))))
    (evidence / "femoral-anterior-union.json").write_text(json.dumps(report))
    return evidence, path, digest


def test_missing_inspections_remain_not_run_and_not_editable(tmp_path):
    fixture(tmp_path)
    result = load_access_union_preview(tmp_path)
    assert result["source_centerlines"] == {}
    assert result["summary"]["read_only"]
    assert result["summary"]["access_union"]["context_status"] == "NOT RUN"
    assert result["summary"]["access_union"]["centerline_status"] == "NOT RUN"


def test_running_paths_are_not_presented_as_pass(tmp_path):
    evidence, _, digest = fixture(tmp_path)
    (evidence / "femoral-anterior-paths.json").write_text(json.dumps(dict(
        status="RUNNING", union_sha256=digest, source_case_revision="fixture",
        source_names=["source"], rows=[])))
    assert load_access_union_preview(tmp_path)["summary"]["access_union"]["centerline_status"] == "RUNNING"


def test_geometry_tampering_rejected(tmp_path):
    _, path, _ = fixture(tmp_path)
    path.write_bytes(path.read_bytes() + b"changed")
    with pytest.raises(ValueError, match="evidence"):
        load_access_union_preview(tmp_path)


def test_completed_empty_paths_rejected(tmp_path):
    evidence, _, digest = fixture(tmp_path)
    (evidence / "femoral-anterior-paths.json").write_text(json.dumps(dict(
        status="PASS", union_sha256=digest, source_case_revision="fixture",
        source_names=["source"], rows=[])))
    with pytest.raises(ValueError, match="coverage"):
        load_access_union_preview(tmp_path)


def test_context_keeps_unknown_contacts_and_checks_identity(tmp_path):
    evidence, _, digest = fixture(tmp_path)
    path = evidence / "femoral-anterior-context.json"
    context = dict(status="UNKNOWN", candidate_sha256=digest, source_case_revision="fixture",
                   neighbor_count=1, rows=[dict(neighbor_id="other")],
                   excluded_union_sources=["source"], remaining_contacts=["other"], unknown=[])
    path.write_text(json.dumps(context))
    result = load_access_union_preview(tmp_path)["summary"]["access_union"]
    assert result["context_status"] == "UNKNOWN"
    assert result["contacts"] == ["other"]
    context["candidate_sha256"] = "wrong"
    path.write_text(json.dumps(context))
    with pytest.raises(ValueError, match="identity"):
        load_access_union_preview(tmp_path)


def test_registered_candidate_description_preserves_unfinished_scope(tmp_path):
    from types import SimpleNamespace
    from vv_toolbox.app import Workspace
    from vv_toolbox.candidate_preview import load_candidate_preview
    fixture(tmp_path)
    candidate = load_candidate_preview(tmp_path, "femoral-anterior-solid-union")
    description = Workspace.description(SimpleNamespace(source="candidate", candidate=candidate), None)
    assert "NOT RUN" in description
    assert "미확인" in description
    assert "12개 면" in description


def graph_fixture(root):
    from test_access_routes import make_case
    from vv_toolbox.access_routes import inspect_route
    from vv_toolbox.case_io import case_digest, save_case
    evidence, _, digest = fixture(root)
    graph = make_case()
    graph.update(model_kind="synthetic", generation=dict(seed=0, generator_version="fixture", config={}),
                 candidate_surface_reference=dict(sha256=digest),
                 declared_sample_graph=dict(source_revision="fixture"))
    graph["nodes"]["lc"]["evidence_status"] = "unresolved"
    route = inspect_route(graph, "lf", "target", ["lf", "lc", "lt"])
    path = root / "exports/graph.snapshot.json"
    save_case(path, graph)
    record = dict(graph_file="exports/graph.snapshot.json", surface_sha256=digest,
                  source_revision="fixture", derived_revision=case_digest(graph), scope="fixture",
                  routes=[dict(start="lf", end="target", required_edges=["lf", "lc", "lt"],
                               femoral_side="L", carotid_side="L", target="fixture", **route)])
    record_path = evidence / "access-sample-graph.json"
    record_path.write_text(json.dumps(record))
    return record_path, record


def test_graph_loaded_and_unknown_route_recomputed(tmp_path):
    graph_fixture(tmp_path)
    result = load_access_union_preview(tmp_path)
    assert result["edges"]
    assert result["summary"]["centerlines_available"]
    assert result["summary"]["access_graph"]["status"] == "UNKNOWN"
    assert result["summary"]["access_graph"]["routes"][0]["unresolved_edges"] > 0


def test_graph_falsified_pass_rejected(tmp_path):
    path, record = graph_fixture(tmp_path)
    record["routes"][0]["status"] = "PASS"
    path.write_text(json.dumps(record))
    with pytest.raises(ValueError, match="route evidence"):
        load_access_union_preview(tmp_path)


def test_graph_path_escape_rejected(tmp_path):
    path, record = graph_fixture(tmp_path)
    record["graph_file"] = "../elsewhere.snapshot.json"
    path.write_text(json.dumps(record))
    with pytest.raises(ValueError, match="workspace"):
        load_access_union_preview(tmp_path)
