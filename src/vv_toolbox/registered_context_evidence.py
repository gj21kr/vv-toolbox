"""Attach locally measured context only to the exact registered case revision."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from .case_io import case_digest


def attach_registered_context(case, root):
    revision=case_digest(case)
    evidence=Path(root)/'docs/evidence'
    binding=json.loads((evidence/'registered-shape-context-binding.json').read_text())
    if (binding.get('case_revision')!=revision or binding.get('binding')!='PASS'
            or binding.get('geometry_equality')!='EXACT'):
        raise ValueError('No context measurement bound to this exact case revision')
    raw=(evidence/'access-bend-context.json').read_bytes()
    if hashlib.sha256(raw).hexdigest()!=binding['evidence_sha256']:
        raise ValueError('Context measurement changed since geometry binding')
    context=json.loads(raw)
    baseline=json.loads((evidence/'resampled-access-context.json').read_text())
    rows=context['rows']; ids=[r['neighbor_id'] for r in rows]
    baseline_ids=[r['neighbor_id'] for r in baseline['rows']]
    count=binding['neighbor_count']
    if (context['completed']!=count or context['neighbor_count']!=count or len(ids)!=count
            or len(set(ids))!=count or set(ids)!=set(baseline_ids) or len(baseline_ids)!=count
            or context['context_sha256']!=binding['context_sha256']
            or context['context_sha256']!=baseline['context_sha256']
            or context['status']!=binding['status'] or context['status'] not in ('PASS','FAIL','UNKNOWN')):
        raise ValueError('Complete matching context scope required')
    if context['status']=='PASS' and (context['new_or_extended_contacts'] or context['unknown']
            or context['remaining_contacts'] or any(not r['after']['complete'] or not r['before']['complete'] for r in rows)):
        raise ValueError('Invalid context PASS')
    if 'registered_shape_edit' not in case.get('inspection',{}):
        raise ValueError('Registered shape inspection required')
    result=deepcopy(case)
    audit=result['inspection']['registered_shape_edit']
    audit.update(neighboring_vessels=context['status'],context=context,context_binding=deepcopy(binding),
                 accepted_for_generation=False)
    case_digest(result)
    return result
