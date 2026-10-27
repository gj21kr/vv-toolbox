"""Workspace adapter for detached candidate radius calculations."""
import copy
import trimesh

from .candidate_radius_session import CandidateRadiusSession
from .radius_context import inspect_radius_context


def snapshot_context(workspace, candidate):
    if workspace.atlas is None:
        raise ValueError('Atlas context unavailable')
    excluded = set(candidate['face_lineage']['source_names'])
    context = {}
    for part in [*workspace.atlas.meshes, *workspace.neck_parts]:
        if part['id'] in excluded or part['layer'] not in ('arterial','systemic_venous','hepatic_portal'):
            continue
        effective = workspace.atlas_modified_parts.get(part['id'], part)
        context[part['id']] = trimesh.Trimesh(effective['vertices'].copy(), effective['faces'].copy(), process=False)
    if not context:
        raise ValueError('Nonempty vascular context required')
    return context


def inspect_result(before, result, context, *, progress=None, _validation_cache=None):
    if progress is not None and not callable(progress):
        raise ValueError('Progress callback must be callable')
    def notify(event):
        if progress is not None:
            progress(dict(phase='context', completed=event['completed'], total=event['total']))
    notify(dict(completed=0, total=len(context)))
    candidate = result['candidate']
    report = inspect_radius_context(
        trimesh.Trimesh(before['vertices_mm'], before['faces'], process=False),
        trimesh.Trimesh(candidate['vertices_mm'], candidate['faces'], process=False), context,
        progress=notify, _validation_cache=_validation_cache)
    candidate['radius_context'] = report
    audit = result['audit']
    audit['neighbor_contact'] = report['status']
    audit['neighbor_context'] = dict(status=report['status'], decision_reason=report['decision_reason'],
        context_sha256=report['context_sha256'], neighbors=len(report['rows']),
        new_or_extended_contacts=report['new_or_extended_contacts'], unknown=report['unknown'],
        remaining_contacts=report['remaining_contacts'],
        unknown_reasons={row['neighbor_id']:list(dict.fromkeys(
            row[phase].get('containment',{}).get('reason','Surface-contact inspection incomplete')
            for phase in ('before','after') if not row[phase]['complete']))
            for row in report['rows'] if row['neighbor_id'] in report['unknown']})
    candidate['summary']['radius_edit'] = copy.deepcopy(audit)
    summary = candidate['summary']
    if 'access_union' in summary:
        summary['access_union'].update(context_status=report['status'],
            context_neighbors=len(report['rows']), context_completed=len(report['rows']),
            contacts=report['remaining_contacts'], unknown=report['unknown'])
    else:
        summary['carotid_union']['new_contacting_neighbors'] = len(report['new_or_extended_contacts'])
    return result


def require_clear_result(before, result, context):
    inspect_result(before, result, context)
    if result['audit']['neighbor_contact'] != 'PASS':
        raise ValueError('Restored edit did not clear current vascular context')
    if 'access_union' in result['candidate']['summary'] and result['audit'].get('centerline_containment', {}).get('status') != 'PASS':
        raise ValueError('Restored edit did not preserve all access centerlines')


def prepare(workspace, raw):
    if workspace.source != 'candidate' or not workspace.candidate.get('source_centerlines'):
        raise ValueError('Select a union candidate with explicit source centerlines first')
    if not isinstance(raw, dict) or set(raw) != {'source_name', 'scale', 'transition_mm', 'max_displacement_mm'}:
        raise ValueError('Source, scale, transition and displacement bound required')
    if raw['source_name'] != workspace.candidate['summary'].get('selected_source'):
        raise ValueError('Selected source changed; select the vessel again')
    if any(type(raw[key]) not in (int, float) for key in ('scale', 'transition_mm', 'max_displacement_mm')):
        raise ValueError('Numeric radius parameters required')
    session = getattr(workspace, 'candidate_radius_session', None)
    if session is None:
        session = CandidateRadiusSession(workspace.candidate)
        workspace.candidate_radius_session = session
    if session.status()['preview_token']:
        raise ValueError('Apply or discard the current preview first')
    return session, session.snapshot(raw['source_name']), workspace.generation


def display(workspace, candidate):
    """Replace displayed geometry, rolling back if drawing fails."""
    previous = workspace.candidate
    candidate = copy.deepcopy(candidate)
    candidate.pop('display_faces', None)
    candidate['summary']['selected_source'] = None
    candidate['summary']['source_selection'] = None
    try:
        workspace.candidate = candidate
        workspace.draw_candidate()
        workspace.metrics.content = workspace.description(workspace.graph)
    except Exception:
        workspace.candidate = previous
        workspace.draw_candidate()
        raise


def publish(workspace, session, generation, result):
    if (workspace.source != 'candidate' or workspace.generation != generation
            or workspace.candidate_radius_session is not session):
        raise ValueError('Scene changed while computing; radius preview discarded')
    receipt = session.publish(result)
    try:
        display(workspace, session.preview())
    except Exception:
        session.discard()
        raise
    workspace.generation += 1
    return receipt


def action(workspace, raw):
    if not isinstance(raw, dict) or set(raw) != {'action', 'token'}:
        raise ValueError('Radius action and token required')
    session = getattr(workspace, 'candidate_radius_session', None)
    if workspace.source != 'candidate' or session is None:
        raise ValueError('No candidate radius session')
    # Work on a detached transaction so a display failure cannot consume undo.
    replacement = copy.deepcopy(session)
    if raw['action'] == 'apply':
        if session.preview()['summary']['radius_edit'].get('neighbor_contact') != 'PASS':
            raise ValueError('Context clearance required; inspect or discard this preview')
        summary = session.preview()['summary']
        if 'access_union' in summary and summary['radius_edit'].get('centerline_containment', {}).get('status') != 'PASS':
            raise ValueError('Complete access centerline clearance required')
        if not isinstance(raw['token'], str):
            raise ValueError('Preview token required')
        candidate = replacement.apply(raw['token'])
    elif raw['action'] == 'discard':
        if not raw['token'] or raw['token'] != replacement.status()['preview_token']:
            raise ValueError('Preview token mismatch')
        replacement.discard()
        candidate = replacement.current()
    elif raw['action'] == 'undo':
        if raw['token'] is not None or replacement.status()['preview_token']:
            raise ValueError('Discard preview before undo')
        candidate = replacement.undo()
    else:
        raise ValueError('Unknown radius action')
    display(workspace, candidate)
    workspace.candidate_radius_session = replacement
    workspace.generation += 1
