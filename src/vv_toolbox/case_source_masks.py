"""Voxelize exact registered surfaces while retaining per-part provenance."""
import math
import numpy as np

from .anatomical_labels import resolve_labels
from .case_contract import validate_case
from .case_io import case_digest
from .case_source_surfaces import selected_surface
from .voxel_output import Grid, Surface, voxelize


def registered_masks(case, edge_ids, vertices, faces, *, grid_config,
                     anatomical_labels, max_bytes, coverage, required_lesion_ids):
    validate_case(case)
    if coverage not in ('whole', 'roi') or case.get('lesions') or required_lesion_ids:
        raise ValueError('Registered surface lesions require explicit materialization; coverage must be whole or roi')
    exact_vertices, exact_faces, metadata = selected_surface(case, edge_ids)
    if not np.array_equal(vertices, exact_vertices) or not np.array_equal(faces, exact_faces):
        raise ValueError('Mask surface differs from registered case surface')
    grid = Grid(**grid_config)
    if grid.frame_id != case['frame']['id']:
        raise ValueError('mask grid frame differs from case')
    lower = np.asarray(grid.origin_xyz_mm) - np.asarray(grid.spacing_xyz_mm)/2
    upper = lower + np.asarray(grid.shape_zyx[::-1])*np.asarray(grid.spacing_xyz_mm)
    if coverage == 'whole' and (np.any(exact_vertices.min(0) < lower) or np.any(exact_vertices.max(0) > upper)):
        raise ValueError('whole output grid must cover selected surface bounds')
    labels, registry = resolve_labels(case, edge_ids, anatomical_labels)
    by_id = {p['part_id']: p for p in case['surface_parts']}
    surfaces, mapping, part_instances = [], {}, {}
    revision = case_digest(case)
    for instance, span in enumerate(metadata['parts'], 1):
        p = by_id[span['part_id']]
        chosen = {labels[i] for i in p['edge_ids']}
        if len(chosen) != 1:
            raise ValueError('Multiple segment labels require explicit surface partition')
        surfaces.append(Surface(instance, chosen.pop(), p['provenance'],
                                np.asarray(p['vertices_mm']), np.asarray(p['faces']),
                                grid.frame_id, f"case:{revision};part:{p['part_id']}"))
        part_instances[p['part_id']] = instance
        for ident in p['edge_ids']:
            mapping[ident] = [instance]
    # Reserve the empty lesion-label array in the same total allocation budget.
    lesion_bytes = math.prod(grid.shape_zyx)*4
    if type(max_bytes) is not int or max_bytes <= lesion_bytes:
        raise ValueError('Registered mask memory budget exceeded')
    volume = voxelize(surfaces, grid, max_bytes=max_bytes-lesion_bytes)
    volume.anatomical_registry = registry
    lesion_labels = np.zeros(grid.shape_zyx, dtype=np.uint32)
    lesion_meta = dict(schema='vv-toolbox.lesion-labels/1', case_revision=revision,
                       status='PASS', sampling_status='NOT APPLICABLE',
                       lesion_presence='none_declared', required_lesion_ids=[], registry=[],
                       edge_instances=mapping, grid=volume.metadata(),
                       definition='No lesions declared; zero labels do not establish absence of disease',
                       clinical_validity='NOT RUN')
    quality = dict(scope='Exact registered surfaces and center-sampled memberships',
                   coverage=coverage, surface_bounds_covered='PASS' if coverage=='whole' else 'NOT APPLICABLE',
                   source_bounds_mm=[exact_vertices.min(0).tolist(),exact_vertices.max(0).tolist()],
                   sampled_bounds_mm=[lower.tolist(),upper.tolist()],
                   surface_membership_equality='PASS', lesion_sampling='NOT APPLICABLE',
                   selected_edges=edge_ids, anatomical_label_registry=labels,
                   segment_label_registry=registry, case_revision=revision, grid=volume.metadata(),
                   instance_policy='One instance per registered surface part; multiple edges may share a part',
                   part_instances=part_instances, edge_instances=mapping,
                   anatomical_validation='NOT RUN')
    return volume, lesion_labels, lesion_meta, quality
