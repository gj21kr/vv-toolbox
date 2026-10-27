from copy import deepcopy

import pytest

from vv_toolbox.case_contract import validate_case
from vv_toolbox.case_io import case_digest
from vv_toolbox.collar_graph import replace_with_collar
from vv_toolbox.declared_sample_graph import build_declared_sample_graph
from test_synthetic_routes import fixture


def source():
    case, _ = fixture()
    return build_declared_sample_graph(case, ["a", "b"], [
        dict(first_edge="a", first_index=1, second_edge="b", second_index=0,
             containment_status="PASS", evidence_ref="fixture")
    ], case_id="parent", expected_revision=case_digest(case))


def apply(case, **overrides):
    options = dict(link_id="declared-link:0", incoming_id="a", outgoing_id="b",
        incoming_reverse=False, outgoing_reverse=False, collar_mm=2,
        expected_revision=case_digest(case), case_id="collar")
    options.update(overrides)
    return replace_with_collar(case, **options)


def test_keeps_original_nodes_and_tails_without_source_mutation():
    case = source()
    before = deepcopy(case)
    result = apply(case)
    incidence = validate_case(result)
    assert case == before
    assert set(case["nodes"]) <= set(result["nodes"])
    assert len(result["edges"]) == len(case["edges"])+2
    assert all(len(incidence[n]) == 3 for n in result["collar_graph"]["anchors"])
    fragments = [e for e in result["edges"] if "collar_origin" in e]
    for original in case["edges"]:
        if original["id"] == "declared-link:0":
            continue
        points = [p for e in fragments if e["collar_origin"]["parent_edge"] == original["id"]
                  for p in e["centerline_mm"]]
        assert all(p in points for p in original["centerline_mm"])
    assert all(e["evidence_status"] == "unresolved" for e in fragments)


@pytest.mark.parametrize("overrides", [
    {"expected_revision": "wrong"}, {"incoming_reverse": True},
    {"collar_mm": 1000}, {"outgoing_id": "a"},
])
def test_invalid_replacement_rejected_without_mutation(overrides):
    case = source()
    before = deepcopy(case)
    with pytest.raises(ValueError):
        apply(case, **overrides)
    assert case == before
