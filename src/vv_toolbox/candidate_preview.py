"""Read-only registered synthetic preview, separate from the Atlas workspace."""
from io import BytesIO
import hashlib
import json
from pathlib import Path
import numpy as np
from .case_io import load_case

CANDIDATE_ID='right-iliac-source-profile'
MCA_CANDIDATE_ID='right-mca-saccular'
MCA_JUNCTION_CANDIDATE_ID='right-mca-junction-review'
MCA_FAIRING_CANDIDATE_ID='right-mca-retained-fairing'


def load_mca_candidate_preview(root, *, junction=False, fairing=False):
    """Load the generated MCA candidate and its exact, revision-bound audit."""
    root=Path(root)
    junction=junction or fairing
    name='mca-retained-fairing' if fairing else 'mca-tangent-transition-constant-earcut-flips-uniform'
    case_path='exports/mca-profile-regularization/case.snapshot.json' if junction else 'exports/atlas-case-inspection/all-arterial.snapshot.json'
    case,revision=load_case(root/case_path)
    context_path=('docs/evidence/mca-retained-fairing-context.json' if fairing else
                  'docs/evidence/mca-uniform-transition-context.json' if junction else
                  'docs/evidence/union-context-inspection.json')
    evidence=json.loads((root/context_path).read_text())
    regularization=json.loads((root/(f'docs/evidence/{name}.json' if junction else 'docs/evidence/union-regularization.json')).read_text())
    raw=(root/(f'exports/{name}/surface.npz' if junction else 'exports/union-regularization/surface.npz')).read_bytes()
    digest=hashlib.sha256(raw).hexdigest()
    audit=evidence if junction else evidence['reports']['after']
    if (evidence['case_revision']!=revision or regularization['case_revision']!=revision or
            regularization['artifact_sha256']!=digest or audit['artifact_sha256']!=digest):
        raise ValueError('candidate evidence mismatch')
    with np.load(BytesIO(raw),allow_pickle=False) as archive:
        vertices=archive['vertices_mm'].copy();faces=archive['faces'].copy()
        metadata=json.loads(str(archive['metadata'].item()))
    if metadata['case_revision']!=revision or metadata['frame']!=case['frame']:
        raise ValueError('candidate coordinate contract mismatch')
    if case['frame']['units']!='mm' or case['frame']['axes']!='LPS':
        raise ValueError('candidate requires LPS millimetres')
    if (vertices.ndim!=2 or vertices.shape[1]!=3 or not len(vertices) or
            not np.isfinite(vertices).all() or faces.ndim!=2 or faces.shape[1]!=3 or
            not len(faces) or not np.issubdtype(faces.dtype,np.integer) or
            faces.min()<0 or faces.max()>=len(vertices)):
        raise ValueError('invalid candidate mesh arrays')
    parent='FJ1692:e0'
    by_id={e['id']:e for e in case['edges']}
    ids=[row['edge_id'] for row in audit['results']]
    if (audit['parent_edge_id']!=parent or parent not in by_id or len(ids)!=len(set(ids)) or
            any(i not in by_id or i==parent for i in ids) or
            audit['context_edge_count']!=len(by_id)-1 or
            len(ids)+audit['aabb_separated_count']!=len(by_id)-1):
        raise ValueError('candidate context coverage mismatch')
    allowed={'SEPARATED_PROFILE','PROFILE_INTERIOR_WITNESS','UNKNOWN'}
    if any(row['status'] not in allowed for row in audit['results']):
        raise ValueError('invalid context status')
    status=('SEPARATED_PROFILES' if all(row['status']=='SEPARATED_PROFILE'
            for row in audit['results']) else 'REVIEW_REQUIRED')
    if status!=audit['status']:
        raise ValueError('candidate context status mismatch')
    resolved={r['edge_id']:dict(r) for r in audit['results']}
    refinement_ids=set()
    for refinement in evidence.get('refinements',[]) if junction else []:
        edge_id=refinement.get('edge_id')
        bound=refinement.get('lower_bound_mm')
        if (edge_id not in resolved or edge_id in refinement_ids or
                resolved[edge_id]['status']!='UNKNOWN' or
                refinement.get('status')!='SEPARATED_PROFILE' or
                refinement.get('unresolved_cells')!=0 or
                not isinstance(bound,(int,float)) or not np.isfinite(bound) or bound<=0):
            raise ValueError('candidate context refinement mismatch')
        refinement_ids.add(edge_id)
        resolved[edge_id]=dict(refinement)
    resolved_rows=list(resolved.values())
    resolved_status=('SEPARATED_PROFILES' if all(r['status']=='SEPARATED_PROFILE'
                     for r in resolved_rows) else 'REVIEW_REQUIRED')
    summary=dict(id=MCA_FAIRING_CANDIDATE_ID if fairing else MCA_JUNCTION_CANDIDATE_ID if junction else MCA_CANDIDATE_ID,
        title='우측 MCA 표면 보정 후보' if fairing else '우측 MCA 접합부 검사 후보' if junction else '우측 MCA 동맥류 합성 후보',revision=revision,
        edge_ids=[parent],frame=case['frame'],surface_sha256=digest,
        vertices=len(vertices),triangles=len(faces),read_only=True,
        scope='원래 Atlas와 별도로 생성한 단일 MCA 병변 후보',
        anatomy='UNKNOWN',whole_atlas_collision='NOT RUN',
        context_inspection=dict(status=resolved_status,context_edge_count=audit['context_edge_count'],
            separated_count=audit['aabb_separated_count']+sum(r['status']=='SEPARATED_PROFILE' for r in resolved_rows),
            review_edges=[r for r in resolved_rows if r['status']!='SEPARATED_PROFILE'],
            refined_count=len(refinement_ids),
            scope=audit['scope']))
    if junction:
        contact_path=('docs/evidence/mca-retained-fairing-uniform-full-surface-contacts.json' if fairing else
                      'docs/evidence/mca-uniform-full-surface-contacts.json')
        contact=json.loads((root/contact_path).read_text())
        if contact.get('artifact_sha256')!=digest or contact.get('case_revision')!=revision:
            raise ValueError('candidate self-contact evidence mismatch')
        if contact.get('scope')!='all distinct triangle pairs of this single vessel candidate':
            raise ValueError('candidate self-contact scope mismatch')
        contact_status=contact.get('full_self_intersection')
        if contact_status not in {'NO_CONTACT_DETECTED','CONTACT_DETECTED','UNKNOWN'}:
            raise ValueError('invalid self-contact status')
        if fairing:
            if (regularization.get('junction_collar_exact') is not True or
                    regularization.get('design_curve_exact') is not True or
                    regularization.get('closed_volume')!='PASS'):
                raise ValueError('candidate fairing preservation mismatch')
            counts=[regularization['after'][region]['above_90'] for region in ('retained','junction')]
            if any(type(n) is not int or n<0 for n in counts):
                raise ValueError('invalid candidate crease counts')
            regularization=dict(regularization,crease_screen='FAIL' if any(counts) else 'PASS',
                                smooth_junction=regularization.get('smoothness'))
        for field in ('crease_screen','smooth_junction'):
            if regularization.get(field) not in {'PASS','FAIL','UNKNOWN','NOT RUN'}:
                raise ValueError('invalid candidate quality status')
        summary['junction_inspection']=dict(
            crease_screen=regularization['crease_screen'],
            smoothness=regularization['smooth_junction'],
            self_contact=contact_status,
            note='자기교차 검사는 이 후보 표면에 한정. 매끄러움 수렴·해부학적 접합은 미확정.')
    return dict(summary=summary,vertices_mm=vertices,faces=faces,edges=[by_id[parent]])


def load_candidate_preview(root, candidate_id):
    from .bend_preview import CANDIDATE_ID as BEND_ID, load_bend_preview
    if candidate_id == BEND_ID:
        return load_bend_preview(root)
    from .resampled_access_preview import CANDIDATE_ID as RESAMPLED_ID, load_resampled_access_preview
    if candidate_id==RESAMPLED_ID:
        return load_resampled_access_preview(root)
    from .access_union_preview import CANDIDATE_ID as ACCESS_ID, load_access_union_preview
    if candidate_id == ACCESS_ID:
        return load_access_union_preview(root)
    from .carotid_preview import IDS, load_carotid_preview
    if candidate_id in IDS:
        return load_carotid_preview(root,candidate_id)
    from .protected_preview import REFERENCE_ID, CANDIDATE_ID as PROTECTED_ID, load_protected_preview
    if candidate_id in (REFERENCE_ID,PROTECTED_ID):
        return load_protected_preview(root,reference=candidate_id==REFERENCE_ID)
    if candidate_id==MCA_FAIRING_CANDIDATE_ID:
        return load_mca_candidate_preview(root,fairing=True)
    if candidate_id==MCA_JUNCTION_CANDIDATE_ID:
        return load_mca_candidate_preview(root,junction=True)
    if candidate_id==MCA_CANDIDATE_ID:
        return load_mca_candidate_preview(root)
    if candidate_id!=CANDIDATE_ID:
        raise ValueError('unknown candidate')
    root=Path(root)
    case,revision=load_case(root/'exports/synthetic-full-iliac-profiles/case.snapshot.json')
    if case['model_kind']!='synthetic':raise ValueError('synthetic candidate required')
    if case['frame']['units']!='mm' or case['frame']['axes']!='LPS':
        raise ValueError('candidate requires LPS millimetres')
    surface=json.loads((root/'docs/evidence/full-iliac-surface.json').read_text())
    separation=json.loads((root/'docs/evidence/full-iliac-mesh-separation.json').read_text())
    raw=(root/'exports/full-iliac-surface/surface.npz').read_bytes()
    digest=hashlib.sha256(raw).hexdigest()
    if (surface['case_revision']!=revision or separation['case_revision']!=revision or
            surface['surface']['status']!='PASS' or surface['surface']['sha256']!=digest or
            separation['surface_sha256']!=digest):
        raise ValueError('candidate evidence mismatch')
    with np.load(BytesIO(raw),allow_pickle=False) as archive:
        vertices=archive['vertices_mm'].copy();faces=archive['faces'].copy()
        metadata=json.loads(str(archive['metadata'].item()))
    ids=surface['edge_ids']
    if (metadata['case_revision']!=revision or metadata['frame']!=case['frame'] or
            metadata['edge_ids']!=ids or len(ids)!=len(set(ids))):
        raise ValueError('candidate coordinate or edge contract mismatch')
    if (vertices.ndim!=2 or vertices.shape[1]!=3 or not len(vertices) or
            not np.isfinite(vertices).all() or faces.ndim!=2 or faces.shape[1]!=3 or
            not len(faces) or not np.issubdtype(faces.dtype,np.integer) or
            faces.min()<0 or faces.max()>=len(vertices) or
            len(vertices)!=surface['surface']['vertices'] or len(faces)!=surface['surface']['triangles']):
        raise ValueError('invalid candidate mesh arrays')
    by_id={e['id']:e for e in case['edges']}
    if any(e not in by_id for e in ids):raise ValueError('candidate edge missing')
    # Return only selected surfaces/paths. The rest of the case is not rendered.
    summary=dict(id=CANDIDATE_ID,title='우측 외장골·고환동맥 합성 후보',revision=revision,
        edge_ids=ids,frame=case['frame'],surface_sha256=digest,
        vertices=len(vertices),triangles=len(faces),spacing_mm=surface['spacing_mm'],
        pair_surface_separation=separation['separation']['status'],
        pair_surface_gap_lower_bound_mm=separation['separation']['triangle_separation_bound_mm'],
        anatomy='UNKNOWN',whole_atlas_collision='NOT RUN',individual_surface_self_intersection='NOT RUN',
        read_only=True,scope='선택한 두 혈관의 전체 경로만 표시하는 합성 후보')
    return dict(summary=summary,vertices_mm=vertices,faces=faces,edges=[by_id[i] for i in ids])
