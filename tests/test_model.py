import json
import numpy as np
import pytest
from vv_toolbox.model import generate, tube_mesh


def test_tube_frame_handles_bend_parallel_to_initial_reference():
    points = np.array([[0, 0, 0], [0, 0, 1], [1, 0, 1], [2, 0, 1]], dtype=float)
    vertices, faces = tube_mesh(points, 0.1)
    assert np.isfinite(vertices).all()
    rings = vertices.reshape(len(points), 12, 3)
    np.testing.assert_allclose(np.linalg.norm(rings-points[:, None], axis=2), 0.1, atol=1e-7)
    assert faces.max() < len(vertices)


@pytest.mark.parametrize("scale,tortuosity", [(0.5, 0), (1, 0.3), (2, 1)])
def test_all_routes_and_geometry(scale, tortuosity):
    graph = generate(scale, tortuosity)
    graph.validate()
    for side in ("left", "right"):
        assert graph.nodes[f"{side}_femoral"][0] * (1 if side == "left" else -1) > 0
        for target_side in ("left", "right"):
            for artery in ("mca", "aca", "pca"):
                start, target = f"{side}_femoral", f"{target_side}_{artery}"
                route, length = graph.route(start, target)
                reverse, reverse_length = graph.route(target, start)
                assert reverse == route[::-1]
                assert length == pytest.approx(reverse_length)
                current = start
                by_name = {edge.name: edge for edge in graph.segments}
                for name in route:
                    edge = by_name[name]
                    assert current in (edge.start, edge.end)
                    current = edge.end if current == edge.start else edge.start
                assert current == target
                assert length > np.linalg.norm(graph.nodes[target]-graph.nodes[start])
    for edge in graph.segments:
        vertices, faces = tube_mesh(edge.points, edge.radius_mm)
        assert np.isfinite(vertices).all()
        assert faces.max() < len(vertices)
        triangle = vertices[faces]
        assert (np.linalg.norm(np.cross(triangle[:, 1]-triangle[:, 0], triangle[:, 2]-triangle[:, 0]), axis=1) > 0).all()


def test_junctions_and_radius_independent_of_path():
    base, altered = generate(1, 0), generate(2, 1)
    for a, b in zip(base.segments, altered.segments):
        np.testing.assert_array_equal(a.points[[0, -1]], b.points[[0, -1]])
        assert b.radius_mm == 2*a.radius_mm
        # Perturbation of an already curved baseline can locally shorten a bend.
        assert b.length_mm > np.linalg.norm(b.points[-1]-b.points[0])
    assert generate(0.5).route("right_femoral", "left_mca")[1] == generate(2).route("right_femoral", "left_mca")[1]


@pytest.mark.parametrize("tortuosity", [0,0.3,1])
def test_aortic_and_femoral_chains_share_tangents(tortuosity):
    graph = generate(tortuosity=tortuosity)
    by_name = {edge.name:edge for edge in graph.segments}
    chains = [["abdominal_aorta","abdominal_aorta_renal","abdominal_aorta_sma","abdominal_aorta_celiac","abdominal_aorta_upper","thoracic_aorta","distal_arch","aortic_arch","aortic_arch_middle","aortic_arch_proximal","ascending_aorta"],
              ["left_femoral_iliac","left_common_iliac","abdominal_aorta"],
              ["right_femoral_iliac","right_common_iliac","abdominal_aorta"]]
    for chain in chains:
        for before,after in zip(chain,chain[1:]):
            a,b = by_name[before],by_name[after]
            np.testing.assert_array_equal(a.points[-1],b.points[0])
            ta,tb = a.points[-1]-a.points[-2],b.points[1]-b.points[0]
            assert np.dot(ta,tb)/np.linalg.norm(ta)/np.linalg.norm(tb) > 0.99
    arch = np.concatenate([edge.points for name,edge in by_name.items() if name.startswith("aortic_arch")])
    assert arch[:,2].max() > 660, "Arch must have a rounded elevated crown"


@pytest.mark.parametrize("kwargs", [{"radius_scale": 0}, {"radius_scale": float("nan")}, {"radius_scale": float("inf")}, {"tortuosity": -1}, {"tortuosity": 1.01}, {"tortuosity": float("nan")}, {"samples": 2}, {"samples": 64.5}, {"samples": True}])
def test_invalid_parameters(kwargs):
    with pytest.raises(ValueError):
        generate(**kwargs)


def test_export_units_provenance_exact_geometry():
    graph = generate()
    document = json.loads(graph.to_json())
    assert document["schema"] == "vv-toolbox.graph/1"
    assert document["units"] == "mm"
    assert document["provenance"]["patient_derived"] is False
    for edge, record in zip(graph.segments, document["segments"]):
        np.testing.assert_array_equal(edge.points, record["points_mm"])
        assert record["points_mm"][0] == document["nodes"][record["start"]]
        assert record["points_mm"][-1] == document["nodes"][record["end"]]


def test_reject_broken_junction_and_disconnection():
    graph = generate()
    graph.segments[0].points[0, 0] += 1
    with pytest.raises(ValueError, match="endpoints"):
        graph.validate()
    graph = generate()
    graph.nodes["isolated"] = np.zeros(3)
    with pytest.raises(ValueError, match="Disconnected"):
        graph.validate()
    with pytest.raises(ValueError, match="Unknown"):
        generate().route("missing", "left_mca")
