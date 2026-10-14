"""Deterministic illustrative topology. Coordinates are LPS-like: +x left, +y posterior, +z superior."""
from dataclasses import dataclass
import heapq
import json
import math

import numpy as np
from scipy.interpolate import CubicSpline


@dataclass(frozen=True)
class Segment:
    name: str
    start: str
    end: str
    points: np.ndarray
    radius_mm: float
    radius_profile_mm: np.ndarray | None = None

    def __post_init__(self):
        if self.radius_profile_mm is not None:
            profile=np.asarray(self.radius_profile_mm,dtype=float)
            if profile.ndim!=1 or len(profile)!=len(self.points) or not np.isfinite(profile).all() or np.any(profile<=0):
                raise ValueError('Radius profile must have one finite positive value per centerline point')
            object.__setattr__(self,'radius_profile_mm',profile.copy())

    @property
    def length_mm(self):
        return float(np.linalg.norm(np.diff(self.points, axis=0), axis=1).sum())


@dataclass
class VesselGraph:
    nodes: dict[str, np.ndarray]
    segments: list[Segment]
    parameters: dict
    provenance: dict | None = None
    coordinates: str = "+x subject-left; +y posterior; +z superior; arbitrary origin"
    nonrendered_links: list[dict] | None = None

    def generation_kwargs(self):
        """Serializable inputs suitable for generate(**kwargs), excluding measurements."""
        return {key:self.parameters[key] for key in ("radius_scale","tortuosity","samples","vessel_parameters","arch_height_ratio","arch_variant","absent_communicators") if key in self.parameters}

    def validate(self):
        if self.provenance is not None and not isinstance(self.provenance,dict):
            raise ValueError('Provenance must be a dictionary')
        if not isinstance(self.coordinates,str) or not self.coordinates.strip():
            raise ValueError('Coordinate description must be nonempty')
        if not self.nodes or not self.segments:
            raise ValueError("Graph must contain nodes and segments")
        for point in self.nodes.values():
            if np.shape(point) != (3,) or not np.isfinite(point).all():
                raise ValueError("Invalid node coordinate")
        adjacency = {key: set() for key in self.nodes}
        names = set()
        for edge in self.segments:
            if edge.name in names or edge.start not in self.nodes or edge.end not in self.nodes:
                raise ValueError("Duplicate segment or unknown endpoint")
            names.add(edge.name)
            if edge.start == edge.end or edge.points.ndim != 2 or edge.points.shape[1] != 3 or len(edge.points) < 2:
                raise ValueError("Invalid segment shape")
            if not np.isfinite(edge.points).all() or not math.isfinite(edge.radius_mm) or edge.radius_mm <= 0:
                raise ValueError("Invalid segment geometry")
            if edge.radius_profile_mm is not None:
                profile=np.asarray(edge.radius_profile_mm)
                if profile.ndim!=1 or len(profile)!=len(edge.points) or not np.isfinite(profile).all() or np.any(profile<=0):
                    raise ValueError('Invalid radius profile')
            if not np.array_equal(edge.points[0], self.nodes[edge.start]) or not np.array_equal(edge.points[-1], self.nodes[edge.end]):
                raise ValueError("Segment endpoints must match junctions exactly")
            if np.any(np.linalg.norm(np.diff(edge.points, axis=0), axis=1) <= 0):
                raise ValueError("Degenerate segment")
            adjacency[edge.start].add(edge.end)
            adjacency[edge.end].add(edge.start)
        if self.nonrendered_links is not None:
            if not isinstance(self.nonrendered_links,list):
                raise ValueError('Nonrendered links must be a list')
            linked=set()
            for link in self.nonrendered_links:
                if not isinstance(link,dict) or set(link)!={'start','end','kind','chamber','render_as_vessel'}:
                    raise ValueError('Invalid nonrendered chamber link')
                a,b=link['start'],link['end']
                if (not isinstance(a,str) or not isinstance(b,str) or a not in adjacency or b not in adjacency or a==b
                    or link['kind']!='unmodeled_chamber' or link['chamber']!='right_atrium' or link['render_as_vessel'] is not False):
                    raise ValueError('Invalid nonrendered chamber link')
                pair=frozenset((a,b))
                if pair in linked or not adjacency[a] or not adjacency[b]:
                    raise ValueError('Duplicate chamber link or orphan endpoint')
                linked.add(pair)
                adjacency[a].add(b)
                adjacency[b].add(a)
        seen, pending = set(), [next(iter(self.nodes))]
        while pending:
            node = pending.pop()
            if node not in seen:
                seen.add(node)
                pending.extend(adjacency[node] - seen)
        if seen != set(self.nodes):
            raise ValueError("Disconnected graph")

    def route(self, start: str, target: str) -> tuple[list[str], float]:
        """Shortest undirected centerline route; not a blood-flow calculation."""
        if start not in self.nodes or target not in self.nodes:
            raise ValueError("Unknown route endpoint")
        adjacency = {key: [] for key in self.nodes}
        for edge in self.segments:
            adjacency[edge.start].append((edge.end, edge))
            adjacency[edge.end].append((edge.start, edge))
        queue = [(0.0, start, [])]
        visited = set()
        while queue:
            length, node, path = heapq.heappop(queue)
            if node in visited:
                continue
            if node == target:
                return path, length
            visited.add(node)
            for other, edge in adjacency[node]:
                if other not in visited:
                    heapq.heappush(queue, (length + edge.length_mm, other, path + [edge.name]))
        raise ValueError("No route exists")

    def to_json(self):
        self.validate()
        return json.dumps({
            "schema": "vv-toolbox.graph/1", "units": "mm",
            "coordinates": self.coordinates,
            "provenance": self.provenance if self.provenance is not None else {"kind": "synthetic-illustrative", "generator": "vv-toolbox/0.1.0", "patient_derived": False, "anatomy_validated": False},
            "parameters": self.parameters,
            "nonrendered_links": self.nonrendered_links or [],
            "nodes": {key: value.tolist() for key, value in self.nodes.items()},
            "segments": [{"id": edge.name, "start": edge.start, "end": edge.end, "radius_mm": edge.radius_mm, "points_mm": edge.points.tolist(),
                          **({"radius_profile_mm":edge.radius_profile_mm.tolist()} if edge.radius_profile_mm is not None else {})} for edge in self.segments],
        }, indent=2, allow_nan=False)


def _generate_base(radius_scale=1.0, tortuosity=0.3, samples=64):
    """Create a connected schematic tree with a vertebrobasilar loop.

    All values are author-chosen illustration parameters, not population estimates.
    Perturbations vanish at junctions. No cerebral communicating arteries are modeled.
    """
    if not math.isfinite(radius_scale) or not 0.5 <= radius_scale <= 2:
        raise ValueError("radius_scale must be finite in [0.5, 2]")
    if not math.isfinite(tortuosity) or not 0 <= tortuosity <= 1:
        raise ValueError("tortuosity must be finite in [0, 1]")
    if isinstance(samples, bool) or not isinstance(samples, int) or not 8 <= samples <= 1024:
        raise ValueError("samples must be an integer in [8, 1024]")
    nodes = {
        "aortic_bifurcation": (0, 0, 180), "abdominal_aorta": (0, 15, 350),
        "descending_aorta": (28, 30, 520), "arch_left": (32, 20, 626),
        "arch_right": (-35, -5, 628), "ascending_aorta": (-42, -25, 550),
        "brachiocephalic": (-45, -5, 670), "basilar_origin": (0, 30, 845),
        "basilar_tip": (0, 20, 895),
    }
    edges = [
        ("abdominal_aorta", "aortic_bifurcation", "abdominal_aorta", 10),
        ("thoracic_aorta", "abdominal_aorta", "descending_aorta", 12),
        ("distal_arch", "descending_aorta", "arch_left", 13),
        ("aortic_arch", "arch_left", "arch_right", 13),
        ("ascending_aorta", "arch_right", "ascending_aorta", 13),
        ("brachiocephalic", "arch_right", "brachiocephalic", 7),
        ("basilar", "basilar_origin", "basilar_tip", 2),
    ]
    for side, sign in [("left", 1), ("right", -1)]:
        def n(key):
            return f"{side}_{key}"
        nodes.update({n("femoral"): (sign*90, -10, 0), n("iliac"): (sign*55, 0, 100),
                      n("subclavian"): (sign*75, 5, 660), n("carotid"): (sign*37, -10, 790),
                      n("ica"): (sign*25, 0, 885), n("mca"): (sign*88, -5, 920),
                      n("aca"): (sign*10, -40, 938), n("vertebral"): (sign*22, 35, 800),
                      n("pca"): (sign*62, 50, 920)})
        origin = "arch_left" if side == "left" else "brachiocephalic"
        edges.extend([(n("femoral_iliac"), n("femoral"), n("iliac"), 4),
                      (n("common_iliac"), n("iliac"), "aortic_bifurcation", 5),
                      (n("common_carotid"), origin, n("carotid"), 3.5),
                      (n("internal_carotid"), n("carotid"), n("ica"), 2.4),
                      (n("middle_cerebral"), n("ica"), n("mca"), 1.5),
                      (n("anterior_cerebral"), n("ica"), n("aca"), 1.2),
                      (n("subclavian"), origin, n("subclavian"), 4),
                      (n("vertebral_proximal"), n("subclavian"), n("vertebral"), 1.8),
                      (n("vertebral_distal"), n("vertebral"), "basilar_origin", 1.7),
                      (n("posterior_cerebral"), "basilar_tip", n("pca"), 1.3)])
    nodes = {key: np.array(value, dtype=float) for key, value in nodes.items()}
    # Fit whole anatomical chains before splitting edges. Shared derivatives remove
    # the angular joins that independent per-edge curves cannot repair by meshing.
    smooth_edges = {}
    def chain(names, extra=None, boundary="natural"):
        coordinates = [nodes[name] for name in names]
        if extra:
            coordinates.insert(extra[0], np.array(extra[1], dtype=float))
        coordinates = np.array(coordinates)
        parameter = np.r_[0,np.cumsum(np.linalg.norm(np.diff(coordinates,axis=0),axis=1))]
        spline = CubicSpline(parameter, coordinates, axis=0, bc_type=boundary)
        node_parameters = list(parameter)
        if extra:
            node_parameters.pop(extra[0])
        for i in range(len(names)-1):
            smooth_edges[(names[i],names[i+1])] = spline(np.linspace(node_parameters[i],node_parameters[i+1],samples))
        return spline
    trunk_names = ["aortic_bifurcation","abdominal_aorta","descending_aorta","arch_left","arch_right","ascending_aorta"]
    trunk = chain(trunk_names, extra=(4,(-2,10,667)))
    incoming = trunk(0,1)
    incoming /= np.linalg.norm(incoming)
    for side in ("left","right"):
        chain([f"{side}_femoral",f"{side}_iliac","aortic_bifurcation"],
              boundary=((1,np.array([0.,0.,1.])),(1,incoming)))
        origin = "arch_left" if side == "left" else "brachiocephalic"
        chain([origin,f"{side}_carotid",f"{side}_ica"])
        chain([origin,f"{side}_subclavian",f"{side}_vertebral","basilar_origin"])
    t = np.linspace(0, 1, samples)
    segments = []
    for name, start, end, radius in edges:
        a, b = nodes[start], nodes[end]
        direction = (b-a) / np.linalg.norm(b-a)
        reference = np.eye(3)[np.argmin(np.abs(direction))]
        normal = np.cross(direction, reference)
        normal /= np.linalg.norm(normal)
        binormal = np.cross(direction, normal)
        amplitude = min(np.linalg.norm(b-a)*0.12, 18)*tortuosity
        # Window has zero value AND derivative at both ends, preserving chain tangents.
        window = np.sin(np.pi*t)**2
        offset = amplitude*window[:,None]*(np.sin(2*np.pi*t)[:, None]*normal + 0.5*np.sin(np.pi*t)[:, None]*binormal)
        if (start,end) in smooth_edges:
            baseline = smooth_edges[(start,end)]
        elif (end,start) in smooth_edges:
            baseline = smooth_edges[(end,start)][::-1]
        else:
            baseline = a[None, :] + t[:, None]*(b-a)
        points = baseline + offset
        points[0], points[-1] = a, b
        segments.append(Segment(name, start, end, points, radius*radius_scale))
    graph = VesselGraph(nodes, segments, {"radius_scale": radius_scale, "tortuosity": tortuosity, "samples": samples})
    graph.validate()
    return graph


def generate(radius_scale=1.0, tortuosity=0.3, samples=64, *, vessel_parameters=None,
             arch_height_ratio=0.5, arch_variant="standard", absent_communicators=()):
    """Generate an editable synthetic graph; local scales override global scales."""
    from .generator import generate_network
    return generate_network(radius_scale, tortuosity, samples, vessel_parameters=vessel_parameters,
                            arch_height_ratio=arch_height_ratio, arch_variant=arch_variant,
                            absent_communicators=absent_communicators)


def tube_mesh(points, radius, sides=12):
    """Open-ended display tube, not a fused/watertight simulation surface."""
    points = np.asarray(points, dtype=float)
    if points.ndim != 2 or points.shape[1] != 3 or len(points) < 2 or not np.isfinite(points).all():
        raise ValueError("Tube points must be finite Nx3 coordinates")
    if not math.isfinite(radius) or radius <= 0 or isinstance(sides, bool) or not isinstance(sides, int) or sides < 3:
        raise ValueError("Tube radius must be positive and sides an integer >= 3")
    tangents = np.gradient(points, axis=0)
    lengths = np.linalg.norm(tangents, axis=1)
    if np.any(lengths < 1e-12) or np.any(np.linalg.norm(np.diff(points, axis=0), axis=1) < 1e-12):
        raise ValueError("Degenerate tube centerline")
    tangents /= lengths[:, None]
    normals = np.empty_like(tangents)
    previous = np.eye(3)[np.argmin(np.abs(tangents[0]))]
    for i, tangent in enumerate(tangents):
        # Transport the previous frame into the next normal plane.
        normal = previous - np.dot(previous, tangent)*tangent
        if np.linalg.norm(normal) < 1e-8:
            reference = np.eye(3)[np.argmin(np.abs(tangent))]
            normal = reference - np.dot(reference, tangent)*tangent
        normals[i] = previous = normal / np.linalg.norm(normal)
    binormals = np.cross(tangents, normals)
    angles = np.linspace(0, 2*np.pi, sides, endpoint=False)
    vertices = points[:, None, :] + radius*(np.cos(angles)[None, :, None]*normals[:, None, :] + np.sin(angles)[None, :, None]*binormals[:, None, :])
    faces = []
    for i in range(len(points)-1):
        for j in range(sides):
            a, b = i*sides+j, i*sides+(j+1)%sides
            faces.extend([(a, b, a+sides), (b, b+sides, a+sides)])
    return vertices.reshape(-1, 3).astype(np.float32), np.array(faces, dtype=np.uint32)
