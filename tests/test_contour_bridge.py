from copy import deepcopy

import numpy as np
import pytest

from vv_toolbox.contour_bridge import bridge_contours
from vv_toolbox.profile_loft import loft_source_profiles


def section(z):
    t = np.linspace(0, 2 * np.pi, 65)
    return dict(status="MEASURED", index=0, normal=[0., 0., 1.],
                contour_xyz_mm=np.column_stack(
                    [2*np.cos(t), np.sin(t), np.full_like(t, z)]).tolist())


def test_endpoints_derivatives_and_source_preserved():
    a, b = section(0), section(20)
    before = deepcopy([a, b])
    mesh, report = bridge_contours(a, b, samples=64, stations=40)
    pair = deepcopy([a, b]); pair[1]["index"] = 1
    endpoints, _ = loft_source_profiles(pair, samples=64)
    assert np.allclose(mesh.vertices[:64], endpoints.vertices[:64])
    assert np.allclose(mesh.vertices[-64:], endpoints.vertices[-64:])
    assert [a, b] == before
    assert report["endpoint_derivative_error"] < 1e-10
    assert mesh.extents == pytest.approx([4, 2, 20])
    assert not mesh.is_watertight and mesh.is_winding_consistent


def test_reversed_direction_rejected():
    with pytest.raises(ValueError, match="normals"):
        bridge_contours(section(20), section(0))


def test_unknown_contour_rejected():
    a = section(0); a["status"] = "UNKNOWN"
    with pytest.raises(ValueError):
        bridge_contours(a, section(20))


def test_corner_preservation_for_different_irregular_contours():
    a,b=section(0),section(20)
    for profile,xy in [(a,[[0,0],[3,0],[2,1],[0,2],[0,0]]),
                       (b,[[0,0],[2,0],[3,1],[1,3],[0,1],[0,0]])]:
        z=profile["contour_xyz_mm"][0][2]
        profile["contour_xyz_mm"]=[[x,y,z] for x,y in xy]
    mesh,report=bridge_contours(a,b,samples=13,preserve_source_corners=True)
    count=report["perimeter_samples"]
    for original,ring in [(a,mesh.vertices[:count]),(b,mesh.vertices[-count:])]:
        for vertex in original["contour_xyz_mm"]:
            assert np.min(np.linalg.norm(ring-vertex,axis=1))<1e-12
