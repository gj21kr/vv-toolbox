"""Independent venous extension tests; no server or arterial edits."""
import json

import numpy as np
import pytest

from vv_toolbox.veins import generate_veins


def edges(graph):
    return {edge.name: edge for edge in graph.segments}


@pytest.mark.parametrize("scale,tortuosity", [(0.5, 0), (1, 0.3), (2, 1)])
def test_systemic_routes_and_portal_separation(scale, tortuosity):
    model = generate_veins(scale, tortuosity)
    model.validate()
    assert not (set(model.systemic.nodes) & set(model.portal.nodes))
    for start in ("left_femoral_distal", "right_femoral_distal", "sss_front", "deep_cerebral", "left_renal_hilum"):
        if start == "deep_cerebral":
            start = "right_deep_cerebral"
        terminal='ven_svc_ostium' if start in ('sss_front','right_deep_cerebral') else 'ven_ivc_ostium'
        route, length = model.systemic.route("ven_"+start, terminal)
        assert route and np.isfinite(length) and length > 0
    route, _ = model.portal.route("ven_splenic_hilum", "ven_portal_right_liver")
    assert "ven_portal_vein" in route
    with pytest.raises(ValueError):
        model.portal.route("ven_splenic_hilum", "ven_right_atrium")


def test_drainage_topology_and_requested_coverage():
    model = generate_veins()
    systemic, portal = edges(model.systemic), edges(model.portal)
    assert systemic["ven_left_sigmoid_lower"].end == "ven_left_jugular_bulb"
    assert systemic["ven_left_internal_jugular_lower"].end == "ven_left_venous_angle"
    assert systemic["ven_left_brachiocephalic"].end == "ven_svc_upper"
    assert systemic["ven_right_gonadal"].end == "ven_ivc_renal"
    assert systemic["ven_left_gonadal"].end == "ven_left_renal_junction"
    assert systemic["ven_great_cerebral_vein"].end == systemic["ven_straight_sinus"].start
    assert systemic["ven_left_hepatic_vein"].end == "ven_ivc_hepatic"
    assert portal["ven_splenic_proximal"].end == portal["ven_superior_mesenteric_proximal"].end
    assert portal["ven_portal_vein"].start == "ven_portal_confluence"
    for side in ("left", "right"):
        for name in ("femoral", "external_iliac", "common_iliac", "internal_iliac", "renal_lateral",
                     "internal_jugular_upper", "transverse_sinus", "superior_petrosal", "inferior_petrosal"):
            assert f"ven_{side}_{name}" in systemic
    assert all(name.startswith("ven_") for name in {*systemic, *portal})


@pytest.mark.parametrize("variation,destination", [("splenic", "ven_splenic_junction"),
                                                  ("superior_mesenteric", "ven_smv_junction"),
                                                  ("confluence", "ven_portal_confluence")])
def test_imv_variation_changes_topology_and_geometry(variation, destination):
    model = generate_veins(imv_drainage=variation)
    edge = edges(model.portal)["ven_inferior_mesenteric"]
    assert edge.end == destination
    np.testing.assert_array_equal(edge.points[-1], model.portal.nodes[destination])
    if variation != "splenic":
        baseline = edges(generate_veins().portal)["ven_inferior_mesenteric"]
        assert not np.array_equal(edge.points, baseline.points)


def test_local_override_does_not_change_other_vessels():
    original = generate_veins()
    changed = generate_veins(vessel_parameters={"ven_left_femoral": {"radius_scale": 1.7, "tortuosity": 0.9}})
    before, after = edges(original.systemic), edges(changed.systemic)
    for name in before:
        if name == "ven_left_femoral":
            assert after[name].radius_mm == pytest.approx(before[name].radius_mm*1.7)
            assert not np.array_equal(before[name].points, after[name].points)
            np.testing.assert_array_equal(before[name].points[[0, -1]], after[name].points[[0, -1]])
        else:
            assert before[name].radius_mm == after[name].radius_mm
            np.testing.assert_array_equal(before[name].points, after[name].points)


def test_transverse_dominance_preserves_connectivity():
    model = generate_veins(transverse_dominance="right")
    ven = edges(model.systemic)
    assert ven["ven_left_transverse_sinus"].radius_mm < ven["ven_right_transverse_sinus"].radius_mm
    model.validate()


def test_bundle_export_and_reproduction():
    model = generate_veins(imv_drainage="confluence", transverse_dominance="left",
                           vessel_parameters={"ven_portal_vein": {"radius_scale": 0.75}})
    payload = json.loads(model.to_json())
    assert payload["schema"] == "vv-toolbox.venous-network/1"
    assert payload["provenance"]["patient_derived"] is False
    assert payload["unmodeled_exchange"]["render_as_vessel"] is False
    clone = generate_veins(**model.generation_kwargs())
    assert clone.to_json() == model.to_json()
    model.parameters["vessel_parameters"]["ven_portal_vein"]["radius_scale"] = 1
    assert clone.parameters["vessel_parameters"]["ven_portal_vein"]["radius_scale"] == 0.75


@pytest.mark.parametrize("kwargs", [
    {"radius_scale": float("nan")}, {"radius_scale": True}, {"tortuosity": -1}, {"samples": 2},
    {"samples": True}, {"imv_drainage": "ivc"}, {"transverse_dominance": "absent"},
    {"vessel_parameters": {"unknown": {"radius_scale": 1}}},
    {"vessel_parameters": {"ven_left_femoral": {"radius_scale": float("inf")}}},
    {"vessel_parameters": {"ven_left_femoral": {"other": 1}}},
])
def test_invalid_configuration_is_rejected(kwargs):
    with pytest.raises(ValueError):
        generate_veins(**kwargs)


def test_smooth_femoral_and_ivc_chain_junctions():
    model = generate_veins(tortuosity=1, samples=128)
    ven = edges(model.systemic)
    for first, second in (("ven_left_femoral", "ven_left_external_iliac"),
                          ("ven_right_external_iliac", "ven_right_common_iliac"),
                          ("ven_ivc_infrarenal", "ven_ivc_suprarenal")):
        a = np.diff(ven[first].points, axis=0)[-1]
        b = np.diff(ven[second].points, axis=0)[0]
        cosine = np.dot(a, b)/(np.linalg.norm(a)*np.linalg.norm(b))
        assert cosine > 0.999


@pytest.mark.parametrize("tortuosity", [0, .3, 1])
def test_unmodeled_atrium_is_a_gap_not_a_continuous_caval_vessel(tortuosity):
    model=generate_veins(tortuosity=tortuosity,samples=128)
    ven = edges(model.systemic)
    ivc, svc = ven["ven_ivc_hepatic"], ven["ven_svc_lower"]
    assert ivc.end=='ven_ivc_ostium' and svc.end=='ven_svc_ostium'
    assert np.linalg.norm(ivc.points[-1]-svc.points[-1])>ivc.radius_mm+svc.radius_mm
    assert 'ven_right_atrium' not in model.systemic.nodes
    with pytest.raises(ValueError,match='No route'):
        model.systemic.route(ivc.end,svc.end)
    record=json.loads(model.to_json())
    assert record['unmodeled_chambers'][0]['render_as_vessel'] is False
    assert record['networks']['systemic_venous']['nonrendered_links']==model.systemic.nonrendered_links


def test_chamber_link_is_required_to_account_for_separate_caval_components():
    model=generate_veins()
    model.systemic.nonrendered_links=None
    with pytest.raises(ValueError,match='Disconnected'):
        model.systemic.validate()


def test_chamber_link_cannot_be_marked_as_rendered_vessel():
    model=generate_veins()
    model.systemic.nonrendered_links[0]['render_as_vessel']=True
    with pytest.raises(ValueError,match='chamber link'):
        model.systemic.validate()
