"""Reproducible native-coordinate inspection, not anatomical boundary approval.

Run in Docker with numpy, scipy and matplotlib. Research use only, not for
clinical decision. Nearest vertex pairs are inspection locators, not junctions.
"""
from pathlib import Path
import hashlib
import json
import zipfile
import urllib.request

import numpy as np
from scipy.spatial import cKDTree
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'reference-data/bodyparts3d'
IDS = ['FJ1742', 'FJ1748', 'FJ1749', 'FJ1655', 'FJ1654', 'FJ1654M',
       'FJ1692', 'FJ1692M', 'FJ1660', 'FJ1660M', 'FJ1694', 'FJ1694M',
       'FJ1699', 'FJ1699M', 'FJ1676', 'FJ1676M']


def inspect():
    archive = SOURCE / 'isa_BP3D_4.0_obj_99.zip'
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    manifest = json.loads((SOURCE / 'acquisition.json').read_text())
    if digest != manifest['files'][archive.name]['sha256']:
        raise ValueError('Source archive fingerprint mismatch')
    meshes, assets = {}, []
    with zipfile.ZipFile(archive) as z:
        for ident in IDS:
            names = [n for n in z.namelist() if Path(n).name == ident + '.obj']
            if len(names) != 1:
                raise ValueError(f'Expected exactly one OBJ for {ident}')
            raw = z.read(names[0])
            lines = raw.decode().splitlines()
            vertices = np.array([list(map(float, s.split()[1:4])) for s in lines if s.startswith('v ')])
            faces = []
            for line in lines:
                if line.startswith('f '):
                    indices = [int(v.split('/')[0]) - 1 for v in line.split()[1:]]
                    for i in range(1, len(indices) - 1):
                        faces.append([indices[0], indices[i], indices[i+1]])
            faces = np.array(faces)
            assert vertices.ndim == 2 and vertices.shape[1] == 3 and np.isfinite(vertices).all()
            assert faces.min() >= 0 and faces.max() < len(vertices)
            meshes[ident] = (vertices, faces)
            assets.append(dict(element_id=ident, obj_sha256=hashlib.sha256(raw).hexdigest(),
                vertices=len(vertices), triangles=len(faces), bounds=[vertices.min(0).tolist(), vertices.max(0).tolist()]))
    locators = []
    for side, aca in [('R', 'FJ1654'), ('L', 'FJ1654M')]:
        av = meshes['FJ1655'][0]
        distance, index = cKDTree(meshes[aca][0]).query(av)
        k = int(np.argmin(distance))
        locators.append(dict(boundary_id=f'B.{side}.ACA.A1_A2', kind='closest_source_vertex_pair',
            source_element_ids=['FJ1655', aca],
            acom_vertex_index=k, aca_vertex_index=int(index[k]),
            acom_position_native=av[k].tolist(), aca_position_native=meshes[aca][0][index[k]].tolist(),
            candidate_position=meshes[aca][0][index[k]].tolist(),
            coordinate_frame_id='bodyparts3d_native_LPS', units='mm',
            source_refs=[f'{ident}:sha256:{next(a["obj_sha256"] for a in assets if a["element_id"] == ident)}'
                         for ident in ['FJ1655', aca]],
            separation_native_units=float(distance[k]), anatomical_boundary_approved=False,
            limitation='Nearest surface vertices are not a lumen center or proof of attachment.'))
    export = ROOT / 'exports/cerebral-boundary-inspection'
    export.mkdir(parents=True, exist_ok=True)
    coordinate_reference = export / 'coordinate_system.png'
    if not coordinate_reference.exists():
        urllib.request.urlretrieve('https://dbarchive.biosciencedbc.jp/data/bodyparts3d/20130619/coordinate_system.png', coordinate_reference)
    if hashlib.sha256(coordinate_reference.read_bytes()).hexdigest() != '338736275c11eac8c89531fdc14193c9a8adf5baab674033d9d89259f152a5f6':
        raise ValueError('Coordinate reference fingerprint mismatch')
    images = []
    groups = {
        'aca-callosum': ['FJ1742', 'FJ1654', 'FJ1654M', 'FJ1655', 'FJ1699', 'FJ1699M', 'FJ1676', 'FJ1676M'],
        'mca-insula': ['FJ1748', 'FJ1749', 'FJ1692', 'FJ1692M', 'FJ1660', 'FJ1660M', 'FJ1694', 'FJ1694M'],
        'acom-closeup': ['FJ1654', 'FJ1654M', 'FJ1655'],
    }
    colors = {'FJ1742':'#96a5b2', 'FJ1748':'#9bba9d', 'FJ1749':'#9bba9d',
        'FJ1654':'#bf3238', 'FJ1654M':'#df9140', 'FJ1655':'#127ad1',
        'FJ1692':'#bf3238', 'FJ1692M':'#bf3238', 'FJ1660':'#df9140',
        'FJ1660M':'#df9140', 'FJ1694':'#7b4ca0', 'FJ1694M':'#7b4ca0',
        'FJ1699':'#bf3238', 'FJ1699M':'#df9140', 'FJ1676':'#7b4ca0', 'FJ1676M':'#7b4ca0'}
    for name, ids in groups.items():
        fig, axes = plt.subplots(1, 3, figsize=(17, 7))
        for ax, (a, b) in zip(axes, [(0,1),(0,2),(1,2)]):
            for ident in ids:
                vertices, faces = meshes[ident]
                polys = vertices[faces][:, :, [a,b]]
                ax.add_collection(PolyCollection(polys, facecolors=colors[ident], edgecolors='none',
                    alpha=0.2 if ident in ['FJ1742','FJ1748','FJ1749'] else 0.75))
            ax.autoscale_view()
            if name == 'acom-closeup':
                lo, hi = meshes['FJ1655'][0].min(0), meshes['FJ1655'][0].max(0)
                ax.set_xlim(lo[a]-7,hi[a]+7)
                ax.set_ylim(lo[b]-7,hi[b]+7)
                for item in locators:
                    p = item['aca_position_native']
                    ax.plot(p[a],p[b],'kx',ms=9)
                    ax.annotate(item['boundary_id'].split('.')[1],(p[a],p[b]))
            ax.set_aspect('equal')
            ax.set_xlabel('XYZ'[a] + ' (native mm)')
            ax.set_ylabel('XYZ'[b] + ' (native mm)')
            ax.grid(alpha=.2)
        fig.suptitle(name + ' | Native mesh projections; no approved anatomical coordinates\n' +
                     ', '.join(ident + ': ' + colors[ident] for ident in ids), fontsize=10)
        fig.tight_layout()
        path = export / (name + '.png')
        fig.savefig(path, dpi=160)
        plt.close(fig)
        images.append(dict(path=str(path.relative_to(ROOT)),sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    result = dict(schema='vv_toolbox.cerebral_boundary_adjudication/1',
        source_archive_sha256=digest, coordinate_frame_id='bodyparts3d_native_LPS',
        units='mm', units_confirmed=True, frame_confirmed=True,
        coordinate_reference=dict(url='https://dbarchive.biosciencedbc.jp/data/bodyparts3d/20130619/coordinate_system.png',
            sha256=hashlib.sha256(coordinate_reference.read_bytes()).hexdigest(),
            interpretation='Native +X left, +Y posterior, +Z superior; native origin preserved; not a DICOM patient affine.'),
        assets=assets, inspection_locators=locators, figures=images,
        approved_boundary_count=0,
        boundaries=[dict(boundary_id=f'B.{side}.{artery}.{transition}',position=None,
            evidence_status='unresolved', reason=reason)
            for side in ['L','R'] for artery,transition,reason in [
                ('ACA','A1_A2','ACom proximity inspected; exact lumen center/attachment plane unconfirmed.'),
                ('ACA','A2_A3','Callosal surface available; rostrum-genu boundary not independently annotated.'),
                ('ACA','A3_A4','Callosal surface available; superior course transition requires source-specific annotation.'),
                ('MCA','M1_M2','Insula and sphenoid/insular named parts available; limen/genu landmark unconfirmed.'),
                ('MCA','M2_M3','Insula perimeter alone does not identify each insular-opercular crossing.'),
                ('MCA','M3_M4','Sylvian cortical exit and operculum labels not available in inspected source tables.')]])
    target = ROOT / 'docs/evidence/cerebral-boundary-adjudication.json'
    target.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(assets=len(assets), locators=locators, approved=0, figures=images)))


if __name__ == '__main__':
    inspect()
