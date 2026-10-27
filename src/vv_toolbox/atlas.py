"""Original BodyParts3D atlas elements in one unchanged source coordinate frame."""
import csv
from dataclasses import dataclass
from functools import lru_cache
import hashlib
import io
from pathlib import Path
import zipfile

import numpy as np
from scipy.spatial import cKDTree

ROOT=Path(__file__).resolve().parents[2]/'reference-data'/'bodyparts3d'
PINNED={
 'isa_BP3D_4.0_obj_99.zip':'40665852c49f218326590e204db91064a1ecfc3c6f8cbd7bbbcaac62c7cd409e',
 'isa_parts_list_e.txt':'ab7796deedd49205e77f3609a1cb8c53e2bbee14ecb5c9a6ca05227469780513',
 'isa_element_parts.txt':'a3de74423f943b0d724ae8f59b3a817f87c423a544f8db98113b1980817cbeaf',
 'partof_parts_list_e.txt':'9224080557053e6f1322f1e13ab27f0ecde0db19bb3b505f0631afad230eeebd',
 'partof_element_parts.txt':'3f5f6df1028eb122b30de77c711597b6bb8e5541658e5985859fd228adbf88ea',
 'README_e.html':'f9a90b4d945ad0fe50db45c712e931aa54e52667187b30d7085b6cc394f40107',
 'LICENSE.html':'7bbf53a72b44fdc32f08af98f1d474acf0363a82fa4f1de1c7889206f69783ea',
}
GROUPS={'arterial':('isa','FMA66464'),'systemic_venous':('isa','FMA66644'),
        'hepatic_portal':('isa','FMA66645'),'context':('partof','FMA7088')}
# IS-A's systemic artery/vein concepts omit central trunks. Add these explicitly
# from the same official table, never by an anatomical coordinate guess.
CENTRAL={'arterial':{'FMA3736','FMA3768','FMA3784','FMA3789'},
         'systemic_venous':{'FMA4720','FMA10951'}}
# FMA separates vessel regions/trunks/zones from whole artery/vein organs.
# These explicit vascular classes restore native pieces otherwise omitted by
# the whole-organ categories; none are synthesized or spatially repositioned.
VASCULAR_SUBDIVISIONS={
 'arterial':{'FMA49918','FMA3711','FMA86256','FMA66332','FMA14177','FMA71537','FMA3728'},
 'systemic_venous':{'FMA22917','FMA3729'},
 'hepatic_portal':{'FMA14329'},
}
ATTRIBUTION='BodyParts3D, © The Database Center for Life Science licensed under CC Attribution 4.0 International'


def parse_obj(data):
    """Preserve original positions; triangulate OBJ polygons without repositioning."""
    vertices=[];faces=[]
    for line in data.decode('utf-8-sig').splitlines():
        tokens=line.split()
        if not tokens:continue
        if tokens[0]=='v':
            vertices.append([float(x) for x in tokens[1:4]])
        elif tokens[0]=='f':
            indices=[]
            for token in tokens[1:]:
                index=int(token.split('/')[0])
                if index==0:raise ValueError('OBJ indices are one-based')
                indices.append(index-1 if index>0 else len(vertices)+index)
            if len(indices)<3:raise ValueError('Invalid OBJ polygon')
            faces.extend((indices[0],indices[i],indices[i+1]) for i in range(1,len(indices)-1))
    v=np.asarray(vertices,dtype=np.float32);f=np.asarray(faces,dtype=np.int64)
    if v.ndim!=2 or v.shape[1]!=3 or f.ndim!=2 or f.shape[1]!=3 or not np.isfinite(v).all() or f.min()<0 or f.max()>=len(v):
        raise ValueError('Invalid atlas mesh')
    return v,f.astype(np.uint32)


def groups_from_tables(tables):
    groups={};labels={}
    for tree,rows in tables.items():
        concepts={}
        for row in rows:
            concepts.setdefault(row['concept id'],set()).add(row['element file id'])
        for row in rows:
            element=row['element file id']
            candidate=(len(concepts[row['concept id']]),row['name'],row['concept id'])
            labels.setdefault(element,[]).append(candidate)
        for layer,(selected_tree,concept) in GROUPS.items():
            if tree==selected_tree:
                groups[layer]=concepts[concept]
        if tree=='isa':
            for layer in GROUPS:
                concept_ids=CENTRAL.get(layer,set())|VASCULAR_SUBDIVISIONS.get(layer,set())
                for concept in concept_ids:
                    groups[layer]=groups[layer]|concepts.get(concept,set())
    if groups['hepatic_portal'] & groups['systemic_venous']:
        raise ValueError('Atlas classification overlaps portal and systemic venous elements')
    if groups['arterial'] & (groups['systemic_venous']|groups['hepatic_portal']):
        raise ValueError('Atlas arterial and venous element classification overlaps')
    # Heart context must not draw the same coronary-vessel element twice.
    groups['context']-=groups['arterial']|groups['systemic_venous']|groups['hepatic_portal']
    chosen={element:min(candidates) for element,candidates in labels.items()}
    central_concepts=set().union(*CENTRAL.values())
    for row in tables['isa']:
        if row['concept id'] in central_concepts:
            chosen[row['element file id']]=(1,row['name'],row['concept id'])
    return groups,chosen


@dataclass
class AtlasReference:
    meshes: list
    metadata: dict
    camera: tuple
    focus_bounds: dict


@lru_cache(maxsize=1)
def load_atlas():
    for name,expected in PINNED.items():
        path=ROOT/name
        if not path.is_file():
            raise FileNotFoundError('BodyParts3D reference unavailable; run scripts/acquire_atlas.py explicitly')
        with path.open('rb') as stream:
            actual=hashlib.file_digest(stream,'sha256').hexdigest()
        if actual!=expected:
            raise ValueError('Pinned atlas source hash mismatch: '+name)
    tables={tree:list(csv.DictReader(io.StringIO((ROOT/f'{tree}_element_parts.txt').read_text(encoding='utf-8')),delimiter='\t')) for tree in ('isa','partof')}
    groups,labels=groups_from_tables(tables)
    memberships={}
    for tree,rows in tables.items():
        for row in rows:
            memberships.setdefault(row['element file id'],[]).append(dict(tree=tree,concept_id=row['concept id'],name=row['name']))
    meshes=[];parts=[]
    with zipfile.ZipFile(ROOT/'isa_BP3D_4.0_obj_99.zip') as archive:
        by_id={Path(name).stem:name for name in archive.namelist() if name.endswith('.obj')}
        for layer,elements in groups.items():
            for element in sorted(elements):
                if element not in by_id:raise ValueError('Missing atlas element: '+element)
                data=archive.read(by_id[element]);v,f=parse_obj(data)
                _,name,concept=labels[element]
                meshes.append(dict(id=element,name=name,layer=layer,vertices=v,faces=f,concept_memberships=memberships.get(element,[])))
                parts.append(dict(id=element,name=name,layer=layer,concept_id=concept,source_file=by_id[element],
                                  sha256=hashlib.sha256(data).hexdigest(),vertices=len(v),triangles=len(f),
                                  bounds_source=[v.min(axis=0).tolist(),v.max(axis=0).tolist()]))
    all_vertices=np.concatenate([mesh['vertices'] for mesh in meshes])
    low,high=all_vertices.min(axis=0),all_vertices.max(axis=0)
    center=(low+high)/2000;span=float((high-low).max())/1000
    focus_bounds={}
    focus_concepts={'Aortic arch':{'FMA3736','FMA3768','FMA4720','FMA4751','FMA4761'},
                    'Femoral bifurcation':{'FMA3789','FMA18805','FMA18806'},
                    'Abdominal':{'FMA3789','FMA10951','FMA66645'}}
    for label,concepts in focus_concepts.items():
        elements={row['element file id'] for row in tables['isa'] if row['concept id'] in concepts}
        vertices=[part['vertices'] for part in meshes if part['id'] in elements]
        if vertices:
            combined=np.concatenate(vertices)
            focus_bounds[label]=[combined.min(axis=0).tolist(),combined.max(axis=0).tolist()]
    neck_concepts={'FMA3941','FMA4058','FMA3949','FMA4062','FMA3958','FMA4066','FMA4754','FMA4762'}
    neck_elements={row['element file id'] for row in tables['isa'] if row['concept id'] in neck_concepts}
    head_neck=[part['vertices'] for part in meshes if part['layer']!='context' and
               (part['id'] in neck_elements or part['vertices'][:,2].max()>=1400)]
    if head_neck:
        combined=np.concatenate(head_neck)
        focus_bounds['Cerebral']=[combined.min(axis=0).tolist(),combined.max(axis=0).tolist()]
    by_id={part['id']:part for part in meshes}
    neck_gaps={}
    for side,common,internal in [('right','FJ3564','FJ1682'),('left','FJ3483','FJ1682M')]:
        a,b=by_id[common]['vertices'],by_id[internal]['vertices']
        neck_gaps[side]=dict(common_carotid_element=common,internal_carotid_element=internal,
            status='SOURCE GAP',vertical_separation_source_units=float(b[:,2].min()-a[:,2].max()),
            nearest_vertex_distance_source_units=float(cKDTree(a).query(b)[0].min()),
            note='Both original elements are included. Vertex proximity is not an exact surface distance or a clinical measurement.')
    metadata=dict(available=True,title='BodyParts3D 4.0 · shared-coordinate vascular atlas',kind='anatomical-atlas-reference',
        source_url='https://dbarchive.biosciencedbc.jp/en/bodyparts3d/download.html',
        license='CC BY 4.0 per current official distribution license (2025-02-27)',attribution=ATTRIBUTION,
        license_url='https://dbarchive.biosciencedbc.jp/en/bodyparts3d/lic.html',
        historical_header='Original OBJ headers retain CC BY-SA 2.1 Japan. Preserved unchanged; current official license page is archived alongside source.',
        units='mm assumed from atlas convention; OBJ units not encoded',
        unit_evidence='Original atlas numeric positions retained. Official modeling notes give source imaging dimensions in mm; OBJ itself has no unit declaration. Absolute scale is not clinically verified.',
        coordinates='One original BodyParts3D coordinate frame; no individual translation, rotation, scaling, registration or vessel fusion',
        neck_discontinuity=dict(status='SOURCE GAP',carotids=neck_gaps,
            internal_jugular_elements=['FJ3585','FJ3485'],vertebral_elements=['FJ1725','FJ1725M'],
            interpretation='Source neck elements are already included; their original extents do not supply continuous neck-to-head lumens. No invented bridging geometry is added.'),
        parts=parts,focus_bounds=focus_bounds,coverage={layer:len(elements) for layer,elements in groups.items()},
        source_groups={layer:[concept,*sorted(CENTRAL.get(layer,set())|VASCULAR_SUBDIVISIONS.get(layer,set()))] for layer,(_,concept) in GROUPS.items()},
        source_coverage_notes='Selection includes whole systemic vessels plus separately classified arterial segments, zones, trunks, anastomoses and portal trunks. Original dural sinus/cerebral venous meshes are absent from this 4.0 selection and metadata; estimates belong to a separate overlay.',
        provenance=dict(kind='anatomical-atlas-reference',anatomy_validated=False,individual_patient_model=False,version='4.0',polygon_reduction_percent=99),
        sha256=PINNED['isa_BP3D_4.0_obj_99.zip'],
        limits='Single atlas; source neck-to-head gaps remain. 99% polygon reduction, small vessels may be coarse. Mesh adjacency is not verified lumen connectivity. No flow, contact or clinical validation.',
        metrics=dict(parts=len(parts),vertices=len(all_vertices),triangles=sum(len(x['faces']) for x in meshes),bounds_source=[low.tolist(),high.tolist()]))
    return AtlasReference(meshes,metadata,(tuple(map(float,center+np.array([0,-span*1.3,span*.08]))),tuple(map(float,center))),focus_bounds)
