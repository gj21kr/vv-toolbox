"""Compare full sampled centerline containment and perpendicular cross sections."""
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen
from copy import deepcopy
import numpy as np
import trimesh

from vv_toolbox.atlas import load_atlas
from vv_toolbox.atlas_modification import deform_part
from vv_toolbox.projected_annulus import contains
from inspect_iliac_normal_sections import section_metrics

ROOT = Path(__file__).resolve().parents[1]


def sections(mesh, edge):
    points = np.asarray(edge['points'], dtype=float)
    output = []
    for i in range(1, len(points)-1):
        normal = points[i+1]-points[i-1]
        length = np.linalg.norm(normal)
        row = dict(index=i, stored_radius_mm=edge['radii'][i], status='UNKNOWN')
        if length <= 1e-12:
            row['reason'] = 'zero tangent'
            output.append(row)
            continue
        normal /= length
        u = np.cross(normal, np.eye(3)[np.argmin(abs(normal))])
        u /= np.linalg.norm(u)
        basis = np.array([u, np.cross(normal, u)]).T
        section = mesh.section(plane_origin=points[i], plane_normal=normal)
        contours = [] if section is None else section.discrete
        closed = [p for p in contours if len(p) >= 4 and np.linalg.norm(p[-1]-p[0]) <= 1e-6]
        enclosing = [(p-points[i])@basis for p in closed
                     if contains((p-points[i])@basis, np.zeros((1,2)))[0]]
        row.update(contours=len(contours), closed_contours=len(closed),
                   enclosing_contours=len(enclosing))
        if len(enclosing) == 1:
            xy = enclosing[0]
            lengths = np.linalg.norm(np.diff(xy, axis=0), axis=1)
            if np.any(lengths <= 1e-12):
                row['reason'] = 'degenerate section interval'
            else:
                row.update(status='MEASURED', metrics=section_metrics(xy))
        else:
            row['reason'] = 'no unique closed contour enclosing centerline point'
        output.append(row)
    return output


def containment(mesh, points):
    if not mesh.is_watertight:
        return dict(status='UNKNOWN', reason='non-watertight surface', point_count=len(points))
    inside = mesh.contains(points)
    return dict(status='MEASURED', point_count=len(points), inside_count=int(inside.sum()),
                outside_indices=np.flatnonzero(~inside).tolist(),
                limitation='Finite precision ray test at sampled points only; boundary points may classify outside.')


def load_candidate():
    prior = json.loads((ROOT/'docs/evidence/atlas-mca-protected-edit-surroundings-width8-product-v3-polyline-flow32-subdiv1.json').read_text())
    with urlopen('http://127.0.0.1:8093/api/export', timeout=30) as response:
        raw = response.read()
    if hashlib.sha256(raw).hexdigest() != prior['input_export_sha256']:
        raise ValueError('Frozen export mismatch')
    bundle = json.loads(raw)
    atlas = load_atlas()
    part = deepcopy(next(p for p in atlas.meshes if p['id'] == prior['part_id']))
    if atlas.metadata['sha256'] != prior['archive_sha256']:
        raise ValueError('Frozen atlas mismatch')
    edges = [e for e in bundle['centerlines']['edges'] if e['part_id'] == part['id']]
    part['vertices'], part['faces'] = trimesh.remesh.subdivide(part['vertices'], part['faces'])
    edited, paths = deform_part(part, edges, prior['parameters'],
        protected_regions=prior['protected_regions'], anchor_blend='product',
        field_version='v3', radial_mode='polyline', integration_steps=32,
        field_support_mm=prior['deformation_method']['field_support_mm'])
    meshes = [trimesh.Trimesh(p['vertices'], p['faces'], process=False) for p in (part, edited)]
    for name, mesh in zip(('before','after'), meshes):
        digest = hashlib.sha256(np.asarray(mesh.vertices[mesh.faces], dtype='<f8').tobytes()).hexdigest()
        if digest != prior['surface_sha256'][name]:
            raise ValueError('Inspected surface differs from frozen candidate')
    return prior, part, edited, edges, paths, meshes


def main():
    prior, part, edited, edges, paths, meshes = load_candidate()
    rows = []
    for original, changed in zip(edges, paths):
        row = dict(edge_id=original['id'], before=sections(meshes[0], original),
                   after=sections(meshes[1], changed))
        for a, b in zip(row['before'], row['after']):
            if a['status'] == b['status'] == 'MEASURED':
                b['measured_area_radius_scale'] = b['metrics']['area_equivalent_radius_mm']/a['metrics']['area_equivalent_radius_mm']
                b['reported_radius_scale'] = b['stored_radius_mm']/a['stored_radius_mm']
        rows.append(row)
    report = dict(part_id=part['id'], parameters=prior['parameters'],
                  surface_sha256=prior['surface_sha256'], input_export_sha256=prior['input_export_sha256'],
                  containment={name:containment(mesh, np.concatenate([np.asarray(e['points']) for e in lines]))
                               for name, mesh, lines in zip(('before','after'), meshes, (edges, paths))},
                  edges=rows, live_workspace_modified=False,
                  scope='All non-endpoint path samples sectioned. Planes follow local path chords, not independently validated anatomical axes. No radius acceptance threshold established.')
    (ROOT/'docs/evidence/atlas-mca-edit-sections.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report['containment']))
    for stage in ('before','after'):
        values = [s for r in rows for s in r[stage]]
        print(stage, 'measured', sum(s['status']=='MEASURED' for s in values), 'of', len(values))
    errors = [abs(s['measured_area_radius_scale']-s['reported_radius_scale'])
              for r in rows for s in r['after'] if 'measured_area_radius_scale' in s]
    print('paired radius-scale absolute error max/median', max(errors) if errors else None,
          float(np.median(errors)) if errors else None)


if __name__ == '__main__':
    main()
