import json
import numpy as np
import pytest
from vv_toolbox import ARCH_VARIANTS, generate


def segments(graph):
    return {edge.name:edge for edge in graph.segments}


@pytest.mark.parametrize("variant", ARCH_VARIANTS)
def test_branch_variants_change_real_adjacency(variant):
    graph = generate(arch_variant=variant)
    graph.validate()
    edges = segments(graph)
    expected = {"standard":"arch_carotid_origin","common_origin":"arch_right","left_carotid_from_brachiocephalic":"brachiocephalic","left_vertebral_from_arch":"arch_carotid_origin"}
    assert edges["left_common_carotid"].start == expected[variant]
    assert edges["left_vertebral_proximal"].start == ("arch_vertebral_origin" if variant == "left_vertebral_from_arch" else "left_subclavian")
    if variant == "standard":
        origins = [edges[name].start for name in ("brachiocephalic","left_common_carotid","left_subclavian")]
        assert len(set(origins)) == 3
        assert len({tuple(graph.nodes[name]) for name in origins}) == 3
    for side in ("left","right"):
        for target in ("left_aca","left_mca","left_pca","right_aca","right_mca","right_pca"):
            assert graph.route(f"{side}_femoral",target)[1] > 0


def test_local_controls_are_absolute_and_isolated():
    base = generate(radius_scale=2,tortuosity=.3)
    changed = generate(radius_scale=2,tortuosity=.3,vessel_parameters={"left_mca_m2":{"radius_scale":.5,"tortuosity":.8}})
    a,b = segments(base),segments(changed)
    assert b["left_mca_m2"].radius_mm == a["left_mca_m2"].radius_mm/4
    assert not np.array_equal(a["left_mca_m2"].points,b["left_mca_m2"].points)
    np.testing.assert_array_equal(a["left_mca_m2"].points[[0,-1]],b["left_mca_m2"].points[[0,-1]])
    for name in set(a)-{"left_mca_m2"}:
        np.testing.assert_array_equal(a[name].points,b[name].points)
        assert a[name].radius_mm == b[name].radius_mm


def test_arch_ratio_moves_origin_and_reports_surrogate():
    low,high = generate(arch_height_ratio=.5,tortuosity=0),generate(arch_height_ratio=2.5,tortuosity=0)
    assert high.nodes["arch_right"][2] < low.nodes["arch_right"][2]
    assert high.parameters["arch_measurement"]["measured_centerline_ratio"] > low.parameters["arch_measurement"]["measured_centerline_ratio"]
    for graph in (low,high):
        m = graph.parameters["arch_measurement"]
        assert m["clinical_classification"] is False
        assert m["left_cca_diameter_mm"] == 2*segments(graph)["left_common_carotid"].radius_mm
        assert m["measured_centerline_ratio"] == pytest.approx(graph.parameters["arch_height_ratio"],abs=.015)


def test_abdominal_and_cerebral_connectivity():
    edges = segments(generate())
    for name in ("splenic_artery","common_hepatic","left_gastric"):
        assert edges[name].start == "celiac_trunk"
    assert edges["celiac_trunk"].start == "celiac_origin"
    assert {edges[name].start for name in ("celiac_trunk","superior_mesenteric","left_renal","inferior_mesenteric")} == {"celiac_origin","sma_origin","renal_origin","ima_origin"}
    for side in ("left","right"):
        for artery,prefix in (("aca","a"),("mca","m"),("pca","p")):
            a,b,c = [edges[f"{side}_{artery}_{prefix}{i}"] for i in (1,2,3)]
            assert a.end == b.start and b.end == c.start
            assert c.end == f"{side}_{artery}"
        assert edges[f"{side}_pcom"].start == f"{side}_ica"
        assert edges[f"{side}_pcom"].end == edges[f"{side}_pca_p1"].end
    assert {edges["acom"].start,edges["acom"].end} == {edges["left_aca_a1"].end,edges["right_aca_a1"].end}


@pytest.mark.parametrize("absent", [(),("acom",),("left_pcom","right_pcom"),("acom","left_pcom","right_pcom")])
def test_communicator_variation_retains_nodes_and_connectedness(absent):
    base,changed = generate(),generate(absent_communicators=absent)
    changed.validate()
    assert set(base.nodes) == set(changed.nodes)
    assert set(segments(base))-set(segments(changed)) == set(absent)


def test_export_reproduction_and_reset():
    graph = generate(arch_variant="left_vertebral_from_arch",arch_height_ratio=2.5,absent_communicators=("acom",),vessel_parameters={"splenic_artery":{"radius_scale":1.7,"tortuosity":.8}})
    raw = json.loads(graph.to_json())
    kwargs = {key:raw["parameters"][key] for key in graph.generation_kwargs()}
    assert generate(**kwargs).to_json() == graph.to_json()
    assert generate().to_json() == generate(**generate().generation_kwargs()).to_json()


@pytest.mark.parametrize("kwargs", [{"arch_variant":"bad"},{"arch_height_ratio":4},{"arch_height_ratio":float("nan")},{"vessel_parameters":{"unknown":{}}},{"vessel_parameters":{"acom":{"radius_scale":0}}},{"vessel_parameters":{"acom":{"other":1}}},{"absent_communicators":("bad",)},{"absent_communicators":"acom"}])
def test_invalid_editable_inputs(kwargs):
    with pytest.raises(ValueError):
        generate(**kwargs)
