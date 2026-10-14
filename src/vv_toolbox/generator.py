"""Editable synthetic topology layered over authored smooth trunk centerlines."""
import math
from collections.abc import Mapping

import numpy as np
from scipy.interpolate import CubicSpline
from scipy.optimize import brentq, minimize_scalar

from .model import Segment, VesselGraph, _generate_base
from .morphometry import arch_height_ratio as measure_arch_height_ratio,arch_type_for_ratio

ARCH_VARIANTS = ("standard", "common_origin", "left_carotid_from_brachiocephalic", "left_vertebral_from_arch")
COMMUNICATORS = ("acom", "left_pcom", "right_pcom")


def generate_network(radius_scale=1.0, tortuosity=0.3, samples=64, *, vessel_parameters=None,
                     arch_height_ratio=0.5, arch_variant="standard", absent_communicators=()):
    base = _generate_base(radius_scale, tortuosity, samples)  # Validate established ranges.
    if not math.isfinite(arch_height_ratio) or not 0.25 <= arch_height_ratio <= 3.5:
        raise ValueError("arch_height_ratio must be finite in [0.25,3.5]")
    if arch_variant not in ARCH_VARIANTS:
        raise ValueError("Unknown arch variant")
    if isinstance(absent_communicators, str) or not isinstance(absent_communicators, (tuple,list)) or any(x not in COMMUNICATORS for x in absent_communicators):
        raise ValueError("Unknown absent communicator")
    if len(set(absent_communicators)) != len(absent_communicators):
        raise ValueError("Duplicate absent communicator")
    if vessel_parameters is None:
        vessel_parameters = {}
    if not isinstance(vessel_parameters, Mapping):
        raise ValueError("vessel_parameters must be a mapping")
    overrides = {}
    for name, values in vessel_parameters.items():
        if not isinstance(values, Mapping) or set(values)-{"radius_scale","tortuosity"}:
            raise ValueError("Unknown vessel parameter")
        overrides[name] = {}
        for key,value in values.items():
            low,high = (0.5,2) if key == "radius_scale" else (0,1)
            if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or not low <= value <= high:
                raise ValueError(f"Invalid vessel parameter {key}")
            overrides[name][key] = float(value)
    # Baselines are independent of global/local geometry controls.
    base = _generate_base(1.0,0.0,max(64,samples))
    nodes = {key:value.copy() for key,value in base.nodes.items()}
    originals = {edge.name:edge for edge in base.segments}
    edges = {}
    def add(name,start,end,radius,points=None):
        if points is None:
            points = np.linspace(nodes[start],nodes[end],samples)
        edges[name] = (start,end,float(radius),np.asarray(points))
    def smooth_chain(names, ids, radii):
        coordinates = np.array([nodes[name] for name in names])
        q = np.r_[0,np.cumsum(np.linalg.norm(np.diff(coordinates,axis=0),axis=1))]
        spline = CubicSpline(q,coordinates,axis=0,bc_type="natural")
        for i,name in enumerate(ids):
            add(name,names[i],names[i+1],radii[i],spline(np.linspace(q[i],q[i+1],samples)))

    # One underlying round trunk remains fixed while origin locations slide along it.
    trunk_ids = ["abdominal_aorta","thoracic_aorta","distal_arch","aortic_arch","ascending_aorta"]
    points = np.concatenate([originals[name].points[:-1] for name in trunk_ids]+[originals[trunk_ids[-1]].points[-1:]])
    q = np.r_[0,np.cumsum(np.linalg.norm(np.diff(points,axis=0),axis=1))]
    trunk = CubicSpline(q,points,axis=0)
    anchor = {"aortic_bifurcation":0.0}
    index = 0
    for name in trunk_ids:
        index += len(originals[name].points)-1
        anchor[originals[name].end] = float(q[index])
    crown_q = minimize_scalar(lambda value:-float(trunk(value)[2]),bounds=(anchor["arch_left"],anchor["arch_right"]),method="bounded").x
    crown_z = float(trunk(crown_q)[2])
    nominal_cca_diameter = 7.0
    origin_z = crown_z-arch_height_ratio*nominal_cca_diameter
    bt_q = brentq(lambda value:float(trunk(value)[2])-origin_z,crown_q,anchor["arch_right"])
    anchor["arch_right"] = bt_q
    anchor["arch_carotid_origin"] = anchor["arch_left"]+0.65*(crown_q-anchor["arch_left"])
    anchor["arch_vertebral_origin"] = anchor["arch_left"]+0.3*(crown_q-anchor["arch_left"])
    for name,fraction in [("ima_origin",0.32),("renal_origin",0.58),("sma_origin",0.75),("celiac_origin",0.91)]:
        anchor[name] = fraction*anchor["abdominal_aorta"]
    trunk_names = ["aortic_bifurcation","ima_origin","renal_origin","sma_origin","celiac_origin","abdominal_aorta","descending_aorta","arch_left","arch_vertebral_origin","arch_carotid_origin","arch_right","ascending_aorta"]
    segment_names = ["abdominal_aorta","abdominal_aorta_renal","abdominal_aorta_sma","abdominal_aorta_celiac","abdominal_aorta_upper","thoracic_aorta","distal_arch","aortic_arch","aortic_arch_middle","aortic_arch_proximal","ascending_aorta"]
    radii = [10,10,10,10,10,12,13,13,13,13,13]
    for name in trunk_names:
        nodes[name] = trunk(anchor[name])
    for i,name in enumerate(segment_names):
        add(name,trunk_names[i],trunk_names[i+1],radii[i],trunk(np.linspace(anchor[trunk_names[i]],anchor[trunk_names[i+1]],samples)))
    add("brachiocephalic","arch_right","brachiocephalic",7)
    add("basilar","basilar_origin","basilar_tip",2)

    for side in ("left","right"):
        for suffix in ("femoral_iliac","common_iliac"):
            old = originals[f"{side}_{suffix}"]
            resampled = CubicSpline(np.linspace(0,1,len(old.points)),old.points,axis=0)(np.linspace(0,1,samples))
            add(old.name,old.start,old.end,old.radius_mm,resampled)
        carotid_origin = "brachiocephalic"
        if side == "left":
            carotid_origin = {"standard":"arch_carotid_origin", "common_origin":"arch_right", "left_carotid_from_brachiocephalic":"brachiocephalic", "left_vertebral_from_arch":"arch_carotid_origin"}[arch_variant]
        smooth_chain([carotid_origin,f"{side}_carotid",f"{side}_ica"], [f"{side}_common_carotid",f"{side}_internal_carotid"],[3.5,2.4])
        subclavian_origin = "arch_left" if side == "left" else "brachiocephalic"
        if side == "left" and arch_variant == "left_vertebral_from_arch":
            add("left_subclavian",subclavian_origin,"left_subclavian",4)
            smooth_chain(["arch_vertebral_origin","left_vertebral","basilar_origin"], ["left_vertebral_proximal","left_vertebral_distal"],[1.8,1.7])
        else:
            smooth_chain([subclavian_origin,f"{side}_subclavian",f"{side}_vertebral","basilar_origin"], [f"{side}_subclavian",f"{side}_vertebral_proximal",f"{side}_vertebral_distal"],[4,1.8,1.7])
        for artery,prefix,old_suffix in [("aca","a","anterior_cerebral"),("mca","m","middle_cerebral"),("pca","p","posterior_cerebral")]:
            old = originals[f"{side}_{old_suffix}"]
            first,second = f"{side}_{prefix}1_end",f"{side}_{prefix}2_end"
            nodes[first] = old.points[0]+0.35*(old.points[-1]-old.points[0])
            nodes[second] = old.points[0]+0.70*(old.points[-1]-old.points[0])
            smooth_chain([old.start,first,second,old.end], [f"{side}_{artery}_{prefix}{i}" for i in (1,2,3)], [old.radius_mm]*3)
    if "acom" not in absent_communicators:
        add("acom","left_a1_end","right_a1_end",1.0)
    for side in ("left","right"):
        if f"{side}_pcom" not in absent_communicators:
            add(f"{side}_pcom",f"{side}_ica",f"{side}_p1_end",1.0)

    # Schematic abdominal arteries; SA denotes splenic artery here.
    abdominal_nodes = {"celiac_trunk":(-5,-30,float(nodes["celiac_origin"][2])+8),
                      "splenic":(90,-10,365),"common_hepatic":(-75,-25,355),"left_gastric":(20,-55,385),
                      "superior_mesenteric":(5,-65,245),"left_renal":(75,5,280),"right_renal":(-75,5,280),
                      "inferior_mesenteric":(15,-45,205)}
    nodes.update({key:np.array(value,dtype=float) for key,value in abdominal_nodes.items()})
    for name,start,end,radius in [("celiac_trunk","celiac_origin","celiac_trunk",3.5),
                                 ("splenic_artery","celiac_trunk","splenic",2.5),
                                 ("common_hepatic","celiac_trunk","common_hepatic",2.5),
                                 ("left_gastric","celiac_trunk","left_gastric",1.5),
                                 ("superior_mesenteric","sma_origin","superior_mesenteric",3),
                                 ("left_renal","renal_origin","left_renal",2.5),
                                 ("right_renal","renal_origin","right_renal",2.5),
                                 ("inferior_mesenteric","ima_origin","inferior_mesenteric",1.5)]:
        add(name,start,end,radius)

    unknown = set(overrides)-set(edges)-set(COMMUNICATORS)
    if unknown:
        raise ValueError("Unknown vessel segment: "+", ".join(sorted(unknown)))
    segments = []
    t = np.linspace(0,1,samples)
    for name,(start,end,radius,baseline) in edges.items():
        local = overrides.get(name,{})
        local_radius = local.get("radius_scale",radius_scale)
        local_tortuosity = local.get("tortuosity",tortuosity)
        a,b = nodes[start],nodes[end]
        direction = (b-a)/np.linalg.norm(b-a)
        normal = np.cross(direction,np.eye(3)[np.argmin(np.abs(direction))])
        normal /= np.linalg.norm(normal)
        binormal = np.cross(direction,normal)
        amplitude = min(np.linalg.norm(b-a)*0.12,18)*local_tortuosity
        offset = amplitude*np.sin(np.pi*t)[:,None]**2*(np.sin(2*np.pi*t)[:,None]*normal+0.5*np.sin(np.pi*t)[:,None]*binormal)
        points = baseline+offset
        points[0],points[-1] = a,b
        segments.append(Segment(name,start,end,points,radius*local_radius))
    # The clinical definition uses a luminal top/origin distance. Ours is explicitly
    # a centerline surrogate and nominal-reference construction, not clinical typing.
    actual_cca_diameter = 2*next(edge.radius_mm for edge in segments if edge.name == "left_common_carotid")
    trunk_set = set(segment_names)
    actual_top = max(float(edge.points[:,2].max()) for edge in segments if edge.name in trunk_set)
    measured_trunk=[edge for edge in segments if edge.name in trunk_set]
    measured=measure_arch_height_ratio(np.concatenate([edge.points[:-1] for edge in measured_trunk]+[measured_trunk[-1].points[-1:]]),nodes['arch_right'],actual_cca_diameter)
    measurements = {"kind":"synthetic-centerline-surrogate", "clinical_classification":False,
                    "requested_ratio":arch_height_ratio,"construction_reference_cca_diameter_mm":nominal_cca_diameter,
                    "left_cca_diameter_mm":actual_cca_diameter,"arch_top_centerline_z_mm":actual_top,
                    "innominate_origin_centerline_z_mm":float(nodes["arch_right"][2]),
                    "measured_centerline_ratio":(actual_top-float(nodes["arch_right"][2]))/actual_cca_diameter}
    measurements.update(requested_type=arch_type_for_ratio(arch_height_ratio),measured_type=measured['surrogate_type'],
                        type_mismatch=arch_type_for_ratio(arch_height_ratio)!=measured['surrogate_type'],
                        type_boundaries=measured['boundaries'],landmark_definition='Centerline top and centerline innominate origin; not verified luminal landmarks')
    definitions={}
    fractions=(0.,.35,.70,1.)
    for side in ('left','right'):
        for artery,prefix in (('aca','a'),('mca','m'),('pca','p')):
            for index in (1,2,3):
                definitions[f'{side}_{artery}_{prefix}{index}']={
                    'status':'ESTIMATED_SUBDIVISION','source_annotated':False,'anatomical_landmarks_validated':False,
                    'method':'Authored fractional subdivisions of an illustrative centerline; not an anatomical annotation protocol',
                    'fraction_basis':'Original endpoint chord; not arc length or verified anatomical boundaries',
                    'fraction_interval':[fractions[index-1],fractions[index]],
                    'limitation':'The original 0.35/0.70 fractional split is invalid as a verified anatomical segmentation; A1/A2/A3, M1/M2/M3 and P1/P2/P3 boundaries require source labels or validated anatomical landmarks'}
    parameters = {"radius_scale":radius_scale,"tortuosity":tortuosity,"samples":samples,
                  "vessel_parameters":overrides,"arch_height_ratio":arch_height_ratio,"arch_variant":arch_variant,
                  "absent_communicators":list(absent_communicators),"arch_measurement":measurements,
                  "segment_definitions":definitions}
    graph = VesselGraph(nodes,segments,parameters)
    graph.validate()
    return graph
