"""Loopback-only shared synthetic anatomy workspace."""
import argparse
import copy
import json
import math
import threading
import time
from functools import lru_cache
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import numpy as np
import viser
from .model import generate
from .surface import network_mesh
from .veins import generate_veins, IMV_DRAINAGE, TRANSVERSE_DOMINANCE
from .web_ui import HTML
from .clearance import cross_circuit_clearance

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
    def __init__(self,server,*,load_reference_source=True):
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
        self.reference=None
        self.atlas=None
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
            elif self.source=='atlas':
                graphs={}
            layers={name:dict(nodes={key:value.tolist() for key,value in graphs[name].nodes.items()},edges=[dict(id=edge.name,start=edge.start,end=edge.end) for edge in graphs[name].segments]) if graphs.get(name) else dict(nodes={},edges=[]) for name in LAYERS}
            return dict(generation=self.generation,busy=self.busy,error=self.error,parameters=json.loads(json.dumps(self.parameters)),
                arch_measurement=self.graph.parameters.get('arch_measurement',{}) if self.graph else {},
                nodes=layers['arterial']['nodes'],edges=layers['arterial']['edges'],layers=layers,visibility=dict(self.visibility),
                source=self.source,reference=self.reference_info,atlas=self.atlas_info,atlas_selection=self.atlas_selection,context_visible=self.context_visible,
                atlas_centerlines=dict(self.atlas_centerline_status),atlas_centerlines_visible=self.atlas_centerlines_visible,
                atlas_modifications=copy.deepcopy(self.atlas_modifications),
                neck_repairs=self.neck_info,neck_repairs_visible=self.neck_repairs_visible,
                clearance=self.clearance if self.source=='schematic' else None)

    def export_bundle(self):
        with self.lock:
            if self.source=='atlas':
                return json.dumps(dict(schema='vv-toolbox.atlas-workspace/1',generation=self.generation,
                    atlas=self.atlas_info,visibility=self.visibility,context_visible=self.context_visible,
                    neck_repairs=self.neck_info,neck_repairs_visible=self.neck_repairs_visible,
                    centerlines=self.atlas_centerlines,
                    modifications=self.atlas_modifications,
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

    def description(self,graph):
        if self.source=='atlas':
            count=len(self.atlas_modifications)
            return f'**BodyParts3D · shared-coordinate atlas**\n\n{count} modified vessel(s); source files preserved.\n\nRed arteries · blue veins · translucent organ context.\n\nShape edits are illustrative; junction continuity and collisions are not validated.'
        if self.source=='reference':
            return f"**{self.reference_info['title']}**\n\nOriginal image-derived reference surface and source paths.\n\nStandalone reference; not merged with the synthetic body.\n\nClinical validation: NOT RUN."
        route,length=graph.route(self.access,self.target)
        venous_count=sum(len(g.segments) for g in self.venous.graphs.values()) if self.venous else 0
        return f'**Generation {self.generation}** · {len(graph.segments)} arterial / {venous_count} venous vessels\n\nArterial route {length:,.1f} mm · {len(route)} segments\n\nSYNTHETIC / ILLUSTRATIVE\n\nThree separate circulation layers. Undirected arterial route; not blood flow. All tabs share this workspace.'

    def draw(self,graph,mesh,veins=None,venous_meshes=None):
        if self.source=='atlas':
            self.draw_atlas()
            return
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

    def modify_atlas_part(self,raw):
        from .atlas_modification import deform_part
        from .atlas_centerlines import proximity_links
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
        graph=copy.deepcopy(self.atlas_centerlines)
        graph['edges']=[e for e in graph['edges'] if e['part_id']!=pid]+edges
        graph['nodes']=[n for n in graph['nodes'] if n['kind']!='candidate_attachment']
        nodes={n['id']:n for n in graph['nodes']}
        for edge in edges:
            for end,idx in [('start',0),('end',-1)]:
                nodes[edge[end]]['point']=edge['points'][idx]
                nodes[edge[end]]['radius']=edge['radii'][idx]
        graph['links']=proximity_links(graph['nodes'],graph['edges'])
        graph['summary'].update(nodes=len(graph['nodes']),candidate_links=len(graph['links']))
        reset=parameters==dict(radius_scale=1.,tortuosity=0.,torsion_deg=0.)
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
        self.draw_atlas()
        self.select_atlas_part(pid)
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

    def set_source(self,source):
        if source not in ('schematic','reference','atlas') or (source=='reference' and self.reference is None) or (source=='atlas' and self.atlas is None):
            raise ValueError('Reference source unavailable')
        self.source=source
        self.visibility['arterial']=True
        self.generation+=1
        self.draw(self.graph,self.mesh)
        self.metrics.content=self.description(self.graph)
        if source=='reference':
            self.focus_reference()
        elif source=='atlas':
            self.mode='Surface'
            self.focus_atlas()
        else:
            for client in self.server.get_clients().values():
                client.camera.position,client.camera.look_at=FOCUS['Whole network']

def serve(port=8093):
    http=ThreadingHTTPServer(('127.0.0.1',port),BaseHTTPRequestHandler)
    try:
        server=viser.ViserServer(host='127.0.0.1',port=port+1,label='VV Toolbox · 3D')
        if server.get_port()!=port+1:
            server.stop()
            raise OSError('3D port is occupied')
    except Exception:
        http.server_close()
        raise
    server.gui.configure_theme(dark_mode=True,brand_color=(40,190,185),show_logo=False,show_share_button=False)
    server.scene.set_up_direction('+z')
    server.scene.world_axes.visible=False
    workspace=Workspace(server)
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
            if self.path=='/': self.send(200,HTML.replace('__VISER_PORT__',str(port+1)),'text/html')
            elif self.path=='/api/state': self.send(200,json.dumps(workspace.snapshot()))
            elif self.path=='/api/atlas-centerlines':
                self.send(200 if workspace.atlas_centerlines is not None else 202,json.dumps(workspace.atlas_centerlines or workspace.atlas_centerline_status))
            elif self.path=='/api/export':
                self.send(200,workspace.export_bundle())
            else: self.send(404,'{}')
        def do_POST(self):
            if self.headers.get('Origin') not in (None,f'http://127.0.0.1:{port}',f'http://localhost:{port}'):
                self.send(403,'{"error":"Origin rejected"}')
                return
            try:
                size=int(self.headers.get('Content-Length',0))
                if not 0<size<=65536: raise ValueError('Invalid request size')
                raw=json.loads(self.rfile.read(size))
                with workspace.lock:
                    if self.path in ('/api/anatomy','/api/atlas-modification') and not expected_generation_matches(self.headers.get('X-Expected-Generation'),workspace.generation):
                        self.send(409,json.dumps(dict(error='Anatomy changed or revision is missing; refresh controls before applying edits',
                                                     code='generation_conflict',current_generation=workspace.generation)))
                        return
                    if workspace.busy and self.path!='/api/visibility':
                        self.send(409,'{"error":"Anatomy is rebuilding"}')
                        return
                    if self.path=='/api/anatomy':
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
                        else:
                            for c in server.get_clients().values(): c.camera.position,c.camera.look_at=FOCUS[raw['focus']]
                    elif self.path=='/api/source':
                        if not isinstance(raw,dict) or set(raw)!={'source'}:
                            raise ValueError('Invalid source selection')
                        workspace.set_source(raw['source'])
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
    server=serve(parser.parse_args().port)
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt: server.stop()

if __name__=='__main__': main()
