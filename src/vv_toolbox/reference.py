"""Offline VMR source reference. Original surface and independent authored paths."""
import base64
from dataclasses import dataclass
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import zlib

import numpy as np
from .model import Segment
from .morphometry import centerline_metrics

DATA_ROOT = Path(__file__).resolve().parents[2] / 'reference-data' / 'vmr-0011'
SOURCE_URL = 'https://purl.stanford.edu/kd053sz6270'
MANIFEST_SHA256 = '4b415d908e260056e5b7cb0295b85e104e15ce894421f809a686fe496a655abe'
PATHS = {'aorta':'aorta_final', 'btrunk':'btrunk_final', 'carotid':'carotid_final_short',
         'rt_carotid':'rt_carotid_final_short', 'subclavian':'subclavian_final'}
COORDINATES = 'Source-native axes; anatomical orientation UNKNOWN; source cm converted to mm, no registration'


def xml_document(data):
    # SimVascular legacy files have two top-level elements (format + content).
    text=data.decode('utf-8-sig')
    if text.lstrip().startswith('<?xml'):
        text=text[text.index('?>')+2:]
    return ET.fromstring('<document>'+text+'</document>')


def xyz(element):
    return np.array([float(element.get(axis)) for axis in 'xyz'])


def contour_area(points):
    """Area of a planar closed 3-D polygon, independent of coordinate orientation."""
    points=np.asarray(points,dtype=float)
    if len(points)<3 or not np.isfinite(points).all():
        raise ValueError('Invalid contour')
    centered=points-points.mean(axis=0)
    area=float(np.linalg.norm(np.cross(centered,np.roll(centered,-1,axis=0)).sum(axis=0))/2)
    if not area>0:
        raise ValueError('Zero contour area')
    return area


def read_vtp(data):
    root=ET.fromstring(data)
    if root.get('byte_order')!='LittleEndian' or root.get('header_type')!='UInt32' or root.get('compressor')!='vtkZLibDataCompressor':
        raise ValueError('Unsupported source VTP encoding')
    appended=root.find('AppendedData')
    if appended is None or appended.get('encoding')!='base64':
        raise ValueError('Expected base64 appended VTP')
    encoded=''.join(appended.text.split()).removeprefix('_')
    def array(element):
        payload=encoded[int(element.get('offset')):]
        blocks=int(np.frombuffer(base64.b64decode(payload[:16]),dtype='<u4')[0])
        hlen=4*((4*(3+blocks)+2)//3)
        header=np.frombuffer(base64.b64decode(payload[:hlen]),dtype='<u4')
        sizes=header[3:]
        total=int(sizes.sum())
        packed=base64.b64decode(payload[hlen:hlen+4*((total+2)//3)])
        parts=[]; cursor=0
        for size in sizes:
            parts.append(zlib.decompress(packed[cursor:cursor+int(size)]));cursor+=int(size)
        raw=b''.join(parts)
        expected=(blocks-1)*int(header[1])+int(header[2]) if blocks else 0
        if len(raw)!=expected:
            raise ValueError('VTP decompressed length mismatch')
        dtype={'Float32':'<f4','Float64':'<f8','Int64':'<i8','Int32':'<i4'}[element.get('type')]
        return np.frombuffer(raw,dtype=dtype)
    piece=root.find('.//Piece')
    vertices=array(piece.find('Points/DataArray')).reshape(-1,3).astype(np.float64)*10
    indices=array(piece.find("Polys/DataArray[@Name='connectivity']"))
    offsets=array(piece.find("Polys/DataArray[@Name='offsets']"))
    if not np.all(np.diff(np.r_[0,offsets])==3):
        raise ValueError('Reference surface is not all triangles')
    faces=indices.reshape(-1,3).astype(np.uint32)
    if not np.isfinite(vertices).all() or faces.max()>=len(vertices):
        raise ValueError('Invalid source surface')
    return vertices.astype(np.float32),faces


@dataclass
class ReferencePaths:
    nodes: dict
    segments: list
    parameters: dict
    license_text: str

    def to_json(self):
        return json.dumps(dict(schema='vv-toolbox.reference-paths/1',units='mm',coordinates=COORDINATES,
            provenance=dict(kind='image-derived-reference',patient_derived=True,anatomy_validated=False,source_url=SOURCE_URL),
            license=self.license_text,
            topology='Independent source modeling paths; junction attachment UNVERIFIED; no artificial connectors',
            parameters=self.parameters,nodes={k:v.tolist() for k,v in self.nodes.items()},
            segments=[dict(id=e.name,start=e.start,end=e.end,points_mm=e.points.tolist(),radius_mm=e.radius_mm,
                           radius_profile_mm=e.radius_profile_mm.tolist()) for e in self.segments]),allow_nan=False)


@dataclass
class SourceReference:
    graph: ReferencePaths
    mesh: tuple
    metadata: dict
    camera: tuple


@lru_cache(maxsize=1)
def load_reference():
    manifest_path=DATA_ROOT/'acquisition.json'
    if not manifest_path.is_file():
        raise FileNotFoundError('VMR reference unavailable; run scripts/acquire_reference.py explicitly')
    record=json.loads(manifest_path.read_text())
    required={'Models/0094_0001.vtp','Models/0094_0001.mdl','0011_H_AO_H.pdf','source-manifest.xml','README-COPYRIGHT'}
    required.update(f'Paths/{name}.pth' for name in PATHS)
    required.update(f'Segmentations/{name}.ctgr' for name in PATHS.values())
    if set(record['files'])!=required:
        raise ValueError('Reference acquisition file list mismatch')
    source_manifest=(DATA_ROOT/'source-manifest.xml').read_bytes()
    if hashlib.sha256(source_manifest).hexdigest()!=MANIFEST_SHA256:
        raise ValueError('Pinned source manifest mismatch')
    source_files=ET.fromstring(source_manifest)
    for name,entry in record['files'].items():
        content=(DATA_ROOT/name).read_bytes()
        if hashlib.sha256(content).hexdigest()!=entry['sha256']:
            raise ValueError('Reference hash mismatch: '+name)
        original=source_files.find(f".//file[@id='0011_H_AO_H/{name}']")
        if original is not None and hashlib.sha1(content).hexdigest()!=original.find("checksum[@type='sha1']").text:
            raise ValueError('Pinned source file mismatch: '+name)
    mesh=read_vtp((DATA_ROOT/'Models/0094_0001.vtp').read_bytes())
    nodes={}; segments=[]; metrics={}
    for name,contour_name in PATHS.items():
        path=xml_document((DATA_ROOT/f'Paths/{name}.pth').read_bytes())
        points=np.array([xyz(x) for x in path.findall('.//path_points/path_point/pos')])*10
        arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(points,axis=0),axis=1))]
        contours=xml_document((DATA_ROOT/f'Segmentations/{contour_name}.ctgr').read_bytes())
        positions=[]; radii=[]
        for contour in contours.findall('.//contour'):
            position=xyz(contour.find('path_point/pos'))*10
            polygon=np.array([xyz(x) for x in contour.findall('contour_points/point')])*10
            positions.append(arc[np.argmin(np.linalg.norm(points-position,axis=1))])
            radii.append(np.sqrt(contour_area(polygon)/np.pi))
        order=np.argsort(positions); positions=np.asarray(positions)[order];radii=np.asarray(radii)[order]
        if np.any(np.diff(positions)<=0):
            raise ValueError('Ambiguous source contour ordering')
        profile=np.interp(arc,positions,radii)
        start,end=name+'_source_start',name+'_source_end'
        nodes[start],nodes[end]=points[0].copy(),points[-1].copy()
        segments.append(Segment(name,start,end,points,float(np.median(profile)),profile))
        metrics[name]=dict(length_mm=float(arc[-1]),contours=len(radii),radius_min_mm=float(radii.min()),radius_max_mm=float(radii.max()),
                           centerline=centerline_metrics(points),
                           radius_definition='sqrt(planar source contour area/pi); arc-length interpolation; endpoint holding outside contour coverage',
                           contour_coverage_mm=[float(positions[0]),float(positions[-1])])
    graph=ReferencePaths(nodes,segments,dict(source='VMR 0011_H_AO_H',source_axes='UNKNOWN',source_unit_assessment='cm inferred from source manifest filename and convention',radius_method='area-equivalent source contour radius'),
        (DATA_ROOT/'README-COPYRIGHT').read_text(encoding='utf-8'))
    vertices,faces=mesh
    center=(vertices.min(axis=0)+vertices.max(axis=0))/2/1000
    span=float(np.ptp(vertices,axis=0).max())/1000
    metadata=dict(available=True,title='VMR 0011_H_AO_H · original MR-derived aorta',kind='image-derived-reference',source_url=SOURCE_URL,
        license='VMR custom research-and-development license; preserve README-COPYRIGHT',units='mm (source cm inferred)',
        source_units='cm',unit_evidence='Source manifest names image OSMSC0094-cm.vti; SimVascular cm convention. Geometry files contain no explicit unit attribute.',
        coordinates=COORDINATES,case_status='Adult age 23; repository-labelled Healthy control, no procedure; single case, not population normal',
        sha256=record['files']['Models/0094_0001.vtp']['sha256'],metrics=dict(paths=metrics,vertices=len(vertices),triangles=len(faces),
            independent_paths=len(segments),total_sampled_path_length_mm=sum(e.length_mm for e in segments),
            contour_count=sum(m['contours'] for m in metrics.values()),
            contour_radius_min_mm=min(m['radius_min_mm'] for m in metrics.values()),
            contour_radius_max_mm=max(m['radius_max_mm'] for m in metrics.values()),
            branch_angles=dict(status='UNKNOWN',reason='Source path attachments and branch landmarks not registered'),
            arch_type=dict(status='UNKNOWN',reason='Anatomical axes and classification landmarks not verified')),
        topology='Independent source paths; attachment UNVERIFIED',radius_note='Contour area-equivalent radius, not maximal-inscribed sphere or exact cross-section reconstruction')
    return SourceReference(graph,mesh,metadata,(tuple(map(float,center+np.array([0,-span*1.7,span*.15]))),tuple(map(float,center))))
