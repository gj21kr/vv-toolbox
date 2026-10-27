"""Capture current Atlas artery surfaces without losing their edit provenance."""
from copy import deepcopy

from .case_source_surfaces import attach_surfaces


def capture_surfaces(case, parts, *, modifications=None, interval_edits=None):
    result = deepcopy(case)
    modifications, interval_edits = modifications or {}, interval_edits or {}
    by_id = {p['id']: p for p in parts}
    if len(by_id) != len(parts):
        raise ValueError('Duplicate Atlas surface identities')
    bindings = {}
    for edge in result['edges']:
        bindings.setdefault(edge['source_part_id'], []).append(edge['id'])
    if not set(bindings) <= set(by_id):
        raise ValueError('Case paths lack corresponding Atlas surfaces')
    edited = set(bindings) & (set(modifications) | set(interval_edits))
    estimated = {e['source_part_id'] for e in result['edges'] if e['geometry_kind']=='estimated'}
    if edited or estimated:
        prior_generation=deepcopy(result.get('generation'))
        result['model_kind'] = 'synthetic'
        result['generation'] = dict(seed=0, generator_version='atlas-surface-capture-v1',
            config=dict(parameter_edits={p:deepcopy(modifications[p]) for p in sorted(edited) if p in modifications},
                        interval_edits={p:deepcopy(interval_edits[p]) for p in sorted(edited) if p in interval_edits},
                        source_generation=prior_generation,
                        seed_use='deterministic capture; no random sampling'))
    surfaces = []
    for pid, ids in bindings.items():
        p = by_id[pid]
        if p['layer'] != 'arterial':
            raise ValueError('Arterial case cannot capture a venous surface')
        surfaces.append(dict(part_id=pid, edge_ids=ids, frame_id=result['frame']['id'],
            provenance='estimated' if pid in edited or pid in estimated else 'source', source_ids=['bp3d'],
            vertices_mm=p['vertices'].tolist(), faces=p['faces'].tolist()))
    for edge in result['edges']:
        pid = edge['source_part_id']
        if pid in modifications:
            edge['geometry_kind'] = 'estimated'
            edge['evidence_status'] = 'synthetic_estimate'
            edge['derivation']['parameter_edits'] = deepcopy(modifications[pid])
        if pid in edited:
            edge['derivation']['radius_status'] = 'reference_profile_not_current_surface_measurement'
    result.setdefault('inspection', {})['atlas_scene_capture'] = dict(
        includes_edits=bool(edited), includes_estimates=bool(estimated),
        estimated_parts=sorted(estimated), captured_parts=sorted(bindings),
        estimated_metadata={pid:deepcopy(by_id[pid].get('metadata',{})) for pid in sorted(estimated)},
        edited_parts=sorted(edited),
        omitted_arterial_parts=sorted(p['id'] for p in parts if p['layer']=='arterial' and p['id'] not in bindings),
        excluded_edit_parts=sorted((set(modifications)|set(interval_edits))-set(bindings)),
        scope='Atlas arteries with mapped paths; omitted parts are not fabricated',
        anatomical_validation='NOT RUN')
    return attach_surfaces(result, surfaces)
