"""Versioned mask IDs for explicit cerebral segments and access-vessel extents."""
from copy import deepcopy
import hashlib
import math

from .case_io import _encode

REGISTRY = dict(schema='vv-toolbox.segment-label-registry/2', unknown=0, labels=[
    dict(id=1+side_index*6+artery_index*3+segment_index, side=side, artery=artery,
         segment=f'{prefix}{segment_index+1}')
    for side_index, side in enumerate(('L','R'))
    for artery_index, (artery,prefix) in enumerate((('ACA','A'),('MCA','M')))
    for segment_index in range(3)])
REGISTRY['labels'] += [
    dict(id=13+side_index*5+index, side=side, artery=artery, segment='whole')
    for side_index,side in enumerate(('L','R'))
    for index,artery in enumerate(('femoral','external_iliac','common_iliac',
                                  'common_carotid','internal_carotid'))]
REGISTRY['labels'] += [
    dict(id=23+index, side=side, artery=artery, segment='whole')
    for index,(side,artery) in enumerate((
        ('midline','abdominal_aorta'), ('midline','descending_thoracic_aorta'),
        ('midline','aortic_arch'), ('R','brachiocephalic')))]


def _extent_digest(edge):
    """Bind the declaration to this exact edge, including geometry and anatomy."""
    return hashlib.sha256(_encode({key:edge.get(key) for key in
        ('id','start','end','centerline_mm','radii_mm','anatomy')})).hexdigest()


def _access_assigned(edge):
    record=edge.get('access_label_assignment')
    return (isinstance(record,dict)
            and record.get('schema')=='vv-toolbox.access-label-assignment/1'
            and record.get('extent_sha256')==_extent_digest(edge)
            and isinstance(record.get('evidence_refs'),list)
            and bool(record['evidence_refs'])
            and all(isinstance(r,str) and r.strip() for r in record['evidence_refs']))


def assign_access_labels(case, assignments, *, expected_revision):
    """Declare complete edge extents explicitly; never infer labels from names.

    References record the operator's basis, not independently verified anatomy.
    Subsequent geometry edits invalidate these declarations until reviewed again.
    """
    from .case_contract import validate_case
    from .case_io import case_digest
    validate_case(case)
    if expected_revision != case_digest(case):
        raise ValueError('access label case revision mismatch')
    if not isinstance(assignments,list) or not assignments:
        raise ValueError('explicit access label assignments required')
    result=deepcopy(case)
    edges={edge['id']:edge for edge in result['edges']}
    registry={r['id']:r for r in REGISTRY['labels'] if r['id']>=13}
    used=set()
    for assignment in assignments:
        if not isinstance(assignment,dict):
            raise ValueError('invalid access label assignment')
        ident=assignment.get('edge_id')
        label=assignment.get('label_id')
        refs=assignment.get('evidence_refs')
        if not isinstance(ident,str) or ident not in edges or ident in used:
            raise ValueError('unknown or repeated access edge')
        if type(label) is not int or label not in registry:
            raise ValueError('registered access label required')
        if not isinstance(refs,list) or not refs or not all(isinstance(r,str) and r.strip() for r in refs):
            raise ValueError('full edge extent evidence references required')
        edge=edges[ident]
        if edge.get('centerline_mm') is None:
            raise ValueError('access label requires explicit edge geometry')
        used.add(ident)
        entry=registry[label]
        edge['anatomy'].update({k:entry[k] for k in ('side','artery','segment')})
        edge.pop('segment_assignment',None)
        edge['access_label_assignment']=dict(
            schema='vv-toolbox.access-label-assignment/1',
            extent_sha256=_extent_digest(edge), evidence_refs=deepcopy(refs),
            source_case_revision=expected_revision,
            scope='operator-declared full edge extent; not independent anatomical validation')
    validate_case(result)
    return result


def _materialized(edge):
    assignment=edge.get('segment_assignment')
    if not isinstance(assignment,dict):
        return False
    address=assignment.get('interval_address')
    tolerance=assignment.get('tolerance_mm')
    return (isinstance(assignment.get('original_edge_id'),str) and bool(assignment['original_edge_id'])
            and isinstance(address,list) and len(address)==2
            and all(type(x) in (int,float) and math.isfinite(x) for x in address)
            and 0 <= address[0] < address[1]
            and type(tolerance) in (int,float) and math.isfinite(tolerance) and tolerance>=0
            and all(isinstance(assignment.get(key),list) and assignment[key]
                    and all(isinstance(x,str) and x.strip() for x in assignment[key])
                    for key in ('boundary_ids','extent_review_refs')))


def resolve_labels(case, edge_ids, requested=None):
    """Validate numeric labels against side/artery/segment, not against anatomy truth."""
    if requested is not None and not isinstance(requested,dict):
        raise ValueError('Anatomical labels must be an edge-to-ID mapping')
    requested={} if requested is None else requested
    if set(requested)-set(edge_ids):
        raise ValueError('Anatomical label assigned outside selected edges')
    by_id={e['id']:e for e in case['edges']}
    lookup={(r['side'],r['artery'],r['segment']):r['id'] for r in REGISTRY['labels']}
    result={}
    for ident in edge_ids:
        edge=by_id[ident]
        anatomy=edge['anatomy']
        canonical=lookup.get(tuple(anatomy[k] for k in ('side','artery','segment')),0)
        supported = _access_assigned(edge) if canonical>=13 else _materialized(edge)
        expected=canonical if supported else 0
        chosen=requested.get(ident,expected)
        if type(chosen) is not int or chosen < 0 or (chosen and chosen!=expected):
            raise ValueError('Anatomical label conflicts with registered segment or materialization evidence')
        result[ident]=chosen
    registry=deepcopy(REGISTRY)
    registry['sha256']=hashlib.sha256(_encode(REGISTRY)).hexdigest()
    registry['evidence_scope']='Explicit segment or full-edge extent references; not independent anatomical validation'
    return result,registry
