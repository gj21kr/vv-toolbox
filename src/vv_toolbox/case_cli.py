"""Case snapshot command line; does not imply clinical or geometry acceptance."""
import argparse
import json
from pathlib import Path

from .case_contract import validate_case, validate_collection
from .case_io import load_case, save_case
from .access_routes import inspect_route
from .segment_materialization import materialize_segments
from .lesions import concentric_stenosis, fusiform_dilation


def main(argv=None):
    parser = argparse.ArgumentParser(description='Validate and preserve VV Toolbox cases')
    sub = parser.add_subparsers(dest='command', required=True)
    save = sub.add_parser('save', help='Validate raw case JSON and atomically save snapshot')
    save.add_argument('input', type=Path)
    save.add_argument('output', type=Path)
    save.add_argument('--expected-revision')
    inspect = sub.add_parser('inspect', help='Verify and summarize a saved case')
    inspect.add_argument('snapshot', type=Path)
    sub.add_parser('label-registry', help='Print fixed cerebral and access-vessel mask IDs')
    access_labels = sub.add_parser('access-labels', help='Save explicit whole-edge access labels in a separate snapshot')
    access_labels.add_argument('snapshot',type=Path)
    access_labels.add_argument('assignments',type=Path,
        help='JSON schema, source_case_revision and assignments list with edge_id, label_id, evidence_refs')
    access_labels.add_argument('output',type=Path)
    context = sub.add_parser('surface-context', help='Inspect a hash-bound surface against all other case profiles')
    context.add_argument('snapshot', type=Path)
    context.add_argument('surface', type=Path)
    context.add_argument('--parent-edge', required=True)
    context.add_argument('--sha256', required=True, help='Expected NPZ artifact hash')
    frame = sub.add_parser('saccular-frame', help='Propose a source-bound engineering placement frame')
    frame.add_argument('snapshot',type=Path)
    frame.add_argument('--edge',required=True)
    frame.add_argument('--station-mm',type=float,required=True)
    frame.add_argument('--reference-direction',type=float,nargs=3,required=True)
    frame.add_argument('--search-mm',type=float,required=True)
    collection = sub.add_parser('collection', help='Check snapshot ancestry and source-content split isolation')
    collection.add_argument('snapshots', type=Path, nargs='+')
    route = sub.add_parser('route', help='Inspect a path through ordered vessel instances')
    route.add_argument('snapshot', type=Path)
    route.add_argument('--start', required=True)
    route.add_argument('--end', required=True)
    route.add_argument('--via', nargs='+', required=True, help='Ordered required edge IDs')
    route.add_argument('--max-states', type=int, default=100000)
    split = sub.add_parser('split', help='Apply explicit reviewed centerline boundary assignments')
    split.add_argument('snapshot', type=Path)
    split.add_argument('annotations', type=Path)
    split.add_argument('assignments', type=Path)
    split.add_argument('output', type=Path)
    split.add_argument('--tolerance-mm', type=float, required=True)
    split.add_argument('--expected-revision')
    stenosis = sub.add_parser('stenosis', help='Generate one explicit synthetic concentric radius lesion')
    stenosis.add_argument('snapshot', type=Path)
    stenosis.add_argument('parameters', type=Path, help='JSON keyword parameters for concentric_stenosis')
    stenosis.add_argument('output', type=Path)
    stenosis.add_argument('--expected-revision')
    dilation = sub.add_parser('dilation', help='Generate one explicit manual synthetic fusiform dilation')
    dilation.add_argument('snapshot', type=Path)
    dilation.add_argument('parameters', type=Path)
    dilation.add_argument('output', type=Path)
    dilation.add_argument('--expected-revision')
    sac = sub.add_parser('saccular-spec', help='Describe a source-bound manual sac; does not generate lumen geometry')
    sac.add_argument('snapshot', type=Path)
    sac.add_argument('parameters', type=Path)
    bifurcation = sub.add_parser('bifurcation-saccular-spec', help='Describe a multi-branch sac and protected outlets; no geometry generation')
    bifurcation.add_argument('snapshot', type=Path)
    bifurcation.add_argument('parameters', type=Path)
    sac_surface = sub.add_parser('saccular-surface', help='Export an experimental single-parent sac union candidate')
    sac_surface.add_argument('snapshot', type=Path)
    sac_surface.add_argument('specification', type=Path)
    sac_surface.add_argument('output', type=Path)
    sac_surface.add_argument('--spacing-mm', type=float, required=True)
    sac_surface.add_argument('--max-grid-voxels', type=int, default=2_000_000)
    branch_surface = sub.add_parser('bifurcation-surface', help='Export an experimental multi-branch sac candidate, not an accepted case')
    branch_surface.add_argument('snapshot', type=Path)
    branch_surface.add_argument('specification', type=Path)
    branch_surface.add_argument('output', type=Path)
    branch_surface.add_argument('--spacing-mm', type=float, required=True)
    branch_surface.add_argument('--max-grid-voxels', type=int, default=2_000_000)
    sac_masks = sub.add_parser('saccular-masks', help='Export candidate surface masks and synthetic sac labels')
    sac_masks.add_argument('snapshot', type=Path)
    sac_masks.add_argument('specification', type=Path)
    sac_masks.add_argument('grid', type=Path)
    sac_masks.add_argument('output', type=Path)
    sac_masks.add_argument('--surface-spacing-mm', type=float, required=True)
    sac_masks.add_argument('--coverage', choices=('whole','sac_roi'), default='whole')
    sac_masks.add_argument('--max-grid-voxels', type=int, default=2_000_000)
    sac_masks.add_argument('--max-bytes', type=int, default=256*1024**2)
    bridges = sub.add_parser('synthetic-routes', help='Save explicit source-endpoint bridges as a separate synthetic case')
    bridges.add_argument('snapshot', type=Path)
    bridges.add_argument('specification', type=Path)
    bridges.add_argument('output', type=Path)
    bridges.add_argument('--case-id', required=True)
    bridges.add_argument('--expected-revision')
    for command, description in (
            ('split-junction','Split an explicit interior point in a separate synthetic case'),
            ('trim-terminal','Trim a declared free terminal tail in a separate synthetic case'),
            ('split-bridge','Split a declared synthetic bridge with attachment lineage'),
            ('extend-routes','Append declared bridges to an existing synthetic case')):
        operation = sub.add_parser(command,help=description)
        operation.add_argument('snapshot',type=Path)
        operation.add_argument('specification',type=Path)
        operation.add_argument('output',type=Path)
        operation.add_argument('--case-id',required=True)
        operation.add_argument('--expected-revision')
    four = sub.add_parser('four-routes', help='Inspect four explicitly declared femoral/carotid graph paths')
    four.add_argument('snapshot', type=Path)
    four.add_argument('routes', type=Path)
    continuity = sub.add_parser('bridge-continuity', help='Measure both attachments of declared synthetic bridges')
    continuity.add_argument('snapshot', type=Path)
    continuity.add_argument('--max-angle-deg', type=float, required=True)
    continuity.add_argument('--max-radius-jump-mm', type=float, required=True)
    smooth = sub.add_parser('smooth-radii', help='Create a bounded synthetic radius regularization')
    smooth.add_argument('snapshot', type=Path)
    smooth.add_argument('parameters', type=Path)
    smooth.add_argument('output', type=Path)
    smooth.add_argument('--expected-revision')
    centerline = sub.add_parser('smooth-centerlines', help='Create bounded synthetic centerline smoothing with fixed attachments')
    centerline.add_argument('snapshot', type=Path)
    centerline.add_argument('parameters', type=Path)
    centerline.add_argument('output', type=Path)
    centerline.add_argument('--expected-revision')
    surface = sub.add_parser('surface', help='Export a synthetic profile union surface as NPZ')
    surface.add_argument('snapshot', type=Path)
    surface.add_argument('output', type=Path)
    surface.add_argument('--edges', nargs='+', required=True)
    surface.add_argument('--spacing-mm', type=float, required=True)
    surface.add_argument('--max-grid-voxels', type=int, default=20_000_000)
    surface.add_argument('--junction-regions', type=Path, help='Explicit case-bound synthetic junction allowances JSON')
    batch = sub.add_parser('batch', help='Generate accepted manual lesion cases from explicit ordered candidates')
    batch.add_argument('snapshot', type=Path)
    batch.add_argument('candidates', type=Path)
    batch.add_argument('output', type=Path)
    batch.add_argument('--target-count', type=int, required=True)
    batch.add_argument('--max-attempts', type=int, required=True)
    batch.add_argument('--seed', type=int, required=True)
    batch.add_argument('--spacing-mm', type=float, required=True)
    batch.add_argument('--mask-config', type=Path, help='Grid and optional anatomical labels for required masks')
    batch.add_argument('--surface-edges', nargs='+', help='Explicit partial surface output; default includes every case edge')
    args = parser.parse_args(argv)
    try:
        if args.command == 'label-registry':
            from .anatomical_labels import REGISTRY
            print(json.dumps(REGISTRY,allow_nan=False))
            return 0
        if args.command == 'collection':
            loaded = [load_case(path) for path in args.snapshots]
            result = validate_collection([case for case, _ in loaded])
            print(json.dumps(dict(result, status='PASS', scope='declared lineage and shared geometry source hashes',
                                  independent_anatomy='UNKNOWN',
                                  revisions=[revision for _, revision in loaded])))
            return 0
        if args.command == 'save':
            case = json.loads(args.input.read_text(encoding='utf-8'))
            if args.input.resolve() == args.output.resolve():
                raise ValueError('snapshot output must differ from raw input')
            revision = save_case(args.output, case, expected_revision=args.expected_revision)
        else:
            case, revision = load_case(args.snapshot)
        if args.command == 'access-labels':
            from .anatomical_labels import assign_access_labels, resolve_labels
            from .case_io import _unique_object
            if (args.output.resolve() in {args.snapshot.resolve(),args.assignments.resolve()} or
                    (args.output.exists() and
                     (args.output.samefile(args.snapshot) or args.output.samefile(args.assignments)))):
                raise ValueError('label output must differ from source and assignments')
            request=json.loads(args.assignments.read_text(encoding='utf-8'),object_pairs_hook=_unique_object)
            if (not isinstance(request,dict) or
                    set(request)!={'schema','source_case_revision','assignments'} or
                    request.get('schema')!='vv-toolbox.access-label-request/1'):
                raise ValueError('access label request schema required')
            case=assign_access_labels(case,request['assignments'],
                                      expected_revision=request['source_case_revision'])
            labels,registry=resolve_labels(case,[a['edge_id'] for a in request['assignments']])
            revision=save_case(args.output,case)
            print(json.dumps(dict(status='PASS',scope='operator-declared edge labels and snapshot integrity',
                revision=revision,labels=labels,registry_sha256=registry['sha256'],
                anatomical_acceptance='UNKNOWN')))
            return 0
        if args.command == 'surface-context':
            from .surface_context import inspect_surface_artifact
            report = inspect_surface_artifact(case,args.surface,parent_edge_id=args.parent_edge,
                                              expected_sha256=args.sha256)
            print(json.dumps(report,allow_nan=False))
            return 0 if report['status']=='SEPARATED_PROFILES' else 3
        if args.command == 'saccular-frame':
            from .saccular_frame import propose_saccular_frame
            print(json.dumps(propose_saccular_frame(case,args.edge,args.station_mm,
                args.reference_direction,search_mm=args.search_mm),allow_nan=False))
            return 0
        if args.command in ('saccular-spec','bifurcation-saccular-spec'):
            from .saccular import saccular_spec
            from .bifurcation_saccular import bifurcation_saccular_spec
            from .case_io import _unique_object
            parameters = json.loads(args.parameters.read_text(encoding='utf-8'), object_pairs_hook=_unique_object)
            builder=saccular_spec if args.command=='saccular-spec' else bifurcation_saccular_spec
            print(json.dumps(builder(case, **parameters), allow_nan=False))
            return 0
        if args.command == 'saccular-masks':
            from .saccular_masks import build_saccular_masks
            from .case_io import _unique_object
            from .volume_cli import save_volume
            specification = json.loads(args.specification.read_text(encoding='utf-8'),
                                       object_pairs_hook=_unique_object)
            grid = json.loads(args.grid.read_text(encoding='utf-8'), object_pairs_hook=_unique_object)
            volume, labels, metadata = build_saccular_masks(case, specification,
                surface_spacing_mm=args.surface_spacing_mm, grid_config=grid, coverage=args.coverage,
                max_grid_voxels=args.max_grid_voxels, max_bytes=args.max_bytes)
            save_volume(args.output, volume, lesion_labels=labels, lesion_metadata=metadata)
            print(json.dumps({'status':'CANDIDATE','counts':metadata['voxel_counts']}))
            return 0
        if args.command in ('smooth-radii','smooth-centerlines'):
            from .radius_regularization import smooth_synthetic_radii
            from .case_io import _unique_object
            if (args.output.resolve() in {args.snapshot.resolve(),args.parameters.resolve()} or
                    (args.output.exists() and
                     (args.output.samefile(args.snapshot) or args.output.samefile(args.parameters)))):
                raise ValueError('regularized output must differ from input and parameters')
            parameters = json.loads(args.parameters.read_text(encoding='utf-8'),object_pairs_hook=_unique_object)
            if args.command == 'smooth-centerlines':
                from .centerline_regularization import smooth_synthetic_centerlines
                case = smooth_synthetic_centerlines(case, **parameters)
            else:
                case = smooth_synthetic_radii(case, **parameters)
            revision = save_case(args.output,case,expected_revision=args.expected_revision)
        if args.command == 'bridge-continuity':
            from .junction_continuity import inspect_bridge_continuity
            report = inspect_bridge_continuity(case, max_angle_deg=args.max_angle_deg,
                                               max_radius_jump_mm=args.max_radius_jump_mm)
            report['case_revision'] = revision
            print(json.dumps(report))
            return 0 if report['status'] == 'PASS' else 1
        if args.command in ('synthetic-routes','extend-routes','split-junction','trim-terminal','split-bridge'):
            from .synthetic_routes import build_synthetic_routes, extend_synthetic_routes
            from .case_io import _unique_object
            if (args.output.resolve() in {args.snapshot.resolve(), args.specification.resolve()} or
                    (args.output.exists() and
                     (args.output.samefile(args.snapshot) or args.output.samefile(args.specification)))):
                raise ValueError('synthetic output must not replace source or specification')
            specification = json.loads(args.specification.read_text(encoding='utf-8'),
                                       object_pairs_hook=_unique_object)
            if args.command == 'split-bridge':
                from .synthetic_junctions import split_synthetic_bridge
                generator = split_synthetic_bridge
            elif args.command == 'trim-terminal':
                from .synthetic_junctions import trim_synthetic_terminal
                generator = trim_synthetic_terminal
            elif args.command == 'split-junction':
                from .synthetic_junctions import split_synthetic_junction
                generator = split_synthetic_junction
            else:
                generator = extend_synthetic_routes if args.command == 'extend-routes' else build_synthetic_routes
            case = generator(case, specification, case_id=args.case_id)
            revision = save_case(args.output, case, expected_revision=args.expected_revision)
        if args.command == 'four-routes':
            from .synthetic_routes import inspect_four_access_routes
            from .case_io import _unique_object
            routes = json.loads(args.routes.read_text(encoding='utf-8'), object_pairs_hook=_unique_object)
            report = inspect_four_access_routes(case, routes)
            statuses = [r['result']['status'] for r in report['routes']]
            report['status'] = 'FAIL' if 'FAIL' in statuses else 'UNKNOWN' if 'UNKNOWN' in statuses else 'PASS'
            report['case_revision'] = revision
            print(json.dumps(report))
            return {'PASS':0, 'FAIL':1, 'UNKNOWN':3}[report['status']]
        if args.command == 'batch':
            from .batch import generate_lesion_batch
            candidates = json.loads(args.candidates.read_text(encoding='utf-8'))
            report = generate_lesion_batch(case,candidates,args.output,target_count=args.target_count,
                max_attempts=args.max_attempts,seed=args.seed,spacing_mm=args.spacing_mm,
                surface_edge_ids=args.surface_edges,
                mask_config=json.loads(args.mask_config.read_text(encoding='utf-8')) if args.mask_config else None)
            print(json.dumps({key:report[key] for key in
                ('status','acceptance_scope','accepted_count','remaining_count','stop_reason')}))
            return 0 if report['status'] == 'PASS' else 1
        if args.command in ('surface', 'saccular-surface', 'bifurcation-surface'):
            import os
            import tempfile
            import numpy as np
            from .case_surface import build_case_surface
            from .case_io import _unique_object
            if args.command in ('saccular-surface','bifurcation-surface'):
                from .saccular_surface import build_saccular_candidate
                from .bifurcation_surface import build_bifurcation_candidate
                specification = json.loads(args.specification.read_text(encoding='utf-8'),
                                           object_pairs_hook=_unique_object)
                builder = build_bifurcation_candidate if args.command=='bifurcation-surface' else build_saccular_candidate
                vertices, faces, metadata = builder(case, specification,
                    spacing_mm=args.spacing_mm, max_grid_voxels=args.max_grid_voxels)
            else:
                regions = (json.loads(args.junction_regions.read_text(encoding='utf-8'),
                                      object_pairs_hook=_unique_object) if args.junction_regions else None)
                vertices, faces, metadata = build_case_surface(case, args.edges,
                    spacing_mm=args.spacing_mm, max_grid_voxels=args.max_grid_voxels,
                    junction_regions=regions)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            fd, temporary = tempfile.mkstemp(dir=args.output.parent, suffix='.npz.tmp')
            try:
                with os.fdopen(fd, 'wb') as stream:
                    np.savez_compressed(stream, vertices_mm=vertices, faces=faces,
                                        metadata=np.array(json.dumps(metadata)))
                    stream.flush()
                    os.fsync(stream.fileno())
                os.link(temporary, args.output)
            finally:
                Path(temporary).unlink(missing_ok=True)
            print(json.dumps({'status':'PASS' if args.command == 'surface' else 'CANDIDATE',
                              'scope':'synthetic surface topology only; no anatomical acceptance',
                              'vertices':len(vertices),'triangles':len(faces)}))
            return 0
        if args.command == 'route':
            report = inspect_route(case, args.start, args.end, args.via, max_states=args.max_states)
            report['case_revision'] = revision
            print(json.dumps(report))
            return {'PASS': 0, 'FAIL': 1, 'UNKNOWN': 3}[report['status']]
        if args.command == 'split':
            annotations = json.loads(args.annotations.read_text(encoding='utf-8'))
            assignments = json.loads(args.assignments.read_text(encoding='utf-8'))
            case = materialize_segments(case, annotations, assignments, tolerance_mm=args.tolerance_mm)
            revision = save_case(args.output, case, expected_revision=args.expected_revision)
        if args.command in ('stenosis','dilation'):
            parameters = json.loads(args.parameters.read_text(encoding='utf-8'))
            generator = concentric_stenosis if args.command == 'stenosis' else fusiform_dilation
            case = generator(case, **parameters)
            revision = save_case(args.output, case, expected_revision=args.expected_revision)
        validate_case(case)
        summary = {'status': 'PASS', 'scope': 'case structure and snapshot integrity only',
                   'case_id': case['case_id'], 'revision': revision,
                   'model_kind': case['model_kind'], 'nodes': len(case['nodes']), 'edges': len(case['edges']),
                   'unresolved_edges': sum(e['evidence_status'] == 'unresolved' for e in case['edges'])}
        print(json.dumps(summary))
        return 0
    except (ValueError, OSError, TypeError) as exc:
        parser.exit(2, str(exc) + '\n')


if __name__ == '__main__':
    raise SystemExit(main())
