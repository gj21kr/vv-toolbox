"""Construct a provisional Hermite transition and measure every interface."""
import hashlib
import argparse
import io
import json
from pathlib import Path

import numpy as np
import trimesh

from inspect_mca_explicit_neck import ordered
from vv_toolbox.ring_stitch import stitch_rings
from vv_toolbox.tangent_patch import hermite_rings
from vv_toolbox.angular_ring import angular_ring, stitch_polar_rings
from vv_toolbox.quality_stitch import quality_stitch
from vv_toolbox.projected_annulus import triangulate_annulus

ROOT = Path(__file__).resolve().parents[1]


def unit(v):
    lengths = np.linalg.norm(v, axis=1)
    if np.any(lengths < 1e-10):
        raise ValueError('undefined tangent field')
    return v/lengths[:, None]


def periodic(values, angles, query):
    return np.column_stack([np.interp(query, np.r_[angles[-1]-2*np.pi, angles, angles[0]+2*np.pi],
                                     np.r_[values[-1, k], values[:, k], values[0, k]])
                            for k in range(3)])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--angular', action='store_true')
    parser.add_argument('--normal-tangent', action='store_true',
                        help='Use the declared neck normal for the common cross-rim tangent')
    parser.add_argument('--constant-normal', action='store_true',
                        help='Use the constant declared normal without tangent projection')
    parser.add_argument('--quality-outer', action='store_true')
    parser.add_argument('--oriented-outer', action='store_true')
    parser.add_argument('--delaunay-outer', action='store_true')
    parser.add_argument('--earcut-outer', action='store_true')
    parser.add_argument('--improve-edges', action='store_true')
    parser.add_argument('--uniform-interior', action='store_true')
    parser.add_argument('--interior-samples', type=int, choices=[32, 64, 128], default=64)
    parser.add_argument('--radial-intervals', type=int, choices=[8, 16, 32], default=8)
    args = parser.parse_args()
    if args.uniform_interior and (not args.earcut_outer or args.angular):
        parser.error('uniform interior requires earcut outer with arc-length correspondence')
    source = json.loads((ROOT/'docs/evidence/mca-surface-origin.json').read_text())
    band = json.loads((ROOT/'docs/evidence/mca-transition-annulus.json').read_text())
    spec = json.loads((ROOT/'docs/evidence/regularized-mca-sac.json').read_text())['specification']
    path = ROOT/'exports/mca-surface-origin/surface.npz'
    raw = path.read_bytes()
    if not (hashlib.sha256(raw).hexdigest() == source['artifact_sha256'] == band['artifact_sha256']):
        raise ValueError('source mismatch')
    with np.load(io.BytesIO(raw), allow_pickle=False) as data:
        original, faces = data['vertices_mm'], data['faces']
        metadata = json.loads(str(data['metadata'].item()))
    if not (metadata['case_revision'] == band['case_revision'] == spec['case_revision']):
        raise ValueError('case mismatch')
    if any(row['status'] != 'BOUNDARIES_PASS' for row in band['sides']):
        raise ValueError('annulus boundaries unavailable')
    labels = np.asarray(metadata['surface_origin']['face_labels'])
    remove = labels == 2
    for row in band['sides']:
        remove[row['removed_face_indices']] = True
    center = np.asarray(spec['neck']['center_mm'])
    basis = np.column_stack([spec['neck'][k] for k in ('width_axis', 'depth_axis', 'normal')])
    rim = np.asarray(metadata['attachment']['curve_mm'])
    vertices = np.vstack([original, rim])
    order = angular_ring if args.angular else ordered
    neck_ids, angles = order(np.arange(len(original), len(vertices)), vertices, center, basis)
    neck = vertices[neck_ids]
    # Estimate external normals from retained faces only, excluding the region
    # being replaced. IDs and coordinates of retained vertices stay unchanged.
    retained_mesh = trimesh.Trimesh(vertices=original, faces=faces[~remove], process=False)
    sides = []
    for row in band['sides']:
        try:
            ids, parameter = order(row['outer_boundary_vertex_indices'], original, center, basis)
        except ValueError as error:
            if not args.angular:
                raise
            report = dict(status='REJECTED', stage='geometric correspondence',
                          side=row['side'], reason=str(error),
                          artifact_sha256=source['artifact_sha256'],
                          case_revision=metadata['case_revision'],
                          input_unchanged=raw == path.read_bytes(),
                          geometry_generated=False, app_applied=False)
            (ROOT/'docs/evidence/mca-angular-transition.json').write_text(json.dumps(report, indent=2)+'\n')
            print(json.dumps(report))
            return
        points = periodic(original[ids], parameter, angles)
        normals = unit(periodic(retained_mesh.vertex_normals[ids], parameter, angles))
        sides.append((ids, parameter, points, normals))
    tangent = unit(np.roll(neck, -1, axis=0)-np.roll(neck, 1, axis=0))
    across = sides[1][2]-sides[0][2]
    q = unit(across-np.sum(across*tangent, axis=1)[:, None]*tangent)
    tangent_alignment = q @ basis[:, 2]
    if args.normal_tangent:
        normal = np.broadcast_to(basis[:, 2], tangent.shape)
        q = unit(normal-np.sum(normal*tangent, axis=1)[:, None]*tangent)
    if args.constant_normal:
        q = np.broadcast_to(basis[:, 2], tangent.shape).copy()
    strips = []
    def connect(a, ta, b, tb):
        if not args.angular:
            return stitch_rings(a, ta, b, tb)
        return stitch_polar_rings(a, ta, b, tb)
    for side, (ids, parameter, outer, normals) in enumerate(sides):
        sign = -1 if side == 0 else 1
        scale = np.linalg.norm(outer-neck, axis=1)[:, None]
        start_d = sign*q*scale
        outward = outer-neck
        end_d = unit(outward-np.sum(outward*normals, axis=1)[:, None]*normals)*scale
        rings, _ = hermite_rings(neck, outer, start_d, end_d,
                                np.linspace(0, 1, args.radial_intervals+1))
        previous = neck_ids
        previous_angles = angles
        interior_angles = np.arange(args.interior_samples)*2*np.pi/args.interior_samples if args.uniform_interior else angles
        # Stop before u=1. Connect the last ring to original boundary IDs;
        # no duplicate sampled outer ring is left disconnected.
        # A projected annulus needs a wider region than the final narrow zipper.
        # Keep the cut at u=5/8 independently of radial resolution.
        cut_index = 5*args.radial_intervals//8
        for ring in (rings[1:cut_index+1] if args.delaunay_outer or args.earcut_outer else rings[1:-1]):
            if args.uniform_interior:
                ring = periodic(ring, angles, interior_angles)
            current = np.arange(len(vertices), len(vertices)+len(ring))
            vertices = np.vstack([vertices, ring])
            strips.append(connect(previous, previous_angles, current, interior_angles))
            previous = current
            previous_angles = interior_angles
        if args.delaunay_outer or args.earcut_outer:
            try:
                strips.append(triangulate_annulus(vertices, previous, ids, center, basis,
                              engine='earcut' if args.earcut_outer else 'delaunay',
                              improve=args.improve_edges))
            except ValueError as error:
                report = dict(status='REJECTED', stage='projected outer annulus',
                              side=side, reason=str(error), case_revision=metadata['case_revision'],
                              artifact_sha256=source['artifact_sha256'],
                              input_unchanged=raw == path.read_bytes(),
                              geometry_generated=False, app_applied=False)
                failure_name = 'mca-earcut-transition.json' if args.earcut_outer else 'mca-delaunay-transition.json'
                (ROOT/'docs/evidence'/failure_name).write_text(json.dumps(report, indent=2)+'\n')
                print(json.dumps(report))
                return
        elif args.oriented_outer:
            refs = np.zeros_like(vertices)
            refs[previous] = normals
            refs[ids] = retained_mesh.vertex_normals[ids]
            baseline = connect(previous, angles, ids, parameter)
            triangles = vertices[baseline]
            orientation = np.sum(np.einsum('ij,ij->i',
                np.cross(triangles[:, 1]-triangles[:, 0], triangles[:, 2]-triangles[:, 0]),
                refs[baseline].sum(axis=1)))
            if orientation < 0:
                refs *= -1
            try:
                strips.append(quality_stitch(vertices, previous, ids, refs))
            except ValueError as error:
                report = dict(status='REJECTED', stage='oriented outer triangulation',
                              side=side, reason=str(error), case_revision=metadata['case_revision'],
                              artifact_sha256=source['artifact_sha256'],
                              input_unchanged=raw == path.read_bytes(),
                              geometry_generated=False, app_applied=False)
                (ROOT/'docs/evidence/mca-oriented-transition.json').write_text(json.dumps(report, indent=2)+'\n')
                print(json.dumps(report))
                return
        else:
            strips.append(quality_stitch(vertices, previous, ids) if args.quality_outer
                          else connect(previous, angles, ids, parameter))
    combined = np.vstack([faces[~remove], *strips])
    mesh = trimesh.Trimesh(vertices=vertices, faces=combined, process=False)
    trimesh.repair.fix_normals(mesh, multibody=False)
    origin = np.r_[labels[~remove], np.full(sum(len(s) for s in strips), 4)]
    design_edges = {tuple(sorted((int(a), int(b)))) for a, b in
                    zip(neck_ids, np.roll(neck_ids, -1))}
    seam = np.array([tuple(sorted(e.tolist())) in design_edges for e in mesh.face_adjacency_edges])
    patch_pair = (origin == 4)[mesh.face_adjacency].sum(axis=1)
    strip_ids = np.r_[np.full(np.count_nonzero(~remove), -1),
                      *[np.full(len(strip), i) for i, strip in enumerate(strips)]]
    dihedral = np.degrees(mesh.face_adjacency_angles)
    groups = dict(neck=seam, outer_join=patch_pair == 1,
                  transition_interior=(patch_pair == 2) & ~seam)
    angle_report = {}
    for name, mask in groups.items():
        values = dihedral[mask]
        worst = np.flatnonzero(mask)[np.argmax(values)]
        angle_report[name] = dict(count=len(values), maximum_deg=float(values.max()),
                                  p95_deg=float(np.percentile(values, 95)),
                                  above_90_deg=int(np.count_nonzero(values > 90)),
                                  worst_edge_vertex_ids=mesh.face_adjacency_edges[worst].tolist(),
                                  worst_face_ids=mesh.face_adjacency[worst].tolist())
    crease_locations = {}
    for pair in strip_ids[mesh.face_adjacency[dihedral > 90]]:
        key = ','.join(map(str, sorted(pair.tolist())))
        crease_locations[key] = crease_locations.get(key, 0)+1
    patch = origin == 4
    triangles = vertices[mesh.faces[patch]]
    squared = np.sum((np.roll(triangles, -1, axis=1)-triangles)**2, axis=(1, 2))
    quality = 4*np.sqrt(3)*mesh.area_faces[patch]/squared
    result = dict(schema='vv-toolbox.tangent-transition/1',
                  case_revision=metadata['case_revision'], frame=metadata['frame'],
                  parent_artifact_sha256=source['artifact_sha256'],
                  design_vertex_ids=neck_ids.tolist(), face_origin_labels=origin.tolist(),
                  status='CANDIDATE', parameterization=('shared geometric polar angle' if args.angular else 'provisional normalized arc length; anatomical correspondence NOT VERIFIED'),
                  cross_rim_tangent=('constant declared neck normal' if args.constant_normal else
                                     'projected declared neck normal' if args.normal_tangent else 'projected outer-ring difference'),
                  original_cross_rim_normal_alignment=dict(minimum=float(tangent_alignment.min()),
                                                          maximum=float(tangent_alignment.max()),
                                                          negative_count=int(np.count_nonzero(tangent_alignment < 0))),
                  sampling_intervals=args.radial_intervals, band_width_mm=band['band_width_mm'],
                  interior_ring_samples=args.interior_samples if args.uniform_interior else len(neck),
                  projected_edge_improvement=args.improve_edges,
                  outer_triangulation=('verified projected Earcut 1.0.3' if args.earcut_outer else
                                       'verified projected Delaunay' if args.delaunay_outer else
                                       'oriented minimum inverse quality' if args.oriented_outer else
                                       'minimum inverse quality' if args.quality_outer else 'parameter zipper'),
                  angles=angle_report, minimum_triangle_quality=float(quality.min()),
                  crease_strip_pairs=crease_locations,
                  strip_index_definition=f'0..{len(strips)//2-1} parent neck-to-outer, {len(strips)//2}..{len(strips)-1} sac neck-to-outer; -1 retained source',
                  minimum_triangle_area_mm2=float(mesh.area_faces[patch].min()),
                  closed_volume='PASS' if mesh.is_volume else 'FAIL',
                  component_count=len(mesh.split(only_watertight=False)),
                  original_vertices_unchanged=bool(np.array_equal(vertices[:len(original)], original)),
                  design_curve_exact=bool(np.array_equal(vertices[neck_ids], neck)),
                  self_intersection='NOT RUN', context_collision='NOT RUN',
                  smooth_junction='UNKNOWN',
                  crease_screen='FAIL' if any(row['above_90_deg'] for row in angle_report.values()) else 'PASS',
                  crease_screen_definition='Reject any measured transition or interface face-normal angle above 90 degrees; passing is not smoothness acceptance.',
                  app_applied=False)
    name = 'mca-angular-transition' if args.angular else 'mca-tangent-transition'
    if args.normal_tangent:
        name += '-normal'
    if args.constant_normal:
        name += '-constant'
    if args.quality_outer:
        name += '-quality'
    if args.oriented_outer:
        name += '-oriented'
    if args.delaunay_outer:
        name += '-delaunay'
    if args.earcut_outer:
        name += '-earcut'
    if args.improve_edges:
        name += '-flips'
    if args.uniform_interior:
        name += '-uniform'
        if args.interior_samples != 64:
            name += f'-{args.interior_samples}'
    if args.radial_intervals != 8:
        name += f'-radial{args.radial_intervals}'
    out = ROOT/'exports'/name
    out.mkdir(exist_ok=True)
    np.savez_compressed(out/'surface.npz', vertices_mm=vertices, faces=mesh.faces,
                        metadata=np.array(json.dumps(result)))
    report = {k: v for k, v in result.items() if k not in ('design_vertex_ids', 'face_origin_labels')}
    report.update(artifact_sha256=hashlib.sha256((out/'surface.npz').read_bytes()).hexdigest(),
                  input_unchanged=raw == path.read_bytes())
    (ROOT/'docs/evidence'/f'{name}.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
