"""Centre-sampled masks of explicit closed surfaces in a declared mm/LPS frame.

No centreline-to-surface inference, mesh repair, or anatomical classification is
performed. Membership is retained for every instance, including intersections.
"""
from dataclasses import dataclass
from copy import deepcopy
import math

import numpy as np
import trimesh


@dataclass(frozen=True)
class Grid:
    shape_zyx: tuple[int, int, int]
    spacing_xyz_mm: tuple[float, float, float]
    origin_xyz_mm: tuple[float, float, float]
    frame_id: str

    def __post_init__(self):
        if len(self.shape_zyx) != 3 or any(type(n) is not int or n <= 0 for n in self.shape_zyx):
            raise ValueError('shape_zyx requires three positive integers')
        for name, values in [('spacing', self.spacing_xyz_mm), ('origin', self.origin_xyz_mm)]:
            if len(values) != 3 or any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) for x in values):
                raise ValueError(f'{name} requires three finite numbers')
        if any(x <= 0 for x in self.spacing_xyz_mm) or not isinstance(self.frame_id, str) or not self.frame_id.strip():
            raise ValueError('positive spacing and a frame_id are required')

    @property
    def affine_xyz(self):
        """Map homogeneous [x_index,y_index,z_index,1] to mm/LPS centres."""
        affine = np.diag([*self.spacing_xyz_mm, 1.0])
        affine[:3, 3] = self.origin_xyz_mm
        return affine


@dataclass(frozen=True)
class Surface:
    instance_id: int
    anatomical_label: int  # 0 = unknown, NOT inferred from proximity
    provenance: str  # source or estimated
    vertices_mm: np.ndarray
    faces: np.ndarray
    frame_id: str
    source_ref: str


@dataclass
class MaskVolume:
    grid: Grid
    foreground: np.ndarray
    anatomical: np.ndarray
    instance: np.ndarray
    provenance: np.ndarray
    overlap_count: np.ndarray
    membership: np.ndarray  # [instance,z,y,x], including all overlaps
    instances: list[dict]
    surface_tolerance_mm: float = 1e-8
    anatomical_registry: dict | None = None

    def metadata(self):
        return dict(schema='vv-toolbox.mask/1', frame_id=self.grid.frame_id,
                    units='mm', axes='LPS', array_order='zyx',
                    sampling='voxel_centres_surface_inclusive',
                    surface_tolerance_mm=self.surface_tolerance_mm,
                    checks={'closed_oriented_nondegenerate_surface': 'PASS',
                            'self_intersection': 'NOT RUN', 'clinical_validity': 'NOT RUN'},
                    shape_zyx=list(self.grid.shape_zyx),
                    spacing_xyz_mm=list(self.grid.spacing_xyz_mm),
                    voxel_xyz_to_world_mm=self.grid.affine_xyz.tolist(),
                    instance_policy='lowest_id_owner_with_all_memberships_retained',
                    anatomical_policy='0_unknown_or_conflicting_labels; foreground_separate',
                    provenance_codes={'background': 0, 'source': 1, 'estimated': 2, 'mixed': 3},
                    instances=self.instances,
                    anatomical_registry=deepcopy(self.anatomical_registry),
                    dtypes={k: str(getattr(self, k).dtype) for k in
                            ('foreground', 'anatomical', 'instance', 'provenance', 'overlap_count', 'membership')})


def _inside(points, triangles, tolerance, *, triangle_chunk=128):
    """Generalized winding of closed consistently oriented triangles, bounded chunks."""
    if type(triangle_chunk) is not int or triangle_chunk not in (32, 128):
        raise ValueError('Supported triangle batches are 32 and 128')
    angles = np.zeros(len(points))
    boundary = np.zeros(len(points), dtype=bool)
    for start in range(0, len(triangles), triangle_chunk):
        tri = triangles[start:start + triangle_chunk]
        a, b, c = (tri[None, :, i, :] - points[:, None, :] for i in range(3))
        la, lb, lc = (np.linalg.norm(v, axis=-1) for v in (a, b, c))
        numer = np.einsum('...i,...i->...', a, np.cross(b, c))
        denom = la * lb * lc + np.einsum('...i,...i->...', a, b) * lc + np.einsum('...i,...i->...', b, c) * la + np.einsum('...i,...i->...', c, a) * lb
        angle_chunk = 2 * np.arctan2(numer, denom)
        # Keep the original 32-triangle reduction and accumulation order.
        for offset in range(0, len(tri), 32):
            angles += np.sum(angle_chunk[:, offset:offset+32], axis=1)
        # Explicit plane and barycentric test includes triangle edges/vertices.
        u, v = tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]
        normal = np.cross(u, v)
        normal_length = np.linalg.norm(normal, axis=1)
        w = -a
        uu, uv, vv = np.sum(u*u, axis=1), np.sum(u*v, axis=1), np.sum(v*v, axis=1)
        wu, wv = np.einsum('pti,ti->pt', w, u), np.einsum('pti,ti->pt', w, v)
        determinant = normal_length**2
        s, t = (vv * wu - uv * wv) / determinant, (uu * wv - uv * wu) / determinant
        distance = np.abs(np.einsum('pti,ti->pt', w, normal)) / normal_length
        boundary |= np.any((distance <= tolerance) & (s >= -1e-12) & (t >= -1e-12) & (s+t <= 1+1e-12), axis=1)
    return boundary | (np.abs(angles) > 2 * np.pi)


def voxelize(surfaces, grid: Grid, *, max_bytes=256 * 1024**2, surface_tolerance_mm=1e-8):
    """Voxelize without optional spatial-index dependencies.

    Budget covers retained arrays, triangle copies and a conservative 8 MiB
    workspace allowance; caller-owned inputs and Python/library overhead excluded.
    This correctness-first O(voxels * faces) implementation suits bounded ROIs.
    """
    surfaces = list(surfaces)
    if not surfaces:
        raise ValueError('at least one surface is required')
    if type(max_bytes) is not int or max_bytes <= 0:
        raise ValueError('max_bytes must be a positive integer')
    if isinstance(surface_tolerance_mm, bool) or not isinstance(surface_tolerance_mm, (int, float)) or not math.isfinite(surface_tolerance_mm) or surface_tolerance_mm < 0:
        raise ValueError('invalid surface tolerance')
    ids = [s.instance_id for s in surfaces]
    if any(type(i) is not int or not 0 < i <= np.iinfo(np.uint32).max for i in ids) or len(set(ids)) != len(ids):
        raise ValueError('unique positive uint32 instance IDs required')
    surfaces.sort(key=lambda s: s.instance_id)
    nvox = math.prod(grid.shape_zyx)
    estimated = nvox * (22 + len(surfaces)) + sum(np.asarray(s.faces).size * 512 + np.asarray(s.vertices_mm).size * 32 for s in surfaces) + 8 * 1024**2
    if estimated > max_bytes:
        raise ValueError(f'mask memory budget exceeded: estimated {estimated} > {max_bytes}')
    triangles = []
    for surface in surfaces:
        if type(surface.anatomical_label) is not int or not 0 <= surface.anatomical_label <= np.iinfo(np.uint32).max:
            raise ValueError('anatomical label must be uint32, with 0 for unknown')
        if surface.frame_id != grid.frame_id or surface.provenance not in ('source', 'estimated') or not isinstance(surface.source_ref, str) or not surface.source_ref.strip():
            raise ValueError('frame, provenance or source reference invalid')
        vertices, faces = np.asarray(surface.vertices_mm), np.asarray(surface.faces)
        if vertices.ndim != 2 or vertices.shape[1] != 3 or vertices.dtype.kind not in 'ifu' or not np.isfinite(vertices).all():
            raise ValueError('finite Nx3 vertices required')
        if faces.ndim != 2 or faces.shape[1] != 3 or len(faces) < 4 or not np.issubdtype(faces.dtype, np.integer) or faces.min() < 0 or faces.max() >= len(vertices):
            raise ValueError('valid triangle vertex indices required')
        mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
        if not mesh.is_watertight or not mesh.is_winding_consistent or not mesh.is_volume or np.any(mesh.area_faces <= 0):
            raise ValueError('closed, outward oriented, nondegenerate volume required; no repair performed')
        triangles.append(vertices.astype(float)[faces])
    membership = np.zeros((len(surfaces), nvox), dtype=bool)
    # Allocate only 128 voxel coordinates at a time, even for a large grid.
    for row, tri in enumerate(triangles):
        lower, upper = tri.min(axis=(0, 1)) - surface_tolerance_mm, tri.max(axis=(0, 1)) + surface_tolerance_mm
        for start in range(0, nvox, 128):
            flat = np.arange(start, min(start + 128, nvox))
            zyx = np.column_stack(np.unravel_index(flat, grid.shape_zyx))
            points = zyx[:, ::-1] * grid.spacing_xyz_mm + grid.origin_xyz_mm
            active = np.all((points >= lower) & (points <= upper), axis=1)
            if active.any():
                membership[row, flat[active]] = _inside(points[active], tri, surface_tolerance_mm)
    owner = np.zeros(nvox, dtype=np.uint32)
    anatomy = np.zeros(nvox, dtype=np.uint32)
    provenance = np.zeros(nvox, dtype=np.uint8)
    count = np.zeros(nvox, dtype=np.uint32)
    for row, surface in enumerate(surfaces):
        mask = membership[row]
        first = mask & (count == 0)
        conflict = mask & (count > 0) & (anatomy != surface.anatomical_label)
        owner[first] = surface.instance_id
        anatomy[first] = surface.anatomical_label
        anatomy[conflict] = 0
        provenance[mask] |= 1 if surface.provenance == 'source' else 2
        count[mask] += 1
    shape = grid.shape_zyx
    return MaskVolume(grid, (count > 0).reshape(shape), anatomy.reshape(shape), owner.reshape(shape),
                      provenance.reshape(shape), count.reshape(shape), membership.reshape((len(surfaces), *shape)),
                      [dict(instance_id=s.instance_id, anatomical_label=s.anatomical_label,
                            provenance=s.provenance, source_ref=s.source_ref) for s in surfaces], float(surface_tolerance_mm))


def crop(volume: MaskVolume, start_zyx, stop_zyx, *, max_bytes=256 * 1024**2):
    """Copy a half-open index ROI, preserving voxel centres in the original frame."""
    if len(start_zyx) != 3 or len(stop_zyx) != 3 or any(type(a) is not int or type(b) is not int or not 0 <= a < b <= n for a, b, n in zip(start_zyx, stop_zyx, volume.grid.shape_zyx)):
        raise ValueError('invalid half-open crop bounds')
    required = math.prod(b-a for a, b in zip(start_zyx, stop_zyx)) * (14 + len(volume.instances))
    if type(max_bytes) is not int or max_bytes < required:
        raise ValueError('crop memory budget exceeded')
    index = tuple(slice(a, b) for a, b in zip(start_zyx, stop_zyx))
    origin = volume.grid.affine_xyz @ np.array([*start_zyx[::-1], 1])
    grid = Grid(tuple(b-a for a, b in zip(start_zyx, stop_zyx)), volume.grid.spacing_xyz_mm,
                tuple(origin[:3]), volume.grid.frame_id)
    return MaskVolume(grid, *(getattr(volume, key)[index].copy() for key in
                             ('foreground', 'anatomical', 'instance', 'provenance', 'overlap_count')),
                      volume.membership[(slice(None), *index)].copy(), [dict(x) for x in volume.instances], volume.surface_tolerance_mm,
                      deepcopy(volume.anatomical_registry))
