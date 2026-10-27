"""Estimated open bridges anchored to measured noncircular endpoint contours."""
from copy import deepcopy

import numpy as np
import trimesh
from scipy.interpolate import CubicHermiteSpline

from .profile_loft import loft_source_profiles


def bridge_contours(start, end, *, stations=96, samples=64, preserve_source_corners=False):
    """Interpolate paired perimeter points with endpoint-normal derivatives.

    End rings are perimeter-resampled source contours. Between their vertices,
    mesh edges are chords; this is not an exact source union or junction model.
    """
    if type(stations) is not int or not 3 <= stations <= 1000:
        raise ValueError("3–1000 longitudinal stations required")
    profiles = deepcopy([start, end])
    for i, profile in enumerate(profiles):
        profile["index"] = i
    endpoints, _ = loft_source_profiles(profiles, samples=samples)
    rings = np.asarray(endpoints.vertices).reshape(2, samples, 3)
    if preserve_source_corners:
        polygons=[];arcs=[]
        for i,profile in enumerate(profiles):
            xyz=np.asarray(profile["contour_xyz_mm"],dtype=float)[:-1].copy()
            normal=np.asarray(profile["normal"])
            area=np.cross(xyz-xyz[0],np.roll(xyz,-1,axis=0)-xyz[0]).sum(axis=0)
            if area@normal<0:
                xyz=xyz[::-1]
            seam=int(np.argmin(np.linalg.norm(xyz-rings[i,0],axis=1)))
            xyz=np.roll(xyz,-seam,axis=0)
            xyz=np.vstack([xyz,xyz[0]])
            arc=np.r_[0.,np.cumsum(np.linalg.norm(np.diff(xyz,axis=0),axis=1))]
            polygons.append(xyz);arcs.append(arc/arc[-1])
        # Both polygons retain every corner using a shared arclength grid.
        fractions=np.unique(np.concatenate([np.arange(samples)/samples,*[a[:-1] for a in arcs]]))
        rings=np.array([np.column_stack([np.interp(fractions,arc,xyz[:,k]) for k in range(3)])
                        for arc,xyz in zip(arcs,polygons)])
        samples=len(fractions)
    normals = np.array([p["normal"] for p in profiles], dtype=float)
    delta = rings[1].mean(axis=0) - rings[0].mean(axis=0)
    length = float(np.linalg.norm(delta))
    if length <= 1e-8 or np.any(normals @ delta <= 0):
        raise ValueError("Endpoint normals must point along the bridge")
    derivatives = np.broadcast_to(normals[:, None, :] * length, rings.shape)
    spline = CubicHermiteSpline([0., 1.], rings, derivatives, axis=0)
    t = np.linspace(0., 1., stations)
    vertices = spline(t).reshape(-1, 3)
    faces = []
    for j in range(stations - 1):
        for k in range(samples):
            a = j * samples + k
            b = j * samples + (k + 1) % samples
            faces.extend([[a, b, b + samples], [a, b + samples, a + samples]])
    mesh = trimesh.Trimesh(vertices, np.asarray(faces), process=False)
    if np.any(mesh.area_faces <= 1e-12) or not mesh.is_winding_consistent:
        raise ValueError("Invalid bridge triangles")
    return mesh, dict(
        method="measured-contour-hermite-bridge/1", status="CANDIDATE",
        stations=stations, perimeter_samples=samples,
        endpoint_derivative_error=float(np.max(np.abs(spline([0., 1.], 1) - derivatives))),
        source_modified=False, endpoint_policy=("all source corners retained with shared perimeter stations"
                         if preserve_source_corners else "perimeter resampling with chord edges"),
        self_intersection="NOT RUN", source_union="NOT RUN",
        neighboring_vessels="NOT RUN", anatomical_validation="NOT RUN")
