"""Candidate surface-derived masks and explicitly defined synthetic sac labels."""
import math

import numpy as np
from scipy.ndimage import label

from .saccular_surface import build_saccular_candidate, _sac_field, _parent_field
from .voxel_output import Grid, Surface, voxelize


def build_saccular_masks(case, spec, *, surface_spacing_mm, grid_config,
                         coverage='whole', max_grid_voxels=2_000_000,
                         max_bytes=256*1024**2):
    """Rebuild the bound surface before voxelizing; never accept unrelated meshes.

    Labels are a synthetic geometric convention, not anatomical/clinical truth:
    sac lumen above its declared neck, plus added lumen below that plane relative
    to the baseline circular parent profile. Baseline parent lumen stays label 0.
    """
    grid = Grid(**grid_config)
    if grid.frame_id != case['frame']['id']:
        raise ValueError('mask grid frame differs from case')
    if coverage not in ('whole', 'sac_roi'):
        raise ValueError('explicit whole or sac_roi coverage required')
    count = math.prod(grid.shape_zyx)
    # Reserve uint32 lesion/component arrays and coordinate/field work chunks
    # in addition to the voxelizer's own allocation checks.
    reserved = count*8 + 2*1024**2
    if type(max_bytes) is not int or max_bytes <= reserved:
        raise ValueError('saccular label memory budget exceeded')
    vertices, faces, surface_meta = build_saccular_candidate(
        case, spec, spacing_mm=surface_spacing_mm, max_grid_voxels=max_grid_voxels)
    lower = np.asarray(grid.origin_xyz_mm)-np.asarray(grid.spacing_xyz_mm)/2
    upper = lower+np.asarray(grid.shape_zyx[::-1])*np.asarray(grid.spacing_xyz_mm)
    if coverage == 'whole':
        bounds = vertices.min(0), vertices.max(0)
    else:
        # Same conservative loft + blending enclosure used by the generator.
        p, neck = spec['parameters'], spec['neck']
        center, normal = np.asarray(neck['center_mm']), np.asarray(neck['normal'])
        extent = (np.abs(neck['width_axis'])*p['dome_width_mm']/2
                  + np.abs(neck['depth_axis'])*p['dome_depth_mm']/2)
        a, b = center-normal*p['blending_extent_mm'], center+normal*p['height_perpendicular_mm']
        bounds = (np.minimum(a,b)-extent-p['blending_extent_mm'],
                  np.maximum(a,b)+extent+p['blending_extent_mm'])
    if np.any(bounds[0] < lower) or np.any(bounds[1] > upper):
        raise ValueError('mask grid does not cover declared surface or sac support bounds')
    ident = spec['parameters']['edge_id']
    source_ref = f"case:{spec['case_revision']};sac-spec:{surface_meta['specification_sha256']};edge:{ident}"
    volume = voxelize([Surface(1,0,'estimated',vertices,faces,grid.frame_id,source_ref)],
                      grid,max_bytes=max_bytes-reserved)
    _, components = label(volume.foreground)
    if components != 1:
        raise ValueError('sampled candidate lumen is empty or disconnected; refine the mask grid')
    labels = np.zeros(count,dtype=np.uint32)
    normal, center = np.asarray(spec['neck']['normal']), np.asarray(spec['neck']['center_mm'])
    edge = next(e for e in case['edges'] if e['id'] == ident)
    points, radii = np.asarray(edge['centerline_mm']), np.asarray(edge['radii_mm'])
    dome_count, added_neck_count = 0, 0
    for offset in range(0,count,2048):
        ids = np.arange(offset,min(offset+2048,count))
        ids = ids[volume.foreground.reshape(-1)[ids]]
        if not len(ids):
            continue
        zyx = np.asarray(np.unravel_index(ids,grid.shape_zyx)).T
        world = zyx[:,::-1]*np.asarray(grid.spacing_xyz_mm)+np.asarray(grid.origin_xyz_mm)
        depth = (world-center) @ normal
        dome = (depth > 0) & (_sac_field(world,spec) <= 0)
        p = spec['parameters']
        local_width = (world-center) @ np.asarray(spec['neck']['width_axis'])
        local_depth = (world-center) @ np.asarray(spec['neck']['depth_axis'])
        support = ((np.abs(local_width) <= p['dome_width_mm']/2+p['blending_extent_mm'])
                   & (np.abs(local_depth) <= p['dome_depth_mm']/2+p['blending_extent_mm'])
                   & (depth >= -2*p['blending_extent_mm']))
        added_neck = support & (depth <= 0) & (_parent_field(world,points,radii) > 0)
        labels[ids[dome | added_neck]] = 1
        dome_count += int(dome.sum())
        added_neck_count += int(added_neck.sum())
    if not dome_count:
        raise ValueError('sac has no sampled lumen voxels; choose a finer mask grid')
    metadata = dict(schema='vv-toolbox.saccular-labels/1', status='CANDIDATE',
        case_revision=spec['case_revision'], specification_sha256=surface_meta['specification_sha256'],
        coverage=coverage, grid=volume.metadata(), surface=surface_meta,
        definition='foreground intersect sac field strictly above neck plane, plus added lumen outside baseline parent below/on plane within declared sac/blend support',
        excluded='baseline parent lumen; wall/plaque/tissue; inferred anatomical segment labels',
        registry=[dict(label=1,lesion_id=spec['parameters']['lesion_id'],edge_id=ident)],
        voxel_counts=dict(foreground=int(volume.foreground.sum()),sac_above_neck=dome_count,
                          added_neck=added_neck_count,labelled=int((labels>0).sum())),
        checks=dict(surface_bounds_covered='PASS' if coverage=='whole' else 'NOT APPLICABLE',
                    sac_support_covered='PASS' if coverage=='sac_roi' else 'NOT APPLICABLE',
                    labels_inside_foreground='PASS',
                    sampled_lumen_connected='PASS',
                    anatomical_segment_labels='UNKNOWN',clinical_validity='NOT RUN'),
        budget_scope='mask arrays and voxelizer workspace; surface generation has separate grid budget',
        limitations='Single-parent candidate only. Centre sampling does not certify fine-neck preservation. '
                    'Label definition is a simulator convention, not patient ground truth.')
    return volume, labels.reshape(grid.shape_zyx), metadata
