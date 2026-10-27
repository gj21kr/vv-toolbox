"""Join synthetic surface, instance masks and lesion labels with explicit checks."""
import numpy as np

from .case_io import case_digest
from .case_surface import build_case_surface
from .lesion_labels import label_lesion_lumen
from .voxel_output import Grid, Surface, voxelize
from .anatomical_labels import resolve_labels


def build_case_masks(case, edge_ids, vertices, faces, *, spacing_mm, grid_config,
                     anatomical_labels=None, max_bytes=256*1024**2,
                     coverage='whole', required_lesion_ids=None):
    if 'surface_parts' in case:
        from .case_source_masks import registered_masks
        return registered_masks(case, edge_ids, vertices, faces, grid_config=grid_config,
                                anatomical_labels=anatomical_labels, max_bytes=max_bytes,
                                coverage=coverage, required_lesion_ids=required_lesion_ids)
    grid = Grid(**grid_config)
    revision = case_digest(case)
    if grid.frame_id != case['frame']['id']:
        raise ValueError('mask grid frame differs from case')
    lower = np.asarray(grid.origin_xyz_mm)-np.asarray(grid.spacing_xyz_mm)/2
    upper = lower+np.asarray(grid.shape_zyx[::-1])*np.asarray(grid.spacing_xyz_mm)
    if coverage not in ('whole','lesion_roi'):
        raise ValueError('unknown mask coverage')
    if coverage == 'whole' and (np.any(np.min(vertices,axis=0)<lower) or np.any(np.max(vertices,axis=0)>upper)):
        raise ValueError('whole output grid must cover selected surface bounds')
    if coverage == 'lesion_roi':
        if not required_lesion_ids:
            raise ValueError('lesion ROI must declare target lesions')
        for lesion in case.get('lesions',[]):
            if lesion['lesion_id'] not in required_lesion_ids:
                continue
            capsules = lesion.get('support_capsules_mm')
            if not capsules:
                raise ValueError('ROI coverage requires recorded lesion support')
            for capsule in capsules:
                points = np.asarray([capsule['start'],capsule['end']])
                if np.any(points.min(0)-capsule['radius_mm']<lower) or np.any(points.max(0)+capsule['radius_mm']>upper):
                    raise ValueError('ROI must cover target lesion support')
    labels, registry = resolve_labels(case, edge_ids, anatomical_labels)
    if set(labels)-set(edge_ids):
        raise ValueError('anatomical label assigned outside selected edges')
    surfaces, mapping = [], {}
    for instance,ident in enumerate(sorted(edge_ids),1):
        label = labels.get(ident,0)
        if len(edge_ids)==1:
            v,f = vertices,faces
        else:
            v,f,_ = build_case_surface(case,[ident],spacing_mm=spacing_mm)
        surfaces.append(Surface(instance,label,'estimated',v,f,grid.frame_id,
                                 f'case:{revision};edge:{ident}'))
        mapping[ident] = [instance]
    volume = voxelize(surfaces,grid,max_bytes=max_bytes)
    volume.anatomical_registry = registry
    if len(edge_ids)>1:
        union = voxelize([Surface(1,0,'estimated',vertices,faces,grid.frame_id,
                                  f'case:{revision};selected-union')],grid,max_bytes=max_bytes)
        if not np.array_equal(union.foreground,volume.foreground):
            raise ValueError('union surface and per-edge memberships disagree on output grid')
    lesion_labels, lesion_meta = label_lesion_lumen(volume,case,mapping,max_bytes=max_bytes,
        required_lesion_ids=required_lesion_ids)
    if lesion_meta['status'] != 'PASS':
        raise ValueError('one or more lesions have no sampled voxels')
    quality = {'scope':'selected surface bounds and voxel-grid equality only',
        'coverage':coverage,'surface_bounds_covered':'PASS' if coverage=='whole' else 'NOT APPLICABLE',
        'surface_membership_equality':'PASS',
        'lesion_sampling':lesion_meta['sampling_status'],'selected_edges':list(edge_ids),
        'anatomical_label_registry':labels,'segment_label_registry':registry,'case_revision':revision,
        'grid':volume.metadata()}
    return volume,lesion_labels,lesion_meta,quality
