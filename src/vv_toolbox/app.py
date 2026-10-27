"""Loopback-only shared synthetic anatomy workspace."""
import argparse
import copy
import json
import math
import os
import threading
import time
from pathlib import Path
from functools import lru_cache
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import numpy as np
import viser
from .model import generate
from .surface import network_mesh
from .veins import generate_veins, IMV_DRAINAGE, TRANSVERSE_DOMINANCE
from .web_ui import HTML
from .clearance import cross_circuit_clearance
from .atlas_annotation_service import AnnotationStore, AnnotationConflict, require_renderable_frame
from .case_app_service import CaseWorkspace, CaseWorkspaceConflict
from .atlas_edit_session import AtlasEditSession, AtlasEditConflict, source_identity, regenerate
from .atlas_edit_checks import AtlasEditCheckFailure, require_self_contact_clearance

TARGETS = {f'{s.title()} {a.upper()}': f'{s}_{a}' for s in ('left','right') for a in ('mca','aca','pca')}
VARIANTS = ('standard','common_origin','left_carotid_from_brachiocephalic','left_vertebral_from_arch')
FOCUS = {'Whole network': ((.06,-.85,.52),(.06,0,.48)), 'Aortic arch': ((.035,-.20,.66),(.035,.01,.63)), 'Cerebral': ((.05,-.30,.92),(.05,.02,.90)), 'Femoral bifurcation': ((.07,-.4,.20),(.07,0,.15)), 'Abdominal': ((.08,-.50,.39),(.08,0,.38))}
LAYERS = ('arterial','systemic_venous','hepatic_portal')
LAYER_COLORS = {'arterial':(230,76,83),'systemic_venous':(80,130,235),'hepatic_portal':(77,181,240)}

def defaults():
    return dict(radius_scale=1.,tortuosity=.3,vessel_parameters={},arch_height_ratio=.5,arch_variant='standard',absent_communicators=[],
                venous=dict(radius_scale=1.,tortuosity=.3,samples=64,vessel_parameters={},imv_drainage='splenic',transverse_dominance='balanced'))

def validate_parameters(raw, known, known_venous=None):
    if not isinstance(raw,dict) or set(raw)!=set(defaults()):
        raise ValueError('Expected complete anatomy parameters')
    def number(v,lo,hi):
        if isinstance(v,bool) or not isinstance(v,(float,int)) or not math.isfinite(v) or not lo<=v<=hi:
            raise ValueError('Shape value out of range')
        return float(v)
    result=dict(radius_scale=number(raw['radius_scale'],.5,2),tortuosity=number(raw['tortuosity'],0,1),arch_height_ratio=number(raw['arch_height_ratio'],.25,3.5))
    if raw['arch_variant'] not in VARIANTS:
        raise ValueError('Unknown arch connection')
    absent=raw['absent_communicators']
    if not isinstance(absent,list) or len(absent)!=len(set(absent)) or not set(absent)<={'acom','left_pcom','right_pcom'}:
        raise ValueError('Unknown communicating artery')
    params=raw['vessel_parameters']
    if not isinstance(params,dict) or not set(params)<=known:
        raise ValueError('Unknown vessel')
    cleaned={}
    for name,values in params.items():
        if not isinstance(values,dict) or set(values)!={'radius_scale','tortuosity'}:
            raise ValueError('Invalid vessel shape')
        cleaned[name]=dict(radius_scale=number(values['radius_scale'],.5,2),tortuosity=number(values['tortuosity'],0,1))
    result.update(arch_variant=raw['arch_variant'],absent_communicators=absent,vessel_parameters=cleaned)
    veins=raw['venous']
    if not isinstance(veins,dict) or set(veins)!=set(defaults()['venous']):
        raise ValueError('Expected complete venous parameters')
    if isinstance(veins['samples'],bool) or not isinstance(veins['samples'],int) or not 8<=veins['samples']<=1024:
        raise ValueError('Invalid venous samples')
    if veins['imv_drainage'] not in IMV_DRAINAGE or veins['transverse_dominance'] not in TRANSVERSE_DOMINANCE:
        raise ValueError('Unknown venous variation')
    venous_overrides=veins['vessel_parameters']
    if not isinstance(venous_overrides,dict) or not set(venous_overrides)<=set(known_venous or ()):
        raise ValueError('Unknown venous vessel')
    cleaned_veins={}
    for name,values in venous_overrides.items():
        if not isinstance(values,dict) or set(values)!={'radius_scale','tortuosity'}:
            raise ValueError('Invalid venous vessel shape')
        cleaned_veins[name]=dict(radius_scale=number(values['radius_scale'],.5,2),tortuosity=number(values['tortuosity'],0,1))
    result['venous']=dict(radius_scale=number(veins['radius_scale'],.5,2),tortuosity=number(veins['tortuosity'],0,1),samples=veins['samples'],
                          vessel_parameters=cleaned_veins,imv_drainage=veins['imv_drainage'],transverse_dominance=veins['transverse_dominance'])
    return result


def validate_visibility(raw):
    if not isinstance(raw,dict) or set(raw)!=set(LAYERS) or any(type(value) is not bool for value in raw.values()):
        raise ValueError('Expected exact layer visibility mapping')
    return dict(raw)


def expected_generation_matches(header,current_generation):
    """Require the revision the editor actually loaded, not a later poll result."""
    return (isinstance(header,str) and header.isascii() and header.isdigit()
            and len(header)<=20 and int(header)==current_generation)

@lru_cache(maxsize=2)
def cached_surface(key):
    graph=generate(**json.loads(key))
    return graph,network_mesh(graph)


@lru_cache(maxsize=2)
def cached_venous_surface(key):
    veins=generate_veins(**json.loads(key))
    # Each circulation is extracted independently. Never fuse portal and systemic.
    return veins,{name:network_mesh(graph) for name,graph in veins.graphs.items()}

class Workspace:
    def __init__(self,server,*,load_reference_source=True,atlas_edit_session_path=None):
        self.server=server
        self.lock=threading.RLock()
        self.parameters=defaults()
        self.generation=0
        self.busy=True
        self.error=None
        self.graph=None
        self.venous=None
        self.venous_meshes={}
        self.clearance=None
        self.known=set()
        self.known_venous=set()
        self.visibility={name:True for name in LAYERS}
        self.handles=[]
        self.layer_handles={name:[] for name in LAYERS}
        self.access,self.target='right_femoral','left_mca'
        self.mode='Surface'
        self.source='schematic'
        self.candidate=None
        self.reference=None
        self.atlas=None
        from .atlas import ROOT, PINNED
        self.annotations=AnnotationStore(ROOT/'cerebral-boundary-drafts.json', PINNED['isa_BP3D_4.0_obj_99.zip'])
        self.case_workspace=CaseWorkspace(ROOT/'arterial-workspace.snapshot.json')
        self.atlas_edit_session=AtlasEditSession(
            ROOT/'atlas-edits.snapshot.json' if atlas_edit_session_path is None else atlas_edit_session_path)
        self._atlas_edit_identity_cache=None
        self.annotation_context_visible=False
        self.annotation_context_meshes=None
        self.annotation_handles=[]
        self.annotation_point_handle=None
        self.atlas_selection=None
        self.atlas_part_handles={}
        self.atlas_centerlines=None
        self.atlas_original_centerlines=None
        self.atlas_modifications={}
        self.atlas_modified_parts={}
        self.atlas_centerline_status=dict(available=False,busy=False,summary={})
        self.atlas_centerlines_visible=True
        self.atlas_centerline_handles={}
        self.atlas_centerline_colors={}
        self.atlas_info=dict(available=False,error='Atlas files have not been acquired.')
        self.context_visible=True
        self.context_handles=[]
        self.neck_parts=[]
        self.neck_info=dict(available=False,parts=[])
        self.neck_repairs_visible=True
        self.neck_handles={name:[] for name in LAYERS}
        self.reference_info=dict(available=False,error='Reference files have not been acquired.')
        try:
            from .reference import load_reference
            if load_reference_source:
                self.reference=load_reference()
                self.reference_info=dict(self.reference.metadata,available=True)
        except (ImportError,OSError,ValueError):
            self.reference_info=dict(available=False,error='Reference unavailable or integrity validation failed. Run the documented reference acquisition step.')
        if load_reference_source:
            try:
                from .atlas import load_atlas
                self.atlas=load_atlas()
                self.atlas_info=dict(self.atlas.metadata,available=True)
            except (ImportError,OSError,ValueError):
                self.atlas_info=dict(available=False,error='Atlas unavailable or integrity validation failed.')
        if self.atlas is not None:
            try:
                from .atlas_neck import build_neck_repairs
                self.neck_parts,self.neck_info=build_neck_repairs(self.atlas)
                self.neck_info['available']=bool(self.neck_parts)
            except (ImportError,OSError,ValueError):
                self.neck_info=dict(available=False,parts=[],error='Estimated neck reconstruction unavailable.')
        self.metrics=server.gui.add_markdown('Building initial anatomy…')
        # The browser shell renders this shared description in the tab's language.
        self.metrics.visible=False
        self.rebuild(self.parameters)
        # Atlas is the primary editing workspace. Legacy generator data remains
        # available internally, but is no longer the initial user-facing scene.
        if self.atlas is not None and load_reference_source:
            self.source='atlas'
            self.draw_atlas()
            self.metrics.content=self.description(self.graph)
            self.atlas_centerline_status=dict(available=False,busy=True,completed=0,total=len(self.atlas.meshes),summary={})
            threading.Thread(target=self.build_atlas_centerlines,daemon=True).start()

    def build_atlas_centerlines(self):
        try:
            from .atlas import ROOT
            from .atlas_centerlines import build_atlas_centerlines
            def progress(completed,total):
                with self.lock:self.atlas_centerline_status.update(completed=completed,total=total)
            result=build_atlas_centerlines(self.atlas,self.neck_parts,cache_dir=ROOT/'centerline-cache',progress=progress)
            with self.lock:
                self.atlas_centerlines=result
                self.atlas_original_centerlines=copy.deepcopy(result)
                self.atlas_centerline_status=dict(available=True,busy=False,summary=result['summary'])
                if self.source=='atlas':self.draw_atlas_centerlines()
        except Exception as error:
            with self.lock:self.atlas_centerline_status=dict(available=False,busy=False,error=str(error),summary={})

    def snapshot(self):
        with self.lock:
            graphs={'arterial':self.graph,**(self.venous.graphs if self.venous else {})}
            if self.source=='reference':
                graphs={'arterial':self.reference.graph}
            elif self.source in ('atlas','candidate'):
                graphs={}
            layers={name:dict(nodes={key:value.tolist() for key,value in graphs[name].nodes.items()},edges=[dict(id=edge.name,start=edge.start,end=edge.end) for edge in graphs[name].segments]) if graphs.get(name) else dict(nodes={},edges=[]) for name in LAYERS}
            return dict(generation=self.generation,busy=self.busy,
                scene_description=self.metrics.content,
                candidate_radius_busy=getattr(self,'candidate_radius_busy',False),
                candidate_radius_progress=dict(getattr(self,'candidate_radius_progress',{})),
                candidate_radius_request=(dict(self.candidate_radius_request)
                    if getattr(self,'candidate_radius_busy',False) and getattr(self,'candidate_radius_request',None) else None),
                candidate_radius=getattr(self,'candidate_radius_session',None).status() if getattr(self,'candidate_radius_session',None) else None,
                interval_preview_busy=getattr(self,'interval_preview_busy',False),
                atlas_interval_edits={pid:len(edits) for pid,edits in getattr(self,'atlas_interval_edits',{}).items()},
                atlas_interval_undo_available=bool(getattr(self,'atlas_interval_undo',[]) and self.atlas_interval_undo[-1]['generation']==self.generation),
                error=self.error,parameters=json.loads(json.dumps(self.parameters)),
                mode=self.mode,access=self.access,target=self.target,
                arch_measurement=self.graph.parameters.get('arch_measurement',{}) if self.graph else {},
                nodes=layers['arterial']['nodes'],edges=layers['arterial']['edges'],layers=layers,visibility=dict(self.visibility),
                source=self.source,candidate=copy.deepcopy(self.candidate['summary']) if getattr(self,'candidate',None) else None,reference=self.reference_info,atlas=self.atlas_info,atlas_selection=self.atlas_selection,context_visible=self.context_visible,
                atlas_centerlines=dict(self.atlas_centerline_status),atlas_centerlines_visible=self.atlas_centerlines_visible,
                atlas_modifications=copy.deepcopy(self.atlas_modifications),
                atlas_edit_checks={pid:copy.deepcopy(p.get('edit_checks')) for pid,p in self.atlas_modified_parts.items()},
                atlas_edit_recovery_error=getattr(self,'atlas_edit_recovery_error',None),
                annotation_context_visible=self.annotation_context_visible,
                neck_repairs=self.neck_info,neck_repairs_visible=self.neck_repairs_visible,
                clearance=self.clearance if self.source=='schematic' else None)

    def export_bundle(self):
        with self.lock:
            if self.source=='candidate':
                raise ValueError('Candidate preview is read-only; workspace export is unavailable')
            if self.source=='atlas':
                return json.dumps(dict(schema='vv-toolbox.atlas-workspace/1',generation=self.generation,
                    atlas=self.atlas_info,visibility=self.visibility,context_visible=self.context_visible,
                    neck_repairs=self.neck_info,neck_repairs_visible=self.neck_repairs_visible,
                    centerlines=self.atlas_centerlines,
                    modifications=self.atlas_modifications,
                    interval_edits=getattr(self,'atlas_interval_edits',{}),
                    edit_checks={pid:p.get('edit_checks') for pid,p in self.atlas_modified_parts.items()},
                    modified_surfaces={pid:dict(vertices=p['vertices'].tolist(),faces=p['faces'].tolist()) for pid,p in self.atlas_modified_parts.items()},
                    clinical_validation=False,surface='Source atlas plus explicitly parameterized derived surfaces. Original files preserved; edited geometry and collisions are not anatomically validated.'),indent=2,allow_nan=False)
            if self.source=='reference':
                return json.dumps(dict(schema='vv-toolbox.reference-workspace/1',generation=self.generation,
                    reference=self.reference_info,paths=json.loads(self.reference.graph.to_json()),
                    surface='Original source surface; see source URL and SHA256 in reference metadata.',
                    clinical_validation=False),indent=2,allow_nan=False)
            if self.graph is None or self.venous is None:
                raise ValueError('Anatomy is not ready')
            return json.dumps(dict(schema='vv-toolbox.workspace/1',units='mm',generation=self.generation,
                provenance=dict(kind='synthetic-illustrative',patient_derived=False,anatomy_validated=False),
                parameters=self.parameters,visibility=self.visibility,clearance=self.clearance,
                arterial=json.loads(self.graph.to_json()),venous=json.loads(self.venous.to_json()),
                circuit_separation='Arterial, systemic venous and hepatic portal surfaces are independent; exchange beds are not rendered as direct vessels.'),indent=2,allow_nan=False)

    def set_visibility(self,raw):
        visibility=validate_visibility(raw)
        with self.lock:
            self.visibility=visibility
            # Visibility is a tiny scene update, never a mesh build/retransmission.
            with self.server.atomic():
                for layer,handles in self.layer_handles.items():
                    for handle in handles:
                        handle.visible=visibility[layer]
                for layer,handles in self.neck_handles.items():
                    for handle in handles:
                        handle.visible=visibility[layer] and self.neck_repairs_visible
                self.update_atlas_centerline_visibility()

    def rebuild(self,parameters):
        try:
            arterial={key:value for key,value in parameters.items() if key!='venous'}
            graph,mesh=cached_surface(json.dumps(arterial,sort_keys=True))
            veins,venous_meshes=cached_venous_surface(json.dumps(parameters['venous'],sort_keys=True))
            clearance=cross_circuit_clearance({'arterial':graph,**veins.graphs})
            with self.lock:
                self.draw(graph,mesh,veins,venous_meshes)
                self.graph,self.mesh=graph,mesh
                self.venous,self.venous_meshes=veins,venous_meshes
                self.clearance=clearance
                self.parameters=parameters
                self.known.update(e.name for e in graph.segments)
                self.known_venous.update(edge.name for venous_graph in veins.graphs.values() for edge in venous_graph.segments)
                self.generation+=1
                self.error=None
                self.metrics.content=self.description(graph)
        except Exception as exc:
            with self.lock:
                self.error=f'Rebuild failed: {type(exc).__name__}: {exc}'
        finally:
            with self.lock:
                self.busy=False

    def description(self,graph,*,atlas_modified_count=None):
        if self.source=='candidate':
            summary=self.candidate['summary']
            if 'access_union' in summary:
                audit=summary['access_union']
                if 'radius_edit' in summary:
                    edit=summary['radius_edit']
                    return f"**{summary['title']} · 반경 변형 후보**\n\n원본 Atlas 보존 · 배율 {edit['scale']}\n\n자기 접촉 검사: {edit['self_contact']['status']}\n\n중심선 검사: {audit['centerline_status']} ({audit['checked_paths']}개 경로) · 주변 검사: {edit['neighbor_contact']}\n\n변형 좌표는 합성 출처입니다. 접합 매끄러움·해부학적 수용: 미확인."
                lineage=(f"{audit['lineage_faces']}개 면 출처 확인" if isinstance(audit['lineage_faces'],int)
                         else "변경 표면의 출처 대조 미실행")
                return f"**{summary['title']}**\n\n{summary['scope']}\n\n읽기 전용 · 원본 Atlas 보존\n\n단일 폐곡면 · {lineage}.\n\n중심선 검사: {audit['centerline_status']} · 주변 검사: {audit['context_status']}.\n\n네 접근 경로 그래프·해부 구간·접합 매끄러움: 미확인."
            if 'carotid_union' in summary:
                audit=summary['carotid_union']
                if 'radius_edit' in summary:
                    edit=summary['radius_edit']
                    return f"**{summary['title']} · 반경 변형 후보**\n\n원본 Atlas 보존 · 배율 {edit['scale']}\n\n자기 접촉 검사: {audit['self_contact']}\n\n주변 혈관 검사: {edit['neighbor_contact']}\n\n중심선 포함·접합 매끄러움: 재검사 필요. 해부학적 연결: 미확인."
                return f"**{summary['title']} · 합성 후보**\n\n{summary['scope']}\n\n읽기 전용 · 원본 Atlas 보존\n\n중심선 {audit['path_segments']}개 구간 포함 · {audit['lineage_faces']}개 면 출처 확인.\n\n접합 매끄러움과 해부학적 연결: 미확인."
            if 'protected_comparison' in summary:
                audit=summary['protected_comparison']
                stage='원본 비교' if audit['reference'] else '합성 보정 후보'
                return f"**{summary['title']} · {stage}**\n\n{summary['scope']}\n\n읽기 전용 · 원본 파일 보존\n\n후보 자기 접촉 검출 0 · 동시 대체 {audit['affected_pairs']}조합의 접촉 쌍 보존.\n\n중심선·반경 일치와 해부학적 수용: 미확인."
            if 'context_inspection' in summary:
                audit=summary['context_inspection']
                return f"**{summary['title']} · 합성 후보**\n\n{summary['scope']}\n\n읽기 전용 · 원본 Atlas 보존\n\n주변 프로파일 검사: {audit['status']} · 분리 {audit['separated_count']}/{audit['context_edge_count']}\n\n원본 표면 충돌·임상 검증: NOT RUN."
            return f"**{summary['title']} · 합성 후보**\n\n{summary['scope']}\n\n읽기 전용 · 빨간 동맥 · 원본 Atlas 보존\n\n두 표면 간 분리: {summary['pair_surface_separation']}\n\n전체 Atlas 충돌·자기 교차: NOT RUN. 해부학 검증: UNKNOWN."
        if self.source=='atlas':
            count=len(set(self.atlas_modifications)|set(getattr(self,'atlas_interval_edits',{}))) if atlas_modified_count is None else atlas_modified_count
            return f'**BodyParts3D · shared-coordinate atlas**\n\n{count} modified vessel(s); source files preserved.\n\nRed arteries · blue veins · translucent organ context.\n\nShape edits are illustrative; junction continuity and collisions are not validated.'
        if self.source=='reference':
            return f"**{self.reference_info['title']}**\n\nOriginal image-derived reference surface and source paths.\n\nStandalone reference; not merged with the synthetic body.\n\nClinical validation: NOT RUN."
        route,length=graph.route(self.access,self.target)
        venous_count=sum(len(g.segments) for g in self.venous.graphs.values()) if self.venous else 0
        return f'**Generation {self.generation}** · {len(graph.segments)} arterial / {venous_count} venous vessels\n\nArterial route {length:,.1f} mm · {len(route)} segments\n\nSYNTHETIC / ILLUSTRATIVE\n\nThree separate circulation layers. Undirected arterial route; not blood flow. All tabs share this workspace.'

    def draw(self,graph,mesh,veins=None,venous_meshes=None):
        if self.source=='candidate':
            self.draw_candidate()
            return
        if self.source=='atlas':
            self.draw_atlas()
            return
        self.annotation_context_visible=False
        self.draw_annotation_context()
        if self.annotation_point_handle is not None:
            self.annotation_point_handle.remove()
            self.annotation_point_handle=None
        veins=self.venous if veins is None else veins
        venous_meshes=self.venous_meshes if venous_meshes is None else venous_meshes
        route,_=graph.route(self.access,self.target)
        graphs={'arterial':graph,**(veins.graphs if veins else {})}
        meshes={'arterial':mesh,**venous_meshes}
        if self.source=='reference':
            graphs={'arterial':self.reference.graph}
            meshes={'arterial':self.reference.mesh}
            route=[]
        with self.server.atomic():
            for h in self.handles:
                h.remove()
            self.handles.clear()
            self.context_handles=[]
            self.neck_handles={name:[] for name in LAYERS}
            self.layer_handles={name:[] for name in LAYERS}
            for layer,current_graph in graphs.items():
                first_handle=len(self.handles)
                color=LAYER_COLORS[layer]
                if self.mode=='Surface':
                    v,f=meshes[layer]
                    self.handles.append(self.server.scene.add_mesh_simple('/layers/'+layer+'/surface',v/1000,f,color=color,side='double',opacity=1.,cast_shadow=False,receive_shadow=False))
                for e in current_graph.segments:
                    selected=layer=='arterial' and e.name in route
                    if selected or self.mode=='Centerlines':
                        points=np.stack([e.points[:-1],e.points[1:]],axis=1).astype(np.float32)/1000
                        self.handles.append(self.server.scene.add_line_segments('/layers/'+layer+'/'+e.name,points,(255,112,108) if selected else color,thickness=3 if selected else 2,thickness_units='screen'))
                self.layer_handles[layer]=self.handles[first_handle:]
                for handle in self.layer_handles[layer]:
                    handle.visible=self.visibility[layer]

    def focus_reference(self):
        vertices=self.reference.mesh[0]/1000
        low,high=vertices.min(axis=0),vertices.max(axis=0)
        center=(low+high)/2
        span=float(np.max(high-low))
        for client in self.server.get_clients().values():
            client.camera.look_at=tuple(center)
            client.camera.position=tuple(center+np.array([.25,-1.8,.25])*span)

    def draw_atlas(self):
        with self.server.atomic():
            for handle in self.handles:
                handle.remove()
            self.handles=[]
            self.context_handles=[]
            self.neck_handles={name:[] for name in LAYERS}
            self.layer_handles={name:[] for name in LAYERS}
            self.atlas_part_handles={}
            self.atlas_centerline_handles={}
            for part in self.atlas.meshes:
                part=self.atlas_modified_parts.get(part['id'],part)
                layer=part['layer']
                context=layer=='context'
                handle=self.server.scene.add_mesh_simple('/atlas/'+part['id'],part['vertices']/1000,part['faces'],
                    color=(185,163,147) if context else LAYER_COLORS[layer],side='double',
                    opacity=.18 if context else 1.,cast_shadow=False,receive_shadow=False)
                handle.visible=self.context_visible if context else self.visibility[layer]
                self.handles.append(handle)
                self.atlas_part_handles[part['id']]=handle
                if part['id']==self.atlas_selection:handle.color=(255,222,125)
                (self.context_handles if context else self.layer_handles[layer]).append(handle)
            for part in self.neck_parts:
                part=self.atlas_modified_parts.get(part['id'],part)
                layer=part['layer']
                handle=self.server.scene.add_mesh_simple('/estimated-neck/'+part['id'],part['vertices']/1000,part['faces'],
                    color=LAYER_COLORS[layer],side='double',opacity=1.,
                    cast_shadow=False,receive_shadow=False)
                handle.visible=self.neck_repairs_visible and self.visibility[layer]
                self.handles.append(handle)
                self.neck_handles[layer].append(handle)
                self.atlas_part_handles[part['id']]=handle
                if part['id']==self.atlas_selection:handle.color=(255,222,125)
            self.draw_atlas_centerlines()
            self.draw_annotation_context()

    def draw_annotation_context(self):
        """Display native landmarks using the existing Atlas display scale only."""
        for handle in self.annotation_handles:
            handle.remove()
        self.annotation_handles=[]
        if self.source!='atlas' or not self.annotation_context_visible:return
        if self.annotation_context_meshes is None:
            import zipfile
            from pathlib import Path
            from .atlas import ROOT, parse_obj
            # load_atlas has already checked the pinned source archive.
            with zipfile.ZipFile(ROOT/'isa_BP3D_4.0_obj_99.zip') as archive:
                names={Path(name).stem:name for name in archive.namelist() if name.endswith('.obj')}
                self.annotation_context_meshes={pid:parse_obj(archive.read(names[pid])) for pid in ('FJ1742','FJ1748','FJ1749')}
        for pid,(vertices,faces) in self.annotation_context_meshes.items():
            self.annotation_handles.append(self.server.scene.add_mesh_simple('/annotation-context/'+pid,vertices/1000,faces,
                color=(140,215,186),opacity=.22,side='double',cast_shadow=False,receive_shadow=False))

    def focus_annotation_candidate(self, boundary_id):
        value=self.annotations.read()
        if boundary_id not in {b['boundary_id'] for b in value['document']['boundaries']}:
            raise ValueError('Unknown boundary')
        self.clear_annotation_candidate()
        require_renderable_frame(value['document'])
        xyz=value['candidate_positions'].get(boundary_id)
        if xyz is None:return
        point=np.asarray([xyz],dtype=np.float32)/1000
        self.annotation_point_handle=self.server.scene.add_point_cloud('/annotation-candidate',
            points=point,colors=np.asarray([[255,204,70]],dtype=np.uint8),point_size=.004)
        for client in self.server.get_clients().values():
            client.camera.look_at=tuple(point[0])
            client.camera.position=tuple(point[0]+np.array([.02,-.12,.04]))

    def clear_annotation_candidate(self):
        if self.annotation_point_handle is not None:
            self.annotation_point_handle.remove()
            self.annotation_point_handle=None

    def draw_atlas_centerlines(self):
        if self.source!='atlas' or self.atlas_centerlines is None:return
        with self.server.atomic():
            for handle in self.atlas_centerline_handles.values():
                handle.remove()
                if handle in self.handles:self.handles.remove(handle)
            self.atlas_centerline_handles={}
            paths={}
            for edge in self.atlas_centerlines['edges']:
                points=np.asarray(edge['points'],dtype=np.float32)/1000
                paths.setdefault(edge['part_id'],[]).append(np.stack([points[:-1],points[1:]],axis=1))
            for pid,segments in paths.items():
                layer=next(e['layer'] for e in self.atlas_centerlines['edges'] if e['part_id']==pid)
                self.atlas_centerline_colors[pid]={'arterial':(255,90,96),'systemic_venous':(92,174,255),'hepatic_portal':(108,211,255)}[layer]
                points=np.concatenate(segments)
                color=(255,220,95) if pid==self.atlas_selection else self.atlas_centerline_colors[pid]
                colors=np.broadcast_to(np.asarray(color,dtype=np.uint8),points.shape).copy()
                handle=self.server.scene.add_line_segments('/atlas-centerlines/'+pid,points,
                    colors,thickness=2,thickness_units='screen')
                self.atlas_centerline_handles[pid]=handle;self.handles.append(handle)
                if hasattr(handle,'on_click'):
                    def select(event,part_id=pid):
                        with self.lock:
                            if self.source=='atlas':self.select_atlas_part(part_id)
                    handle.on_click(select)
            self.update_atlas_centerline_visibility()

    def update_atlas_centerline_visibility(self):
        if self.source!='atlas':return
        parts=[*self.atlas.meshes,*self.neck_parts]
        estimated={p['id'] for p in self.neck_parts}
        for p in parts:
            pid=p['id'];layer=p['layer']
            if pid in self.atlas_centerline_handles:
                self.atlas_centerline_handles[pid].visible=self.atlas_centerlines_visible and self.visibility.get(layer,False) and (pid not in estimated or self.neck_repairs_visible)
            if pid in self.atlas_part_handles and layer!='context':
                self.atlas_part_handles[pid].opacity=.25 if self.atlas_centerlines_visible and self.atlas_centerlines is not None else 1.

    def select_atlas_part(self,part_id):
        if self.source!='atlas' or not isinstance(part_id,str):
            raise ValueError('Select a vessel in the detailed atlas first')
        parts={p['id']:p for p in [*self.atlas.meshes,*self.neck_parts]}
        if part_id not in parts or parts[part_id]['layer']=='context':
            raise ValueError('Unknown atlas vessel')
        with self.server.atomic():
            if self.atlas_selection in self.atlas_part_handles:
                old=parts[self.atlas_selection]
                self.atlas_part_handles[self.atlas_selection].color=LAYER_COLORS[old['layer']]
            self.atlas_selection=part_id
            self.atlas_part_handles[part_id].color=(255,222,125)
            for pid,handle in self.atlas_centerline_handles.items():
                handle.colors=np.broadcast_to(np.array((255,220,95) if pid==part_id else self.atlas_centerline_colors[pid],dtype=np.uint8),handle.points.shape).copy()
        vertices=self.atlas_modified_parts.get(part_id,parts[part_id])['vertices']/1000
        low,high=vertices.min(axis=0),vertices.max(axis=0)
        center=(low+high)/2;span=max(float((high-low).max()),.08)
        for client in self.server.get_clients().values():
            with self.server.atomic():
                client.camera.position=tuple(center+np.array([0.,-1.6,.1])*span)
                client.camera.look_at=tuple(center)

    def atlas_edit_identity(self):
        if self.atlas is None or self.atlas_original_centerlines is None:
            raise ValueError('Original atlas centerlines must be available')
        key=(id(self.atlas),id(self.atlas_original_centerlines),id(self.neck_parts))
        if self._atlas_edit_identity_cache is None or self._atlas_edit_identity_cache[0]!=key:
            self._atlas_edit_identity_cache=(key,source_identity(self.atlas.metadata,self.atlas_original_centerlines,[*self.atlas.meshes,*self.neck_parts]))
        return self._atlas_edit_identity_cache[1]

    def atlas_edit_status(self):
        with self.lock:
            recovery_error=getattr(self,'atlas_edit_recovery_error',None)
            available=self.source=='atlas' and self.atlas_original_centerlines is not None and not recovery_error
            exists=self.atlas_edit_session.path.exists()
            saved_revision=None
            dirty=bool(self.atlas_modifications)
            error=recovery_error
            if available and exists:
                try:
                    saved,saved_revision=self.atlas_edit_session.read(self.atlas_edit_identity())
                    dirty=saved!=self.atlas_modifications
                except (ValueError,OSError,TypeError,KeyError):
                    error='Saved edits are invalid or incompatible; file preserved'
            intervals=getattr(self,'atlas_interval_edits',{})
            if intervals:
                available=False
                dirty=True
                error='Active interval edits are session-only; download candidates or undo intervals before parameter save/reload'
            return dict(available=available,generation=self.generation,file_exists=exists,
                        saved_revision=saved_revision,modified_parts=len(self.atlas_modifications),dirty=dirty,error=error,
                        scope='Atlas vessel radius, tortuosity and torsion parameters; source geometry preserved. Selection and visibility remain current.',
                        quality=dict(anatomical_validation='NOT RUN',collision_validation='NOT RUN'))

    def update_atlas_edit_session(self,raw):
        with self.lock:
            if getattr(self,'atlas_interval_edits',{}):
                raise AtlasEditConflict('Interval edits require their own save format; undo interval edits before parameter save/reload')
            if getattr(self,'atlas_edit_recovery_error',None):
                raise AtlasEditConflict(self.atlas_edit_recovery_error)
            if not isinstance(raw,dict) or set(raw)!={'action','expected_generation'} or raw['action'] not in ('save','reload'):
                raise ValueError('Invalid atlas edit session action')
            if type(raw['expected_generation']) is not int or raw['expected_generation']!=self.generation:
                raise AtlasEditConflict('Anatomy changed; refresh before saving or reloading edits')
            if self.busy or self.source!='atlas':
                raise AtlasEditConflict('Atlas must be active and ready')
            identity=self.atlas_edit_identity()
            if raw['action']=='save':
                for pid in self.atlas_modifications:
                    if pid not in self.atlas_modified_parts:
                        raise AtlasEditCheckFailure('Edited surface unavailable for save inspection')
                    require_self_contact_clearance(self.atlas_modified_parts[pid])
                self.atlas_edit_session.save(identity,self.atlas_modifications)
            else:
                modifications,revision=self.atlas_edit_session.read(identity)
                parts=[*self.atlas.meshes,*self.neck_parts]
                graph,surfaces,modifications=regenerate(parts,self.atlas_original_centerlines,modifications)
                # Existing handles preserve selection, visibility and callbacks.
                # Stage every array first; rollback inside the same scene atomic block.
                updates=[]
                changed=set(self.atlas_modifications)|set(modifications)
                for part in parts:
                    pid=part['id']
                    if pid not in changed:continue
                    if pid not in self.atlas_part_handles or pid not in self.atlas_centerline_handles:
                        raise ValueError('Atlas edit scene handles unavailable')
                    updates.append((self.atlas_part_handles[pid],'vertices',surfaces.get(pid,part)['vertices']/1000))
                    paths=[]
                    for edge in graph['edges']:
                        if edge['part_id']==pid:
                            points=np.asarray(edge['points'],dtype=np.float32)/1000
                            paths.append(np.stack([points[:-1],points[1:]],axis=1))
                    updates.append((self.atlas_centerline_handles[pid],'points',np.concatenate(paths)))
                updates.append((self.metrics,'content',self.description(self.graph,atlas_modified_count=len(modifications))))
                prior=[(handle,field,copy.deepcopy(getattr(handle,field))) for handle,field,_ in updates]
                with self.server.atomic():
                    try:
                        for handle,field,value in updates:setattr(handle,field,value)
                    except Exception:
                        rollback_errors=[]
                        for handle,field,value in reversed(prior):
                            try:setattr(handle,field,value)
                            except Exception as error:rollback_errors.append(error)
                        if rollback_errors:
                            self.error='Atlas edit scene rollback incomplete; restart the demo server before further editing'
                            self.atlas_edit_recovery_error=self.error
                            raise RuntimeError(self.error) from rollback_errors[0]
                        raise
                self.atlas_modifications=modifications
                self.atlas_modified_parts=surfaces
                self.atlas_centerlines=graph
                self.atlas_centerline_status['summary']=graph['summary']
                self.atlas_edit_session.revision=revision
                self.generation+=1
            return self.atlas_edit_status()

    def modify_atlas_part(self,raw):
        from .atlas_modification import deform_part
        from .atlas_centerlines import proximity_links
        if getattr(self,'atlas_interval_edits',{}):
            raise AtlasEditConflict('Undo interval edits before whole-vessel parameter editing')
        if getattr(self,'atlas_edit_recovery_error',None):
            raise AtlasEditConflict(self.atlas_edit_recovery_error)
        if self.source!='atlas' or self.atlas_centerlines is None:
            raise ValueError('Atlas centerlines must be available')
        if not isinstance(raw,dict) or set(raw)!={'part_id','radius_scale','tortuosity','torsion_deg'}:
            raise ValueError('Invalid atlas modification')
        pid=raw['part_id']
        if not isinstance(pid,str):raise ValueError('Invalid part')
        original=next((p for p in [*self.atlas.meshes,*self.neck_parts] if p['id']==pid and p['layer']!='context'),None)
        if original is None:raise ValueError('Unknown atlas vessel')
        base=self.atlas_original_centerlines or self.atlas_centerlines
        source_edges=[e for e in base['edges'] if e['part_id']==pid]
        parameters={k:raw[k] for k in ('radius_scale','tortuosity','torsion_deg')}
        part,edges=deform_part(original,source_edges,parameters)
        if parameters!=dict(radius_scale=1.,tortuosity=0.,torsion_deg=0.):
            require_self_contact_clearance(part)
        graph=copy.deepcopy(self.atlas_centerlines)
        graph['edges']=[e for e in graph['edges'] if e['part_id']!=pid]+edges
        graph['nodes']=[n for n in graph['nodes'] if n['kind']!='candidate_attachment']
        nodes={n['id']:n for n in graph['nodes']}
        for edge in edges:
            for end,idx in [('start',0),('end',-1)]:
                nodes[edge[end]]['point']=edge['points'][idx]
                nodes[edge[end]]['radius']=edge['radii'][idx]
        graph['links']=proximity_links(graph['nodes'],graph['edges'])
        from .atlas_topology import build_reference_topology
        graph['reference_topology']=build_reference_topology([*self.atlas.meshes,*self.neck_parts],graph['links'])
        graph['summary'].update(nodes=len(graph['nodes']),candidate_links=len(graph['links']))
        reset=parameters==dict(radius_scale=1.,tortuosity=0.,torsion_deg=0.)
        prior=(self.atlas_modifications,self.atlas_modified_parts,self.atlas_centerlines,
               self.atlas_centerline_status['summary'],self.generation,self.atlas_selection,
               self.metrics.content)
        self.atlas_modifications=dict(self.atlas_modifications)
        self.atlas_modified_parts=dict(self.atlas_modified_parts)
        if reset:
            self.atlas_modifications.pop(pid,None)
            self.atlas_modified_parts.pop(pid,None)
        else:
            self.atlas_modifications[pid]=parameters
            self.atlas_modified_parts[pid]=part
        graph['modifications']=copy.deepcopy(self.atlas_modifications)
        self.atlas_centerlines=graph
        self.atlas_centerline_status['summary']=graph['summary']
        self.generation+=1
        try:
            self.draw_atlas()
            self.select_atlas_part(pid)
            self.metrics.content=self.description(self.graph)
        except Exception:
            (self.atlas_modifications,self.atlas_modified_parts,self.atlas_centerlines,
             self.atlas_centerline_status['summary'],self.generation,self.atlas_selection,
             legend)=prior
            try:
                self.draw_atlas()
                if self.atlas_selection is not None:
                    self.select_atlas_part(self.atlas_selection)
                self.metrics.content=legend
            except Exception as rollback_error:
                self.error='Atlas modification rollback incomplete; restart the demo server before further editing'
                self.atlas_edit_recovery_error=self.error
                raise RuntimeError(self.error) from rollback_error
            raise

    def render_interval_part(self, pid):
        """Update the existing surface handle without replacing selection or camera."""
        self.render_interval_parts([pid])

    def render_interval_parts(self, part_ids):
        sources={p['id']:p for p in [*self.atlas.meshes,*self.neck_parts]}
        updates=[(self.atlas_part_handles[pid],
                  self.atlas_modified_parts.get(pid,sources[pid])['vertices']/1000) for pid in part_ids]
        with self.server.atomic():
            for handle,vertices in updates:
                handle.vertices=vertices
            self.metrics.content=self.description(self.graph)

    def focus_atlas(self,focus='Whole network'):
        parts=self.atlas.meshes
        if focus=='Aortic arch':
            selected=[part for part in parts if part['layer']=='context' or 'brachiocephalic vein' in part['name'].lower()]
            parts=selected or parts
        vertices=np.concatenate([part['vertices'] for part in parts])/1000
        low,high=vertices.min(axis=0),vertices.max(axis=0)
        if focus in getattr(self.atlas,'focus_bounds',{}):
            low,high=np.asarray(self.atlas.focus_bounds[focus],dtype=float)/1000
        center=(low+high)/2
        span=float(np.max(high-low))
        camera=getattr(self.atlas,'camera',None) if focus=='Whole network' else None
        for client in self.server.get_clients().values():
            position,target=camera if camera else (tuple(center+np.array([0.,-1.4,.1])*span),tuple(center))
            with self.server.atomic():
                client.camera.position=position
                client.camera.look_at=target

    def draw_candidate(self):
        self.clear_annotation_candidate()
        for handle in self.annotation_handles:
            handle.remove()
        self.annotation_handles=[]
        with self.server.atomic():
            for handle in self.handles:
                handle.remove()
            self.handles=[]
            self.context_handles=[]
            self.neck_handles={name:[] for name in LAYERS}
            self.layer_handles={name:[] for name in LAYERS}
            if self.mode=='Surface':
                self.handles.append(self.server.scene.add_mesh_simple('/candidate/surface',
                    self.candidate['vertices_mm']/1000,self.candidate.get('display_faces',self.candidate['faces']),color=LAYER_COLORS['arterial'],
                    side='double',opacity=1.,cast_shadow=False,receive_shadow=False))
            else:
                for index,edge in enumerate(self.candidate['edges']):
                    points=np.asarray(edge.get('points',edge.get('centerline_mm')),dtype=np.float32)/1000
                    color=((255,145,145) if self.candidate['summary'].get('access_graph')
                           and edge.get('geometry_kind')=='estimated' else LAYER_COLORS['arterial'])
                    self.handles.append(self.server.scene.add_line_segments('/candidate/path/'+str(index),
                        np.stack([points[:-1],points[1:]],axis=1),color,
                        thickness=2,thickness_units='screen'))
            self.layer_handles['arterial']=list(self.handles)
            for handle in self.handles:handle.visible=self.visibility['arterial']

    def select_candidate_source(self, source_name):
        from .union_selection import select_union_source
        if self.source!='candidate' or 'face_lineage' not in self.candidate:
            raise ValueError('Source selection unavailable for this candidate')
        if source_name is not None and not isinstance(source_name,str):
            raise ValueError('Source name must be a string or null')
        selection=None if source_name is None else select_union_source(
            self.candidate['vertices_mm'],self.candidate['faces'],self.candidate['face_lineage'],source_name)
        old_faces=self.candidate.get('display_faces')
        old_summary=copy.deepcopy(self.candidate['summary'])
        try:
            if selection is None:self.candidate.pop('display_faces',None)
            else:self.candidate['display_faces']=self.candidate['faces'][selection['face_ids']]
            summary=self.candidate['summary']
            summary['selected_source']=source_name
            summary['source_selection']=None if selection is None else dict(
                faces=len(selection['face_ids']),exclusive_vertices=len(selection['exclusive_vertex_ids']),
                shared_vertices=len(selection['shared_interface_vertex_ids']))
            self.draw_candidate()
        except Exception:
            self.candidate['summary']=old_summary
            if old_faces is None:self.candidate.pop('display_faces',None)
            else:self.candidate['display_faces']=old_faces
            self.draw_candidate()
            raise
        self.generation+=1

    def focus_candidate(self):
        vertices=self.candidate['vertices_mm']/1000
        low,high=vertices.min(axis=0),vertices.max(axis=0)
        center=(low+high)/2
        span=max(float(np.max(high-low)),.02)
        for client in self.server.get_clients().values():
            with self.server.atomic():
                client.camera.position=tuple(center+np.array([.25,-1.8,.25])*span)
                client.camera.look_at=tuple(center)

    def set_source(self,source,candidate_id=None):
        if getattr(self,'candidate_radius_busy',False):
            raise ValueError('Wait for radius computation before changing source')
        radius_session=getattr(self,'candidate_radius_session',None)
        if radius_session and (radius_session.status()['preview_token'] or radius_session.status()['undo_available']):
            raise ValueError('Discard preview and undo radius edits before changing source')
        if source not in ('schematic','reference','atlas','candidate') or (source=='reference' and self.reference is None) or (source=='atlas' and self.atlas is None):
            raise ValueError('Reference source unavailable')
        if source=='candidate':
            from .candidate_preview import load_candidate_preview,CANDIDATE_ID
            # Revalidate every entry, before changing the current scene or source.
            try:
                candidate=load_candidate_preview(Path(__file__).resolve().parents[2],candidate_id or CANDIDATE_ID)
            except (OSError,ValueError,KeyError,TypeError) as error:
                raise ValueError('Candidate unavailable or evidence validation failed') from error
            self.candidate=candidate
            self.candidate_radius_session=None
            self.mode='Surface'
        self.source=source
        self.visibility['arterial']=True
        self.generation+=1
        self.draw(self.graph,self.mesh)
        self.metrics.content=self.description(self.graph)
        if source=='reference':
            self.focus_reference()
        elif source=='candidate':
            self.focus_candidate()
        elif source=='atlas':
            self.mode='Surface'
            self.focus_atlas()
        else:
            for client in self.server.get_clients().values():
                client.camera.position,client.camera.look_at=FOCUS['Whole network']

def serve(port=8093,*,atlas_edit_session_path=None):
    bind_host=os.environ.get('VV_BIND_HOST','127.0.0.1')
    http=ThreadingHTTPServer((bind_host,port),BaseHTTPRequestHandler)
    try:
        server=viser.ViserServer(host=bind_host,port=port+1,label='VV Toolbox · 3D')
        if server.get_port()!=port+1:
            server.stop()
            raise OSError('3D port is occupied')
    except Exception:
        http.server_close()
        raise
    server.gui.configure_theme(dark_mode=True,brand_color=(40,190,185),show_logo=False,show_share_button=False)
    server.scene.set_up_direction('+z')
    server.scene.world_axes.visible=False
    workspace=Workspace(server,atlas_edit_session_path=atlas_edit_session_path)
    from .context_jobs import ContextJobs,ContextJobBusy
    from .registered_context import run_access_context
    context_root=Path(__file__).resolve().parents[2]
    context_jobs=ContextJobs(lambda case,progress:run_access_context(case,progress,context_root),
                            store=context_root/'exports/context-jobs')
    if workspace.graph is None:
        server.stop()
        http.server_close()
        raise RuntimeError(workspace.error or 'Initial anatomy could not be generated')

    @server.on_client_connect
    def connect(client):
        client.camera.position,client.camera.look_at=FOCUS['Whole network']
        client.camera.up_direction=(0.,0.,1.)
        if workspace.source=='reference':
            workspace.focus_reference()
        elif workspace.source=='atlas':
            workspace.focus_atlas()
        elif workspace.source=='candidate':
            workspace.focus_candidate()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def send(self,status,body,kind='application/json'):
            data=body.encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type',kind+'; charset=utf-8')
            self.send_header('Content-Length',str(len(data)))
            self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            try:
                self.end_headers()
                self.wfile.write(data)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                # Browser navigation can close an in-flight polling response.
                return
        def do_GET(self):
            from .ui_language import with_language, JS as language_js
            if self.path=='/': self.send(200,with_language(HTML.replace('__VISER_PORT__',str(port+1))),'text/html')
            elif self.path=='/ui-language.js': self.send(200,language_js,'application/javascript')
            elif self.path=='/case-labels':
                from .label_workbench import HTML as label_html
                self.send(200,with_language(label_html),'text/html')
            elif self.path=='/case-preview.js':
                from .case_preview_ui import JS
                self.send(200,JS,'application/javascript')
            elif self.path=='/api/atlas-edit-session':
                self.send(200,json.dumps(workspace.atlas_edit_status()))
            elif self.path=='/api/candidate-case-snapshot':
                try:
                    from .candidate_case import displayed_candidate_snapshot
                    with workspace.lock:
                        if workspace.source!='candidate' or workspace.busy or getattr(workspace,'candidate_radius_busy',False):
                            raise ValueError('An idle displayed access candidate is required')
                        if not expected_generation_matches(self.headers.get('X-Expected-Generation'),workspace.generation):
                            self.send(409,json.dumps(dict(error='Candidate changed; refresh before downloading')))
                            return
                        document=displayed_candidate_snapshot(workspace.candidate,Path(__file__).resolve().parents[2])
                    self.send(200,json.dumps(document),'application/json')
                except (ValueError,KeyError,TypeError) as error:
                    self.send(400,json.dumps(dict(error=str(error))))
                except OSError:
                    self.send(503,json.dumps(dict(error='Candidate source graph unavailable')))
            elif self.path=='/api/candidate-radius-session':
                try:
                    with workspace.lock:
                        session=getattr(workspace,'candidate_radius_session',None)
                        if workspace.source!='candidate' or session is None or getattr(workspace,'candidate_radius_busy',False):
                            raise ValueError('No idle radius session to save')
                        text=session.export_text()
                    self.send(200,text,'application/json')
                except ValueError as error:
                    self.send(400,json.dumps(dict(error=str(error))))
            elif self.path in ('/api/case-workspace','/api/case-download'):
                try:
                    value=workspace.case_workspace.download() if self.path.endswith('download') else workspace.case_workspace.status()
                    self.send(200,json.dumps(value))
                except ValueError as error:self.send(400,json.dumps({'error':str(error)}))
                except OSError:self.send(503,'{"error":"Local case storage unavailable"}')
            elif self.path=='/api/atlas-annotations':
                try:
                    if workspace.atlas is None:raise ValueError('Atlas unavailable')
                    self.send(200,json.dumps(workspace.annotations.read()))
                except (OSError,ValueError,KeyError,TypeError):
                    self.send(503,'{"error":"Annotations unavailable or invalid; existing file preserved"}')
            elif self.path.startswith('/api/case-context-jobs/'):
                try:
                    parts=self.path.split('/')
                    if len(parts) not in (4,5) or (len(parts)==5 and parts[4]!='result'):
                        raise ValueError('Unknown context job route')
                    status=context_jobs.status(parts[3])
                    if len(parts)==5 and status['state']!='COMPLETE':
                        self.send(409,json.dumps(dict(error='Context result not complete',job=status)))
                    else:self.send(200,json.dumps(context_jobs.result(parts[3]) if len(parts)==5 else status))
                except ValueError as error:self.send(404,json.dumps(dict(error=str(error))))
            elif self.path=='/api/state': self.send(200,json.dumps(workspace.snapshot()))
            elif self.path=='/api/atlas-centerlines':
                self.send(200 if workspace.atlas_centerlines is not None else 202,json.dumps(workspace.atlas_centerlines or workspace.atlas_centerline_status))
            elif self.path=='/api/export':
                try:self.send(200,workspace.export_bundle())
                except ValueError as error:self.send(400,json.dumps({'error':str(error)}))
            else: self.send(404,'{}')
        def do_POST(self):
            if self.headers.get('Origin') not in (None,f'http://127.0.0.1:{port}',f'http://localhost:{port}'):
                self.send(403,'{"error":"Origin rejected"}')
                return
            try:
                size=int(self.headers.get('Content-Length',0))
                if not 0<size<=(20*1024**2 if self.path in ('/api/case-labels','/api/case-context-jobs','/api/interval-snapshot','/api/atlas-interval-revalidate','/api/atlas-interval-apply','/api/atlas-interval-session','/api/candidate-radius-restore') else 65536): raise ValueError('Invalid request size')
                from .case_io import _unique_object
                raw=json.loads(self.rfile.read(size),
                    object_pairs_hook=_unique_object if self.path in ('/api/case-labels','/api/case-context-jobs','/api/interval-snapshot','/api/atlas-interval-revalidate','/api/atlas-interval-apply','/api/atlas-interval-undo','/api/atlas-interval-session') else None)
                if self.path=='/api/atlas-interval-session':
                    from .interval_session import encode_session, decode_session, restore_session
                    with workspace.lock:
                        if not expected_generation_matches(self.headers.get('X-Expected-Generation'),workspace.generation):
                            raise AtlasEditConflict('Scene changed; refresh before session operation')
                        generation=workspace.generation
                        if raw=={'action':'export'}:
                            data,revision=encode_session(workspace)
                            self.send(200,json.dumps(dict(session_text=data.decode(),revision=revision)))
                            return
                        if not isinstance(raw,dict) or set(raw)!={'action','session_text'} or raw['action']!='restore' or not isinstance(raw['session_text'],str):
                            raise ValueError('Invalid interval session request')
                        if workspace.source!='atlas' or workspace.atlas is None:
                            raise ValueError('Atlas unavailable')
                        content,_=decode_session(raw['session_text'],workspace.atlas.metadata.get('sha256'))
                        part_ids=sorted({json.loads(s)['candidate']['part_id'] for s in content['snapshots']})
                    result=restore_session(workspace,raw['session_text'],generation,
                                           lambda:workspace.render_interval_parts(part_ids))
                    self.send(200,json.dumps(result))
                    return
                if self.path in ('/api/atlas-interval-apply','/api/atlas-interval-undo'):
                    from .interval_application import apply_interval, undo_interval
                    from .interval_revalidation import prepare_revalidation
                    with workspace.lock:
                        if not expected_generation_matches(self.headers.get('X-Expected-Generation'),workspace.generation):
                            raise AtlasEditConflict('Scene changed; refresh before interval editing')
                        generation=workspace.generation
                        if self.path.endswith('apply'):
                            if not isinstance(raw,dict) or set(raw)!={'snapshot_text'}:
                                raise ValueError('Snapshot text required')
                            if workspace.source!='atlas' or workspace.atlas is None:
                                raise ValueError('Atlas unavailable')
                            candidate,_,_=prepare_revalidation(raw['snapshot_text'],atlas_sha256=workspace.atlas.metadata.get('sha256'))
                            pid=candidate['part_id']
                        else:
                            if raw!={} or not getattr(workspace,'atlas_interval_undo',[]):
                                raise ValueError('No interval undo available')
                            pid=workspace.atlas_interval_undo[-1]['part_id']
                    render=lambda: workspace.render_interval_part(pid)
                    result=(apply_interval(workspace,raw['snapshot_text'],generation,render)
                            if self.path.endswith('apply') else undo_interval(workspace,generation,render))
                    self.send(200,json.dumps(result))
                    return
                if self.path=='/api/interval-snapshot':
                    from .interval_snapshot import process_snapshot_request
                    with workspace.lock:
                        atlas_sha=workspace.atlas.metadata.get('sha256') if workspace.atlas is not None else None
                    try:
                        self.send(200,json.dumps(process_snapshot_request(raw,expected_atlas_sha256=atlas_sha)))
                    except (ValueError,TypeError,KeyError) as error:
                        self.send(400,json.dumps({'error':str(error)}))
                    return
                if self.path=='/api/case-context-jobs':
                    from .case_io import case_digest,_unique_object
                    if not isinstance(raw,dict) or set(raw)!={'snapshot'}:
                        raise ValueError('One case snapshot required')
                    document=raw['snapshot']
                    if isinstance(document,str):document=json.loads(document,object_pairs_hook=_unique_object)
                    if (not isinstance(document,dict) or set(document)!={'schema','revision','case'}
                            or document['schema']!='vv-toolbox.case-snapshot/1'
                            or case_digest(document['case'])!=document['revision']):
                        raise ValueError('Matching case snapshot required')
                    try:self.send(202,json.dumps(context_jobs.start(document['case'])))
                    except ContextJobBusy as error:self.send(409,json.dumps(dict(error=str(error))))
                    return
                if self.path=='/api/case-labels':
                    from .label_workbench import process_request
                    try:self.send(200,json.dumps(process_request(raw)))
                    except (ValueError,TypeError,KeyError) as error:self.send(400,json.dumps({'error':str(error)}))
                    return
                if self.path=='/api/candidate-radius-restore':
                    from .candidate_radius_io import restore_session
                    from .candidate_radius_app import display,snapshot_context,require_clear_result
                    from .candidate_preview import load_candidate_preview
                    with workspace.lock:
                        if workspace.busy or getattr(workspace,'candidate_radius_busy',False) or not expected_generation_matches(self.headers.get('X-Expected-Generation'),workspace.generation):
                            self.send(409,json.dumps(dict(error='Scene changed or busy',current_generation=workspace.generation)))
                            return
                        session=getattr(workspace,'candidate_radius_session',None)
                        if workspace.source!='candidate' or not workspace.candidate.get('source_centerlines'):
                            raise ValueError('Select the matching carotid candidate before loading')
                        if session and (session.status()['preview_token'] or session.status()['undo_available']):
                            raise ValueError('Discard preview and undo edits before loading')
                        if not isinstance(raw,dict) or set(raw)!={'session_text'} or not isinstance(raw['session_text'],str):
                            raise ValueError('Saved radius session text required')
                        candidate_id=workspace.candidate['summary']['id']
                        context=snapshot_context(workspace,workspace.candidate)
                        generation=workspace.generation
                        workspace.candidate_radius_busy=True
                        workspace.candidate_radius_request=None
                    try:
                        base=load_candidate_preview(Path(__file__).resolve().parents[2],candidate_id)
                        restored=restore_session(base,raw['session_text'],
                            inspect_operation=lambda before,result:require_clear_result(before,result,context))
                        with workspace.lock:
                            if workspace.source!='candidate' or workspace.generation!=generation:
                                raise ValueError('Scene changed during restore; result discarded')
                            display(workspace,restored.current())
                            workspace.candidate_radius_session=restored
                            workspace.generation+=1
                    finally:
                        with workspace.lock:workspace.candidate_radius_busy=False
                    self.send(200,json.dumps(workspace.snapshot()))
                    return
                if self.path=='/api/candidate-radius-preview':
                    from .candidate_radius_app import prepare,publish,snapshot_context,inspect_result
                    with workspace.lock:
                        if workspace.busy or getattr(workspace,'candidate_radius_busy',False) or not expected_generation_matches(self.headers.get('X-Expected-Generation'),workspace.generation):
                            self.send(409,json.dumps(dict(error='Scene changed or busy',current_generation=workspace.generation)))
                            return
                        session,snapshot,generation=prepare(workspace,raw)
                        context=snapshot_context(workspace,snapshot['candidate'])
                        workspace.candidate_radius_busy=True
                        workspace.candidate_radius_progress=dict(phase='geometry',completed=0,total=1)
                        workspace.candidate_radius_request=dict(raw)
                    def radius_progress(event):
                        with workspace.lock:
                            workspace.candidate_radius_progress=dict(event)
                    try:
                        from .disjoint_containment import _SurfaceValidationCache
                        validation_cache=_SurfaceValidationCache()
                        result=session.compute(snapshot,progress=radius_progress,_validation_cache=validation_cache,**{key:raw[key] for key in ('scale','transition_mm','max_displacement_mm')})
                        result=inspect_result(snapshot['candidate'],result,context,progress=radius_progress,_validation_cache=validation_cache)
                        with workspace.lock:
                            publish(workspace,session,generation,result)
                            workspace.candidate_radius_progress=dict(phase='complete')
                    except Exception:
                        with workspace.lock:workspace.candidate_radius_progress=dict(phase='failed')
                        raise
                    finally:
                        with workspace.lock:workspace.candidate_radius_busy=False
                    self.send(200,json.dumps(workspace.snapshot()))
                    return
                if self.path in ('/api/atlas-interval-preview','/api/atlas-interval-revalidate'):
                    from .atlas_interval_preview import preview_interval, snapshot_interval_workspace
                    with workspace.lock:
                        if workspace.busy or getattr(workspace,'interval_preview_busy',False) or not expected_generation_matches(self.headers.get('X-Expected-Generation'),workspace.generation):
                            self.send(409,json.dumps(dict(error='Scene changed or busy; refresh before preview',
                                                         code='generation_conflict',current_generation=workspace.generation)))
                            return
                        revalidation_text=None
                        if self.path=='/api/atlas-interval-revalidate':
                            from .interval_revalidation import prepare_revalidation, revalidate_interval_snapshot
                            if workspace.source!='atlas' or workspace.atlas is None:
                                raise ValueError('Atlas must be available for revalidation')
                            if not isinstance(raw,dict) or set(raw)!={'snapshot_text'} or not isinstance(raw['snapshot_text'],str):
                                raise ValueError('Snapshot text required')
                            revalidation_text=raw['snapshot_text']
                            _,_,raw=prepare_revalidation(revalidation_text,atlas_sha256=workspace.atlas.metadata.get('sha256'))
                        snapshot=snapshot_interval_workspace(workspace,raw)
                        workspace.interval_preview_busy=True
                    try:
                        result=(revalidate_interval_snapshot(snapshot,revalidation_text) if revalidation_text is not None
                                else preview_interval(snapshot,raw))
                    finally:
                        with workspace.lock:
                            workspace.interval_preview_busy=False
                    with workspace.lock:
                        if workspace.generation!=snapshot.generation or workspace.source!='atlas':
                            self.send(409,json.dumps(dict(error='Scene changed while computing; preview discarded',
                                                         code='generation_conflict',current_generation=workspace.generation)))
                            return
                    self.send(200,json.dumps(result))
                    return
                with workspace.lock:
                    if self.path=='/api/candidate-radius-action':
                        from .candidate_radius_app import action
                        if getattr(workspace,'candidate_radius_busy',False) or not expected_generation_matches(self.headers.get('X-Expected-Generation'),workspace.generation):
                            self.send(409,json.dumps(dict(error='Scene changed or busy',current_generation=workspace.generation)))
                            return
                        action(workspace,raw)
                        self.send(200,json.dumps(workspace.snapshot()))
                        return
                    if workspace.source=='candidate' and self.path not in ('/api/source','/api/view','/api/visibility','/api/candidate-selection'):
                        raise ValueError('Candidate preview is read-only')
                    if self.path in ('/api/anatomy','/api/atlas-modification','/api/atlas-interval-preview') and not expected_generation_matches(self.headers.get('X-Expected-Generation'),workspace.generation):
                        self.send(409,json.dumps(dict(error='Anatomy changed or revision is missing; refresh controls before applying edits',
                                                     code='generation_conflict',current_generation=workspace.generation)))
                        return
                    if workspace.busy and self.path!='/api/visibility':
                        self.send(409,'{"error":"Anatomy is rebuilding"}')
                        return
                    if self.path=='/api/atlas-edit-session':
                        try:self.send(200,json.dumps(workspace.update_atlas_edit_session(raw)))
                        except AtlasEditConflict as error:self.send(409,json.dumps({'error':str(error)}))
                        except AtlasEditCheckFailure as error:self.send(422,json.dumps({'error':str(error),'code':'atlas_edit_checks_failed'}))
                        except (ValueError,KeyError,TypeError) as error:self.send(400,json.dumps({'error':str(error)}))
                        except OSError:self.send(503,'{"error":"Local atlas edit storage unavailable; existing data preserved"}')
                        except Exception:self.send(503,'{"error":"Atlas edit scene update failed; inspect workspace state before retrying"}')
                        return
                    elif self.path=='/api/case-workspace':
                        try:
                            current=isinstance(raw,dict) and raw.get('action')=='prepare_current'
                            if current and (workspace.source!='atlas' or
                                    getattr(workspace,'interval_preview_busy',False) or
                                    not expected_generation_matches(self.headers.get('X-Expected-Generation'),workspace.generation)):
                                raise CaseWorkspaceConflict('Current Atlas changed or busy; refresh before capture')
                            parts=([workspace.atlas_modified_parts.get(p['id'],p)
                                    for p in [*workspace.atlas.meshes,*workspace.neck_parts]]
                                   if current and workspace.atlas is not None else None)
                            result=workspace.case_workspace.update(raw,
                                preview=workspace.atlas_centerlines if current else workspace.atlas_original_centerlines,
                                metadata=workspace.atlas.metadata if workspace.atlas is not None else None,
                                surface_parts=parts,modifications=workspace.atlas_modifications,
                                interval_edits=getattr(workspace,'atlas_interval_edits',{}))
                            self.send(200,json.dumps(result))
                        except CaseWorkspaceConflict as error:self.send(409,json.dumps({'error':str(error)}))
                        except (ValueError,KeyError,TypeError) as error:self.send(400,json.dumps({'error':str(error)}))
                        except OSError:self.send(503,'{"error":"Local case storage unavailable; existing data preserved"}')
                        return
                    elif self.path=='/api/atlas-annotations':
                        if workspace.source!='atlas':raise ValueError('Atlas must be active')
                        result=workspace.annotations.update(raw)
                        workspace.clear_annotation_candidate()
                        self.send(200,json.dumps(result))
                        return
                    elif self.path=='/api/annotation-clear':
                        if raw!={}:raise ValueError('Expected empty controls')
                        workspace.clear_annotation_candidate()
                    elif self.path=='/api/annotation-context':
                        if workspace.source!='atlas' or not isinstance(raw,dict) or set(raw)!={'visible'} or type(raw['visible']) is not bool:
                            raise ValueError('Invalid annotation context')
                        workspace.annotation_context_visible=raw['visible']
                        workspace.draw_annotation_context()
                    elif self.path=='/api/annotation-focus':
                        if workspace.source!='atlas' or not isinstance(raw,dict) or set(raw)!={'boundary_id'}:
                            raise ValueError('Invalid annotation focus')
                        try:workspace.focus_annotation_candidate(raw['boundary_id'])
                        except ValueError as error:
                            self.send(400,json.dumps({'error':str(error)}))
                            return
                    elif self.path=='/api/anatomy':
                        if workspace.source!='schematic':
                            raise ValueError('Reference source is read-only')
                        parameters=validate_parameters(raw,workspace.known,workspace.known_venous)
                        workspace.busy=True
                        workspace.error=None
                        threading.Thread(target=workspace.rebuild,args=(parameters,),daemon=True).start()
                    elif self.path=='/api/atlas-modification':
                        workspace.modify_atlas_part(raw)
                    elif self.path=='/api/view':
                        if set(raw)!={'access','target','mode','focus'} or raw['access'] not in ('left_femoral','right_femoral') or raw['target'] not in TARGETS.values() or raw['mode'] not in ('Surface','Centerlines') or raw['focus'] not in FOCUS:
                            raise ValueError('Invalid view')
                        workspace.access,workspace.target,workspace.mode=raw['access'],raw['target'],raw['mode']
                        workspace.draw(workspace.graph,workspace.mesh)
                        workspace.metrics.content=workspace.description(workspace.graph)
                        if workspace.source=='reference':
                            workspace.focus_reference()
                        elif workspace.source=='atlas':
                            workspace.focus_atlas(raw['focus'])
                        elif workspace.source=='candidate':
                            workspace.focus_candidate()
                        else:
                            for c in server.get_clients().values(): c.camera.position,c.camera.look_at=FOCUS[raw['focus']]
                    elif self.path=='/api/source':
                        if getattr(workspace,'atlas_interval_edits',{}):
                            raise AtlasEditConflict('Undo session interval edits before changing anatomy source')
                        if (not isinstance(raw,dict) or 'source' not in raw or
                                set(raw)-{'source','candidate_id'} or
                                ('candidate_id' in raw and (raw['source']!='candidate' or
                                 not isinstance(raw['candidate_id'],str)))):
                            raise ValueError('Invalid source selection')
                        workspace.set_source(raw['source'],candidate_id=raw.get('candidate_id'))
                    elif self.path=='/api/candidate-selection':
                        if not isinstance(raw,dict) or set(raw)!={'source_name'}:
                            raise ValueError('Invalid candidate source selection')
                        workspace.select_candidate_source(raw['source_name'])
                    elif self.path=='/api/atlas-selection':
                        if not isinstance(raw,dict) or set(raw)!={'part_id'}:
                            raise ValueError('Invalid atlas vessel selection')
                        workspace.select_atlas_part(raw['part_id'])
                    elif self.path=='/api/atlas-centerlines-visibility':
                        if not isinstance(raw,dict) or set(raw)!={'visible'} or type(raw['visible']) is not bool:
                            raise ValueError('Invalid centerline visibility')
                        workspace.atlas_centerlines_visible=raw['visible']
                        workspace.update_atlas_centerline_visibility()
                    elif self.path=='/api/visibility':
                        workspace.set_visibility(raw)
                    elif self.path=='/api/atlas-context':
                        if not isinstance(raw,dict) or set(raw)!={'visible'} or type(raw['visible']) is not bool:
                            raise ValueError('Invalid atlas context visibility')
                        workspace.context_visible=raw['visible']
                        for handle in workspace.context_handles:
                            handle.visible=raw['visible']
                    elif self.path=='/api/neck-repairs':
                        if not isinstance(raw,dict) or set(raw)!={'visible'} or type(raw['visible']) is not bool:
                            raise ValueError('Invalid neck reconstruction visibility')
                        workspace.neck_repairs_visible=raw['visible']
                        for layer,handles in workspace.neck_handles.items():
                            for handle in handles:
                                handle.visible=raw['visible'] and workspace.visibility[layer]
                        workspace.update_atlas_centerline_visibility()
                    else:
                        self.send(404,'{}')
                        return
                self.send(202,'{"ok":true}')
            except AtlasEditCheckFailure as error:self.send(422,json.dumps({'error':str(error),'code':'atlas_edit_checks_failed'}))
            except AtlasEditConflict as error:self.send(409,json.dumps({'error':str(error),'code':'atlas_edit_recovery_required'}))
            except AnnotationConflict as error:self.send(409,json.dumps({'error':str(error)}))
            except OSError:self.send(503,'{"error":"Local annotation storage unavailable"}')
            except (ValueError,TypeError,KeyError,AttributeError): self.send(400,'{"error":"Invalid controls"}')
    http.RequestHandlerClass=Handler
    threading.Thread(target=http.serve_forever,daemon=True).start()
    original_stop=server.stop
    def stop():
        http.shutdown()
        http.server_close()
        original_stop()
    server.stop=stop
    return server

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port',type=int,default=8093)
    parser.add_argument('--atlas-edit-session',type=Path,
                        help='Separate local parameter snapshot path (default: Atlas data directory)')
    args=parser.parse_args()
    server=serve(args.port,atlas_edit_session_path=args.atlas_edit_session)
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt: server.stop()

if __name__=='__main__': main()
