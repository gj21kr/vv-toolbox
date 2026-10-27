import json
import shutil
import pytest
from test_mca_candidate_preview import bundle
from vv_toolbox.candidate_preview import load_candidate_preview, MCA_JUNCTION_CANDIDATE_ID
from vv_toolbox.candidate_preview import MCA_FAIRING_CANDIDATE_ID


@pytest.fixture
def junction_bundle(bundle):
    name='mca-tangent-transition-constant-earcut-flips-uniform'
    destination=bundle/'exports/mca-profile-regularization'
    destination.mkdir()
    shutil.copyfile(bundle/'exports/atlas-case-inspection/all-arterial.snapshot.json',
                    destination/'case.snapshot.json')
    shutil.copytree(bundle/'exports/union-regularization',bundle/'exports'/name)
    docs=bundle/'docs/evidence'
    regularization=json.loads((docs/'union-regularization.json').read_text())
    regularization.update(crease_screen='PASS',smooth_junction='UNKNOWN')
    (docs/f'{name}.json').write_text(json.dumps(regularization))
    audit=json.loads((docs/'union-context-inspection.json').read_text())['reports']['after']
    audit['case_revision']=regularization['case_revision']
    (docs/'mca-uniform-transition-context.json').write_text(json.dumps(audit))
    (docs/'mca-uniform-full-surface-contacts.json').write_text(json.dumps(dict(
        artifact_sha256=regularization['artifact_sha256'],case_revision=regularization['case_revision'],
        scope='all distinct triangle pairs of this single vessel candidate',
        full_self_intersection='NO_CONTACT_DETECTED')))
    return bundle


def test_junction_preview_keeps_unknown_acceptance(junction_bundle):
    summary=load_candidate_preview(junction_bundle,MCA_JUNCTION_CANDIDATE_ID)['summary']
    assert summary['id']==MCA_JUNCTION_CANDIDATE_ID
    assert summary['read_only']
    assert summary['junction_inspection']['smoothness']=='UNKNOWN'
    assert summary['junction_inspection']['self_contact']=='NO_CONTACT_DETECTED'
    assert summary['context_inspection']['status']=='REVIEW_REQUIRED'
    assert summary['anatomy']=='UNKNOWN'


@pytest.mark.parametrize('preserved',[True,False])
def test_fairing_preview_requires_its_own_evidence(junction_bundle,preserved):
    root=junction_bundle
    docs=root/'docs/evidence'
    name='mca-tangent-transition-constant-earcut-flips-uniform'
    shutil.copytree(root/'exports'/name,root/'exports/mca-retained-fairing')
    report=json.loads((docs/f'{name}.json').read_text())
    report.update(junction_collar_exact=preserved,design_curve_exact=True,
                  closed_volume='PASS',smoothness='UNKNOWN',
                  after={'retained':{'above_90':0},'junction':{'above_90':0}})
    (docs/'mca-retained-fairing.json').write_text(json.dumps(report))
    with pytest.raises(FileNotFoundError):
        load_candidate_preview(root,MCA_FAIRING_CANDIDATE_ID)
    shutil.copyfile(docs/'mca-uniform-transition-context.json',docs/'mca-retained-fairing-context.json')
    shutil.copyfile(docs/'mca-uniform-full-surface-contacts.json',docs/'mca-retained-fairing-uniform-full-surface-contacts.json')
    if not preserved:
        with pytest.raises(ValueError,match='preservation mismatch'):
            load_candidate_preview(root,MCA_FAIRING_CANDIDATE_ID)
    else:
        summary=load_candidate_preview(root,MCA_FAIRING_CANDIDATE_ID)['summary']
        assert summary['id']==MCA_FAIRING_CANDIDATE_ID
        assert summary['read_only']
        assert summary['junction_inspection']['smoothness']=='UNKNOWN'


@pytest.mark.parametrize('field,value',[
    ('artifact_sha256','0'*64),('case_revision','wrong'),('scope','new transition only')])
def test_junction_preview_rejects_mismatched_contact_evidence(junction_bundle,field,value):
    path=junction_bundle/'docs/evidence/mca-uniform-full-surface-contacts.json'
    report=json.loads(path.read_text())
    report[field]=value
    path.write_text(json.dumps(report))
    with pytest.raises(ValueError,match='mismatch'):
        load_candidate_preview(junction_bundle,MCA_JUNCTION_CANDIDATE_ID)


@pytest.mark.parametrize('invalid',[None,'duplicate','witness','unresolved','nonfinite','foreign'])
def test_refinement_requires_unresolved_edge_and_positive_certificate(junction_bundle,invalid):
    path=junction_bundle/'docs/evidence/mca-uniform-transition-context.json'
    report=json.loads(path.read_text())
    row=next(r for r in report['results'] if r['status']!='SEPARATED_PROFILE')
    row['status']='UNKNOWN'
    refinement=dict(edge_id=row['edge_id'],status='SEPARATED_PROFILE',
                    unresolved_cells=0,lower_bound_mm=.002)
    report['refinements']=[refinement]
    if invalid=='duplicate':report['refinements'].append(dict(refinement))
    if invalid=='witness':row['status']='PROFILE_INTERIOR_WITNESS'
    if invalid=='unresolved':refinement['unresolved_cells']=1
    if invalid=='nonfinite':refinement['lower_bound_mm']=float('nan')
    if invalid=='foreign':refinement['edge_id']='not-in-context'
    path.write_text(json.dumps(report))
    if invalid:
        with pytest.raises(ValueError,match='refinement mismatch'):
            load_candidate_preview(junction_bundle,MCA_JUNCTION_CANDIDATE_ID)
    else:
        inspection=load_candidate_preview(junction_bundle,MCA_JUNCTION_CANDIDATE_ID)['summary']['context_inspection']
        assert inspection['refined_count']==1
        assert inspection['status']=='SEPARATED_PROFILES'
        assert inspection['review_edges']==[]
        assert inspection['separated_count']==inspection['context_edge_count']
