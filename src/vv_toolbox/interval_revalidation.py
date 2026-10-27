"""Regenerate saved candidates against a captured current Atlas scene."""
import numpy as np

from .atlas_interval_preview import preview_interval
from .interval_snapshot import decode_interval_snapshot


def prepare_revalidation(text, *, atlas_sha256):
    candidate, revision = decode_interval_snapshot(text, expected_atlas_sha256=atlas_sha256)
    edit = candidate['interval_edit']
    if (edit.get('arclength_origin') != 'first supplied section'
            or edit.get('fit', {}).get('transition_rings') != 3):
        raise ValueError('Unsupported saved interval generator settings')
    request = dict(part_id=candidate['part_id'], edge_id=candidate['edge_id'],
                   start_mm=edit['start_mm'], end_mm=edit['end_mm'], factor=edit['factor'],
                   max_displacement_mm=edit['fit']['displacement_bound_mm'],
                   absolute_scale_tolerance=edit['absolute_scale_tolerance'])
    return candidate, revision, request


def revalidate_interval_snapshot(workspace, text):
    saved, revision, request = prepare_revalidation(
        text, atlas_sha256=workspace.atlas.metadata.get('sha256'))
    originals = [*workspace.atlas.meshes, *workspace.neck_parts]
    source = next((p for p in originals if p['id'] == saved['part_id']), None)
    if source is None:
        raise ValueError('Saved source part is unavailable')
    source = workspace.atlas_modified_parts.get(source['id'], source)
    edges = [e for e in workspace.atlas_centerlines['edges'] if e['part_id'] == source['id']]
    if (len(edges) != 1 or edges[0]['id'] != saved['edge_id']
            or not np.array_equal(source['vertices'], saved['reference_vertices'])
            or not np.array_equal(source['faces'], saved['faces'])
            or not np.array_equal(edges[0]['points'], saved['centerline_mm'])):
        raise ValueError('Saved reference geometry or centerline differs from current scene')
    regenerated = preview_interval(workspace, request)
    if (not np.array_equal(regenerated['vertices'], saved['vertices'])
            or not np.array_equal(regenerated['faces'], saved['faces'])):
        raise ValueError('Regenerated candidate differs from saved geometry')
    regenerated['revalidation'] = dict(
        status='PASS', saved_revision=revision, geometry_exact=True,
        scope='Regeneration and implemented candidate checks against current scene',
        whole_anatomy_acceptance='NOT RUN')
    return regenerated
