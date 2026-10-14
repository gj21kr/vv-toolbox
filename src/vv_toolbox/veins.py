"""Independent synthetic systemic and hepatic-portal venous networks.

No arterial state, viewer process, or server is modified by this module.
Coordinates follow the toolbox convention: mm, +x left, +y posterior, +z superior.
"""
from collections.abc import Mapping
from dataclasses import dataclass
import json
import math

import numpy as np
from scipy.interpolate import CubicSpline

from .model import Segment, VesselGraph


IMV_DRAINAGE = ("splenic", "superior_mesenteric", "confluence")
TRANSVERSE_DOMINANCE = ("balanced", "left", "right")


@dataclass
class VenousNetwork:
    systemic: VesselGraph
    portal: VesselGraph
    parameters: dict

    @property
    def graphs(self):
        """Render separately: hepatic sinusoids are not a direct venous tube."""
        return {"systemic_venous": self.systemic, "hepatic_portal": self.portal}

    def validate(self):
        self.systemic.validate()
        self.portal.validate()
        if set(self.systemic.nodes) & set(self.portal.nodes):
            raise ValueError("Portal and systemic compartments must remain separate")
        names = [edge.name for graph in self.graphs.values() for edge in graph.segments]
        if len(names) != len(set(names)):
            raise ValueError("Venous segment identifiers must be unique")

    def generation_kwargs(self):
        return json.loads(json.dumps(self.parameters, allow_nan=False))

    def to_json(self):
        self.validate()
        return json.dumps({
            "schema": "vv-toolbox.venous-network/1",
            "units": "mm",
            "coordinates": "+x subject-left; +y posterior; +z superior; arbitrary origin",
            "provenance": {"kind": "synthetic-illustrative", "patient_derived": False,
                           "anatomy_validated": False, "generator": "vv-toolbox.veins/1"},
            "parameters": self.generation_kwargs(),
            "networks": {name: json.loads(graph.to_json()) for name, graph in self.graphs.items()},
            "display_colors": {"systemic_venous": "#5082eb", "hepatic_portal": "#4db5f0"},
            "direction": "Segment start-to-end is schematic drainage, not simulated blood flow",
            "unmodeled_chambers": [{"id":"right_atrium","ostia":["ven_ivc_ostium","ven_svc_ostium"],
                                    "render_as_vessel":False,"geometry_modeled":False}],
            "unmodeled_exchange": {
                "kind": "hepatic_sinusoids",
                "portal_terminals": ["ven_portal_left_liver", "ven_portal_right_liver"],
                "systemic_sources": ["ven_left_hepatic_liver", "ven_middle_hepatic_liver", "ven_right_hepatic_liver"],
                "render_as_vessel": False,
            },
        }, indent=2, allow_nan=False)


def _number(value, low, high, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f"{name} must be finite in [{low}, {high}]")
    return float(value)


def generate_veins(radius_scale=1.0, tortuosity=0.3, samples=64, *,
                   vessel_parameters=None, imv_drainage="splenic",
                   transverse_dominance="balanced"):
    """Build schematic major veins; organ microcirculation and heart are omitted.

    Local radius scales are absolute baseline multipliers, matching arterial controls.
    All IDs start with ``ven_``. This function has no viewer/server side effects.
    """
    radius_scale = _number(radius_scale, 0.5, 2, "radius_scale")
    tortuosity = _number(tortuosity, 0, 1, "tortuosity")
    if isinstance(samples, bool) or not isinstance(samples, int) or not 8 <= samples <= 1024:
        raise ValueError("samples must be an integer in [8, 1024]")
    if imv_drainage not in IMV_DRAINAGE or transverse_dominance not in TRANSVERSE_DOMINANCE:
        raise ValueError("Unknown venous variation")
    vessel_parameters = {} if vessel_parameters is None else vessel_parameters
    if not isinstance(vessel_parameters, Mapping):
        raise ValueError("vessel_parameters must be a mapping")
    overrides = {}
    for name, settings in vessel_parameters.items():
        if not isinstance(name, str) or not isinstance(settings, Mapping) or set(settings) - {"radius_scale", "tortuosity"}:
            raise ValueError("Invalid vessel override")
        overrides[name] = {key: _number(value, 0.5 if key == "radius_scale" else 0, 2 if key == "radius_scale" else 1, key)
                           for key, value in settings.items()}

    # Authored coordinates: illustrative anatomy, not population measurements.
    # Local anterior/right caval and anterior portal corridors avoid penetration
    # of the default arterial fixture; no clearance is promised under overrides.
    nodes = {}
    records = {"systemic": [], "portal": []}

    def node(name, xyz):
        name = "ven_" + name
        point = np.asarray(xyz, dtype=float)
        if name in nodes and not np.array_equal(nodes[name], point):
            raise ValueError(f"Conflicting node {name}")
        nodes[name] = point
        return name

    def chain(system, names, ids, radii):
        keys = ["ven_" + name for name in names]
        coordinates = np.array([nodes[key] for key in keys])
        q = np.r_[0, np.cumsum(np.linalg.norm(np.diff(coordinates, axis=0), axis=1))]
        spline = CubicSpline(q, coordinates, axis=0, bc_type="natural")
        for i, name in enumerate(ids):
            points = spline(np.linspace(q[i], q[i+1], samples))
            points[0], points[-1] = coordinates[i], coordinates[i+1]
            records[system].append(("ven_" + name, keys[i], keys[i+1], radii[i], points))
        return spline,q

    for name, point in {
        "iliac_confluence": (-25, 14, 185), "ivc_renal": (-30, -8, 270),
        "ivc_hepatic": (-35, -8, 390), "right_atrium": (-55, -26, 505),
        "svc_lower": (-72, -40, 565), "svc_upper": (-72, -40, 620),
        "azygos_upper": (-75, 40, 550), "azygos_lower": (-28, 44, 300),
        "hemiazygos_lower": (25, 44, 315), "hemiazygos_cross": (25, 44, 450),
        "azygos_cross": (-29, 44, 450),
        "sss_front": (0, -65, 990), "sss_crown": (0, 0, 1020),
        "confluence": (0, 78, 958), "iss_front": (0, -28, 965),
        "deep_confluence": (0, 22, 948), "straight_origin": (0, 38, 950),
        "occipital_inferior": (0, 72, 905),
    }.items():
        node(name, point)
    # Preserve the authored caval paths, but remove the false tube through the
    # unmodeled atrium. Two independently capped ostia delimit an illustrative gap.
    caval_spline,caval_q=chain("systemic", ["iliac_confluence", "ivc_renal", "ivc_hepatic", "right_atrium", "svc_lower", "svc_upper"],
          ["ivc_infrarenal", "ivc_suprarenal", "ivc_hepatic", "svc_lower", "svc_upper"], [10, 11, 12, 10, 9])
    for index,ostium,interval in [(2,'ivc_ostium',(caval_q[2],caval_q[3]-24)),
                                  (3,'svc_ostium',(caval_q[3]+24,caval_q[4]))]:
        name,start,end,radius,_=records['systemic'][index]
        points=caval_spline(np.linspace(*interval,samples))
        if index==2:
            end=node(ostium,points[-1])
            points[0]=nodes[start]
        else:
            start=node(ostium,points[0])
            points[-1]=nodes[end]
        records['systemic'][index]=(name,start,end,radius,points)
    nodes.pop('ven_right_atrium')
    # Retain SVC drainage orientation while sharing the same geometric spline.
    for index in (3, 4):
        name, start, end, radius, points = records["systemic"][index]
        records["systemic"][index] = (name, end, start, radius, points[::-1].copy())
    chain("systemic", ["azygos_lower", "azygos_cross", "azygos_upper", "svc_lower"],
          ["azygos_lower", "azygos_upper", "azygos_arch"], [3, 3.5, 4])
    chain("systemic", ["hemiazygos_lower", "hemiazygos_cross", "azygos_cross"],
          ["hemiazygos", "hemiazygos_crossing"], [2.5, 2.5])
    chain("systemic", ["sss_front", "sss_crown", "confluence"], ["superior_sagittal_anterior", "superior_sagittal_posterior"], [3, 4])
    chain("systemic", ["iss_front", "straight_origin", "confluence"], ["inferior_sagittal", "straight_sinus"], [1.5, 3])
    chain("systemic", ["deep_confluence", "straight_origin"], ["great_cerebral_vein"], [2.5])
    chain("systemic", ["occipital_inferior", "confluence"], ["occipital_sinus"], [1.5])

    for side, sign in (("left", 1), ("right", -1)):
        n = lambda suffix: side + "_" + suffix
        for suffix, xyz in {
            "femoral_distal": (sign*100-12, 7, 0), "femoral_proximal": (sign*75-12, 15, 80),
            "iliac_junction": (sign*45-12, 20, 137), "pelvis": (sign*30-12, 38, 100),
            "profunda": (sign*118-12, 32, 24),
            "renal_hilum": (sign*88, -15, 282), "renal_junction": (sign*42, -15, 276),
            "adrenal": (sign*72, -6, 325), "gonadal": (sign*42, -8, 180),
            "axillary": (sign*142, -22, 628), "subclavian": (sign*83, -24, 638),
            "venous_angle": (sign*49, -40, 653), "jugular_neck": (sign*55, -16, 780),
            "jugular_bulb": (sign*40, 34, 868), "sigmoid_bend": (sign*58, 55, 913),
            "transverse_lateral": (sign*66, 77, 950),
            "cortical": (sign*68, -5, 1000), "deep_cerebral": (sign*20, -10, 952),
            "basal_cerebral": (sign*35, 8, 927), "cavernous": (sign*48, -32, 900),
        }.items():
            node(n(suffix), xyz)
        chain("systemic", [n("femoral_distal"), n("femoral_proximal"), n("iliac_junction"), "iliac_confluence"],
              [n("femoral"), n("external_iliac"), n("common_iliac")], [4, 5, 6])
        chain("systemic", [n("pelvis"), n("iliac_junction")], [n("internal_iliac")], [3.5])
        chain("systemic", [n("profunda"), n("femoral_proximal")], [n("profunda_femoris")], [3])
        chain("systemic", [n("renal_hilum"), n("renal_junction"), "ivc_renal"], [n("renal_lateral"), n("renal_medial")], [4.5, 5])
        for suffix, radius in (("gonadal", 1.5), ("adrenal", 1.5)):
            destination = n("renal_junction") if side == "left" else ("ivc_renal" if suffix == "gonadal" else "ivc_hepatic")
            chain("systemic", [n(suffix), destination], [n(suffix)], [radius])
        chain("systemic", [n("axillary"), n("subclavian"), n("venous_angle"), "svc_upper"],
              [n("axillary"), n("subclavian"), n("brachiocephalic")], [4.5, 5, 6])
        chain("systemic", [n("jugular_bulb"), n("jugular_neck"), n("venous_angle")],
              [n("internal_jugular_upper"), n("internal_jugular_lower")], [4, 5])
        dominance = 0.7 if transverse_dominance not in ("balanced", side) else 1.0
        chain("systemic", ["confluence", n("transverse_lateral"), n("sigmoid_bend"), n("jugular_bulb")],
              [n("transverse_sinus"), n("sigmoid_upper"), n("sigmoid_lower")], [3.5*dominance, 3.5*dominance, 3.5])
        chain("systemic", [n("cortical"), "sss_crown"], [n("superior_cortical")], [1.5])
        chain("systemic", [n("deep_cerebral"), "deep_confluence"], [n("internal_cerebral")], [1.5])
        chain("systemic", [n("basal_cerebral"), "deep_confluence"], [n("basal_cerebral")], [1.5])
        chain("systemic", [n("cavernous"), n("transverse_lateral")], [n("superior_petrosal")], [1.5])
        chain("systemic", [n("cavernous"), n("jugular_bulb")], [n("inferior_petrosal")], [1.5])
    # Cavernous compartment represented by a short vessel-like display connection.
    chain("systemic", ["left_cavernous", "right_cavernous"], ["intercavernous_sinus"], [1.5])
    for side, xyz in (("left", (15, -16, 420)), ("middle", (-42, -25, 420)), ("right", (-100, -16, 420))):
        node(side + "_hepatic_liver", xyz)
        chain("systemic", [side + "_hepatic_liver", "ivc_hepatic"], [side + "_hepatic_vein"], [4.5])

    for name, xyz in {
        "splenic_hilum": (112, -30, 372), "splenic_junction": (64, -35, 348),
        "portal_confluence": (7, -46, 338), "smv_inferior": (16, -40, 235),
        "smv_junction": (14, -43, 292), "imv_inferior": (67, -35, 220),
        "gastric": (60, -45, 390), "portal_hilum": (-34, -50, 370),
        "portal_left_liver": (0, -42, 405), "portal_right_liver": (-87, -42, 390),
    }.items():
        node(name, xyz)
    chain("portal", ["splenic_hilum", "splenic_junction", "portal_confluence"], ["splenic_distal", "splenic_proximal"], [4, 4.5])
    chain("portal", ["smv_inferior", "smv_junction", "portal_confluence"], ["superior_mesenteric_distal", "superior_mesenteric_proximal"], [4, 4.5])
    destination = {"splenic": "splenic_junction", "superior_mesenteric": "smv_junction", "confluence": "portal_confluence"}[imv_drainage]
    chain("portal", ["imv_inferior", destination], ["inferior_mesenteric"], [2.5])
    chain("portal", ["gastric", "portal_confluence"], ["left_gastric"], [2])
    chain("portal", ["portal_confluence", "portal_hilum"], ["portal_vein"], [6])
    chain("portal", ["portal_hilum", "portal_left_liver"], ["portal_left_branch"], [4])
    chain("portal", ["portal_hilum", "portal_right_liver"], ["portal_right_branch"], [4.5])

    known = {record[0] for group in records.values() for record in group}
    if set(overrides) - known:
        raise ValueError("Unknown venous segment override")
    parameters = {"radius_scale": radius_scale, "tortuosity": tortuosity, "samples": samples,
                  "vessel_parameters": overrides, "imv_drainage": imv_drainage,
                  "transverse_dominance": transverse_dominance}
    graphs = {}
    t = np.linspace(0, 1, samples)
    envelope = np.sin(np.pi*t)**2
    for system, group in records.items():
        segments = []
        used = set()
        for name, start, end, radius, base in group:
            setting = overrides.get(name, {})
            local_radius = setting.get("radius_scale", radius_scale)
            local_tortuosity = setting.get("tortuosity", tortuosity)
            direction = nodes[end] - nodes[start]
            length = np.linalg.norm(direction)
            unit = direction/length
            normal = np.cross(unit, np.eye(3)[np.argmin(np.abs(unit))])
            normal /= np.linalg.norm(normal)
            amplitude = min(0.045*length, 6.0)*local_tortuosity
            points = base + (amplitude*envelope*np.sin(2*np.pi*t))[:, None]*normal
            points[0], points[-1] = nodes[start], nodes[end]
            segments.append(Segment(name, start, end, points, radius*local_radius))
            used.update((start, end))
        graph_parameters = json.loads(json.dumps(parameters))
        graph_parameters.update({"circulation": system, "generator": "vv-toolbox.veins/1"})
        links=[{'start':'ven_ivc_ostium','end':'ven_svc_ostium','kind':'unmodeled_chamber',
                'chamber':'right_atrium','render_as_vessel':False}] if system=='systemic' else None
        graph = VesselGraph({key: nodes[key].copy() for key in sorted(used)}, segments, graph_parameters,nonrendered_links=links)
        graph.validate()
        graphs[system] = graph
    result = VenousNetwork(graphs["systemic"], graphs["portal"], parameters)
    result.validate()
    return result
