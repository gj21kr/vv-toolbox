"""Fixed physical centerline experiment with original-plane mesh comparison."""
from copy import deepcopy
import json
from pathlib import Path

import numpy as np
import trimesh

from inspect_neck_surface_bulge import inspect
from vv_toolbox.case_io import case_digest, load_case, save_case
from vv_toolbox.case_surface import build_case_surface
from vv_toolbox.centerline_regularization import smooth_synthetic_centerlines
from vv_toolbox.geometry_quality import screen_nonincident_clearance
from vv_toolbox.junction_continuity import inspect_bridge_continuity


def fixed_planes(mesh, reference):
    rows = deepcopy(reference['attachments'])
    for row in rows:
        for station in row['stations']:
            center = np.asarray(station['center_mm'])
            section = mesh.section(plane_origin=center,plane_normal=station['normal'])
            loops = []
            if section is not None:
                for polygon in section.discrete:
                    if not np.allclose(polygon[0],polygon[-1],atol=1e-5):
                        continue
                    area = float(np.linalg.norm(np.cross(polygon[:-1]-center,polygon[1:]-center).sum(0))/2)
                    loops.append(dict(centroid_distance_mm=float(np.linalg.norm(polygon[:-1].mean(0)-center)),
                                      area_mm2=area,equivalent_radius_mm=float(np.sqrt(area/np.pi))))
            selected = min(loops,key=lambda x:x['centroid_distance_mm']) if loops else None
            if selected is None or selected['centroid_distance_mm'] > station['profile_radius_mm']:
                raise ValueError('fixed plane has no unambiguous local loop')
            station['section'] = selected
            station['section_loop_count'] = len(loops)
        values = [s['section']['equivalent_radius_mm'] for s in row['stations']
                  if s['offset_from_attachment_mm'] <= 0]
        row['source_side_surface_total_variation_mm'] = float(np.abs(np.diff(values)).sum())
    return rows


def main():
    root = Path(__file__).resolve().parents[1]
    folder = root/'exports/synthetic-neck-case'
    source = folder/'case.snapshot.json'
    original_bytes = source.read_bytes()
    case, revision = load_case(source)
    ids = ['FJ3483:e0','FJ1682M:e0','FJ3564:e0','FJ1682:e0']
    settings = dict(sigma_mm=2.,sample_spacing_mm=.25,max_displacement_mm=1.)
    report = dict(schema='vv-toolbox.centerline-neck-experiment/1',parent_revision=revision,
                  parameters=settings,parameters_relaxed=False,surface_smoothness_acceptance='UNKNOWN')
    target = root/'docs/evidence/centerline-regularized-neck.json'
    try:
        derived = smooth_synthetic_centerlines(case,ids,**settings,
                         case_id='bp3d-arterial-carotid-centerline-regularized')
        snapshot = folder/'centerline-regularized-case.snapshot.json'
        if snapshot.exists():
            if load_case(snapshot)[1] != case_digest(derived):
                raise ValueError('existing centerline experiment differs')
        else:
            save_case(snapshot,derived)
        selected = case['synthetic_route_inspection']['bridge_ids']+ids
        all_geometry = [e['id'] for e in derived['edges'] if e['centerline_mm'] is not None]
        report['whole_case_modified_edge_capsules'] = screen_nonincident_clearance(
            derived,all_geometry,focus_edge_ids=selected,max_segment_pairs=2_000_000)
        baseline_clearance = screen_nonincident_clearance(
            case,all_geometry,focus_edge_ids=selected,max_segment_pairs=2_000_000)
        report['baseline_same_scope_capsules'] = baseline_clearance
        before_pairs = {tuple(sorted(c['edges'])) for c in baseline_clearance['potential_contacts']}
        after_pairs = {tuple(sorted(c['edges'])) for c in report['whole_case_modified_edge_capsules']['potential_contacts']}
        report['contact_pair_changes'] = dict(new_potential_pairs=sorted(after_pairs-before_pairs),
            persisting_potential_pairs=sorted(after_pairs&before_pairs),
            no_longer_detected_pairs=sorted(before_pairs-after_pairs),
            interpretation='capsule witnesses; not adjudicated anatomical junctions or exact mesh collisions')
        report['continuity'] = inspect_bridge_continuity(derived,max_angle_deg=5.,max_radius_jump_mm=1e-6)
        vertices,faces,metadata = build_case_surface(derived,selected,spacing_mm=.6)
        surface = folder/'centerline-regularized-neck-surface.npz'
        if not surface.exists():
            with surface.open('xb') as stream:
                np.savez_compressed(stream,vertices_mm=vertices,faces=faces,metadata=np.array(json.dumps(metadata)))
        with np.load(surface,allow_pickle=False) as data:
            if json.loads(str(data['metadata']))['case_revision'] != case_digest(derived):
                raise ValueError('stored surface belongs to different case')
            mesh = trimesh.Trimesh(vertices=data['vertices_mm'],faces=data['faces'],process=False)
        before = inspect(source,folder/'neck-surface.npz',2.)
        fixed = fixed_planes(mesh,before)
        own = inspect(snapshot,surface,2.)
        comparisons = [dict(edge_id=a['source_edge_id'],
            before_surface_tv_mm=a['source_side_surface_total_variation_mm'],
            fixed_plane_after_tv_mm=b['source_side_surface_total_variation_mm'],
            new_centerline_plane_after_tv_mm=c['source_side_surface_total_variation_mm'])
            for a,b,c in zip(before['attachments'],fixed,own['attachments'])]
        report.update(status='PASS',scope='bounded transformation and matched-plane measurement',
            derived_revision=case_digest(derived),metrics=derived['centerline_regularization'],
            matched_plane_count=before['station_count'],comparisons=comparisons,
            fixed_plane_before=before,fixed_plane_after=fixed,own_plane_after=own,
            topology=metadata['checks'],anatomical_acceptance='UNKNOWN')
        report['default_adoption'] = 'NOT ACCEPTED'
        report['reason_not_adopted'] = 'No uniform surface improvement; whole-case contact candidates unresolved'
    except ValueError as error:
        report.update(status='FAIL',reason=str(error))
    if source.read_bytes() != original_bytes:
        raise ValueError('original snapshot modified')
    report['original_snapshot_unchanged'] = True
    target.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in
        ('fixed_plane_before','fixed_plane_after','own_plane_after','whole_case_modified_edge_capsules','baseline_same_scope_capsules')}))


if __name__ == '__main__':
    main()
