"""Bounded lesion generation with complete-case geometry by default."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import tempfile

import numpy as np

from .case_io import case_digest, save_case
from .case_surface import build_case_surface
from .lesions import concentric_stenosis, fusiform_dilation
from .batch_distribution import parameter_distribution
from .case_artifacts import write_manifest


def _report(path, report):
    fd, temporary = tempfile.mkstemp(dir=path.parent, suffix='.json.tmp')
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as stream:
            json.dump(report,stream,indent=2,allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary,path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def generate_lesion_batch(base_case, candidates, output, *, target_count,
                            max_attempts, seed, spacing_mm, mask_config=None,
                            surface_edge_ids=None):
    """Ordered operator-defined candidates; no implied population distribution.

    All baseline edges are required unless the caller explicitly selects a
    subset. Coverage does not imply anatomically complete source data.
    Every candidate is a list of explicit lesion keyword dictionaries.
    An empty list explicitly requests baseline reconstruction without new lesions.
    """
    revision = case_digest(base_case)
    # Inspection snapshots may be saved for diagnosis despite failed geometry.
    # Their explicit restriction must survive a later batch import. A true flag
    # does not bypass any of the generation/geometry checks below.
    def check_inspection(value):
        if isinstance(value, dict):
            if 'accepted_for_generation' in value and value['accepted_for_generation'] is not True:
                raise ValueError('Inspection case is not approved for generation')
            for child in value.values():
                check_inspection(child)
        elif isinstance(value, list):
            for child in value:
                check_inspection(child)
    check_inspection(base_case.get('inspection', {}))
    all_edges = {e['id'] for e in base_case['edges']}
    if surface_edge_ids is None:
        edge_ids = sorted(all_edges)
    else:
        if (not isinstance(surface_edge_ids,list) or not surface_edge_ids or
                not all(isinstance(e,str) and e in all_edges for e in surface_edge_ids) or
                len(set(surface_edge_ids)) != len(surface_edge_ids)):
            raise ValueError('explicit unique known surface edge IDs required')
        edge_ids = sorted(surface_edge_ids)
    coverage = dict(mode='complete_case' if set(edge_ids)==all_edges else 'explicit_subset',
                    selected_edge_ids=edge_ids, omitted_edge_ids=sorted(all_edges-set(edge_ids)),
                    source_edge_count=len(all_edges),
                    anatomical_completeness='UNKNOWN')
    for value in (target_count,max_attempts):
        if type(value) is not int or value < 1:
            raise ValueError('positive target_count and max_attempts required')
    if type(seed) is not int or not 0 <= seed < 2**64:
        raise ValueError('uint64 batch seed required')
    if not isinstance(candidates,list) or not candidates:
        raise ValueError('explicit candidate list required')
    # Reject non-serializable/NaN settings before reserving output.
    encoded = json.dumps(candidates,sort_keys=True,allow_nan=False).encode()
    if mask_config is not None:
        if (not isinstance(mask_config,dict) or 'grid_config' not in mask_config or
                set(mask_config)-{'grid_config','anatomical_labels','max_bytes','lesion_rois'}):
            raise ValueError('invalid whole-mask configuration')
        json.dumps(mask_config,allow_nan=False)
    root = Path(output)
    root.mkdir(parents=True,exist_ok=False)
    report = {'schema':'vv-toolbox.batch/1','status':'RUNNING',
        'acceptance_scope':'radius profiles and selected-edge synthetic surface topology/clearance only',
        'candidate_mode':'ordered_operator_defined','base_case_revision':revision,
        'base_model_id':base_case['base_model_id'],'seed':seed,'target_count':target_count,
        'max_attempts':max_attempts,'spacing_mm':spacing_mm,
        'surface_coverage':coverage,
        'candidate_config_sha256':hashlib.sha256(encoded).hexdigest(),
        'attempts':[],'accepted_count':0,'remaining_count':target_count,
        'whole_anatomy_quality':'NOT RUN','mask_output':'REQUIRED' if mask_config is not None else 'NOT RUN',
        'mask_config':deepcopy(mask_config)}
    report['parameter_distribution'] = parameter_distribution(candidates, report['attempts'])
    _report(root/'report.json',report)
    for index, candidate in enumerate(candidates[:max_attempts]):
        if report['accepted_count'] >= target_count:
            break
        attempt_seed = int.from_bytes(hashlib.sha256(f'{seed}:{index}'.encode()).digest()[:8],'big')
        record = {'attempt_index':index,'seed':attempt_seed,'parameters':deepcopy(candidate)}
        try:
            if not isinstance(candidate,list):
                raise ValueError('candidate must be a list of lesion operations')
            case = deepcopy(base_case)
            if not candidate:
                case.update(case_id=f"{base_case['case_id']}:batch:{seed}:{index}:baseline",
                    model_kind='synthetic',generation=dict(seed=attempt_seed,
                    generator_version='baseline-reconstruction/1',config={},
                    parent_generation=deepcopy(base_case['generation'])))
                case.setdefault('history',[]).append(dict(
                    operation='baseline-reconstruction/1',parent_case_revision=revision,
                    scope='synthetic surface from unchanged baseline centerlines and radii; no new lesions'))
            for lesion_index, parameters in enumerate(candidate):
                if not isinstance(parameters,dict) or set(parameters)&{'seed','case_id'}:
                    raise ValueError('candidate fields must exclude batch-owned seed and case_id')
                settings = dict(parameters)
                kind = settings.pop('type','concentric_stenosis')
                if kind not in ('concentric_stenosis','fusiform_dilation'):
                    raise ValueError('unsupported lesion type')
                generator = concentric_stenosis if kind == 'concentric_stenosis' else fusiform_dilation
                case = generator(case,**settings,seed=attempt_seed,
                    case_id=f"{base_case['case_id']}:batch:{seed}:{index}:{lesion_index}")
            if any(l['edge_id'] not in edge_ids for l in case.get('lesions',[])):
                raise ValueError('surface subset must include every existing and new lesion edge')
            vertices, faces, metadata = build_case_surface(case,edge_ids,spacing_mm=spacing_mm)
            metadata['case_edge_coverage'] = deepcopy(coverage)
            masks = None
            if mask_config is not None:
                from .case_masks import build_case_masks
                whole_config = {k:v for k,v in mask_config.items() if k != 'lesion_rois'}
                masks = build_case_masks(case,edge_ids,vertices,faces,spacing_mm=spacing_mm,**whole_config)
            with tempfile.TemporaryDirectory(prefix='.pending-',dir=root) as pending:
                folder = Path(pending)
                result_revision = save_case(folder/'case.snapshot.json',case)
                np.savez_compressed(folder/'surface.npz',vertices_mm=vertices,faces=faces,
                                    metadata=np.array(json.dumps(metadata)))
                if masks is not None:
                    from .volume_cli import save_volume
                    volume,labels,lesion_meta,quality = masks
                    save_volume(folder/'mask.npz',volume,lesion_labels=labels,lesion_metadata=lesion_meta)
                    _report(folder/'mask-quality.json',quality)
                    for roi_index,roi in enumerate(mask_config.get('lesion_rois',[])):
                        from .voxel_output import Grid
                        roi_grid = Grid(**roi['grid_config'])
                        parent_grid = volume.grid
                        if (np.any(np.asarray(roi_grid.spacing_xyz_mm)>parent_grid.spacing_xyz_mm) or
                            not np.any(np.asarray(roi_grid.spacing_xyz_mm)<parent_grid.spacing_xyz_mm)):
                            raise ValueError('lesion ROI spacing must be finer than whole grid')
                        lower = np.asarray(roi_grid.origin_xyz_mm)-np.asarray(roi_grid.spacing_xyz_mm)/2
                        upper = lower+np.asarray(roi_grid.shape_zyx[::-1])*roi_grid.spacing_xyz_mm
                        plower = np.asarray(parent_grid.origin_xyz_mm)-np.asarray(parent_grid.spacing_xyz_mm)/2
                        pupper = plower+np.asarray(parent_grid.shape_zyx[::-1])*parent_grid.spacing_xyz_mm
                        if np.any(lower<plower) or np.any(upper>pupper):
                            raise ValueError('lesion ROI physical extent must lie inside whole grid')
                        roi_volume,roi_labels,roi_meta,roi_quality = build_case_masks(case,edge_ids,vertices,faces,
                            spacing_mm=spacing_mm,grid_config=roi['grid_config'],coverage='lesion_roi',
                            required_lesion_ids=roi['required_lesion_ids'],
                            anatomical_labels=whole_config.get('anatomical_labels'),
                            max_bytes=whole_config.get('max_bytes',256*1024**2))
                        roi_quality['roi_voxel_xyz_to_whole_voxel_xyz'] = (
                            np.linalg.inv(parent_grid.affine_xyz)@roi_grid.affine_xyz).tolist()
                        roi_quality['resampling'] = 'independent surface rasterization; no coarse mask interpolation'
                        save_volume(folder/f'lesion-roi-{roi_index:03d}.npz',roi_volume,
                            lesion_labels=roi_labels,lesion_metadata=roi_meta)
                        _report(folder/f'lesion-roi-{roi_index:03d}-quality.json',roi_quality)
                manifest_digest = write_manifest(folder,case_revision=result_revision,
                    generation=dict(base_case_revision=revision,base_model_id=case['base_model_id'],
                                    batch_seed=seed,attempt_seed=attempt_seed,attempt_index=index,
                                    parameters=deepcopy(candidate),spacing_mm=spacing_mm),
                    coverage=deepcopy(coverage),
                    quality=dict(surface=metadata['checks'],
                                 masks=quality if masks is not None else {'status':'NOT RUN'},
                                 whole_anatomy='NOT RUN'))
                final = root/f'case-{report["accepted_count"]:05d}'
                folder.rename(final)
            record.update(status='PASS',case_revision=result_revision,output=final.name,
                measured_lesions=deepcopy(case.get('lesions',[])),mask_output='PASS' if masks is not None else 'NOT RUN',
                artifact_manifest_sha256=manifest_digest)
            report['accepted_count'] += 1
        except (ValueError,TypeError) as error:
            record.update(status='FAIL',reason=str(error))
        report['attempts'].append(record)
        report['remaining_count'] = target_count-report['accepted_count']
        report['parameter_distribution'] = parameter_distribution(candidates, report['attempts'])
        _report(root/'report.json',report)
    report['status'] = 'PASS' if report['accepted_count'] == target_count else 'FAIL'
    report['stop_reason'] = ('target_reached' if report['status']=='PASS' else
        'max_attempts_reached' if len(report['attempts']) == max_attempts else 'candidates_exhausted')
    _report(root/'report.json',report)
    return report


# Preserve the existing API name and default narrowing operation.
generate_stenosis_batch = generate_lesion_batch
