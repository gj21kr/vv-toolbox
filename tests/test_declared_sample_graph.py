from copy import deepcopy

import pytest

from vv_toolbox.access_routes import inspect_route
from vv_toolbox.case_contract import validate_case
from vv_toolbox.case_io import case_digest
from vv_toolbox.declared_sample_graph import build_declared_sample_graph
from test_synthetic_routes import fixture


def declaration(first_index=1):
    return dict(first_edge="a", first_index=first_index, second_edge="b", second_index=0,
                containment_status="PASS", evidence_ref="fixture inspection")


def test_internal_attachment_preserves_both_tails_and_unresolved_source():
    case, _ = fixture()
    case["edges"][0]["centerline_mm"].insert(1, [5, 0, 0])
    case["edges"][0]["radii_mm"].insert(1, 1.5)
    before = deepcopy(case)
    result = build_declared_sample_graph(case, ["a", "b"], [declaration()],
                                        case_id="sample-graph", expected_revision=case_digest(case))
    assert case == before
    fragments = result["edges"][:2]
    assert fragments[0]["centerline_mm"] + fragments[1]["centerline_mm"][1:] == case["edges"][0]["centerline_mm"]
    assert all(e["evidence_status"] == "unresolved" for e in fragments)
    incidence = validate_case(result)
    assert len(incidence["sample:a:1"]) == 3
    route = inspect_route(result, "0", "3", [fragments[0]["id"], "declared-link:0", "b"])
    assert route["status"] == "UNKNOWN" and route["edges"]


def test_coincident_alias_has_no_zero_length_edge_and_keeps_source_record():
    case, _ = fixture()
    case["nodes"]["2"]["position_mm"] = [10, 0, 0]
    case["edges"][1]["centerline_mm"][0] = [10, 0, 0]
    before = deepcopy(case)
    result = build_declared_sample_graph(case, ["a", "b"], [declaration()],
                                        case_id="alias", expected_revision=case_digest(case))
    assert case == before
    assert len(result["edges"]) == 2
    assert result["declared_sample_graph"]["node_aliases"] == {"2": "1"}
    assert "2" in result["declared_sample_graph"]["original_nodes"]
    assert result["edges"][1]["start"] == result["edges"][0]["end"]
    validate_case(result)


@pytest.mark.parametrize("change", ["revision", "index", "evidence"])
def test_bad_declarations_fail_before_mutation(change):
    case, _ = fixture()
    before = deepcopy(case)
    spec = declaration()
    revision = case_digest(case)
    if change == "revision":
        revision = "wrong"
    elif change == "index":
        spec["first_index"] = 100
    else:
        spec["containment_status"] = "UNKNOWN"
    with pytest.raises(ValueError):
        build_declared_sample_graph(case, ["a", "b"], [spec], case_id="bad", expected_revision=revision)
    assert case == before
