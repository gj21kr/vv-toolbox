from copy import deepcopy
import pytest
from vv_toolbox.anatomical_labels import REGISTRY, resolve_labels


def fixture():
    assignment=dict(original_edge_id='source', interval_address=[0,1],
                    tolerance_mm=.01, boundary_ids=['boundary'],extent_review_refs=['synthetic fixture review'])
    edges=[dict(id=str(r['id']),anatomy={k:r[k] for k in ('side','artery','segment')},
                segment_assignment=deepcopy(assignment)) for r in REGISTRY['labels'][:12]]
    return {'edges':edges}


def test_all_twelve_ids_are_fixed_and_order_independent():
    case=fixture()
    labels,registry=resolve_labels(case,[e['id'] for e in case['edges']])
    assert labels=={str(i):i for i in range(1,13)}
    reverse,_=resolve_labels(case,list(reversed(labels)))
    assert reverse==labels
    assert registry['labels'][0]==dict(id=1,side='L',artery='ACA',segment='A1')
    assert registry['labels'][11]==dict(id=12,side='R',artery='MCA',segment='M3')


def test_missing_or_fake_materialization_stays_unknown():
    for assignment in (None,True,{},dict(original_edge_id='e')):
        case=fixture();case['edges'][0]['segment_assignment']=assignment
        labels,_=resolve_labels(case,['1'])
        assert labels=={'1':0}
        with pytest.raises(ValueError,match='evidence'):
            resolve_labels(case,['1'],{'1':1})


@pytest.mark.parametrize('requested',[{'1':7},{'1':True},{'1':-1},{'other':1},[]])
def test_wrong_side_or_invalid_explicit_labels_rejected(requested):
    with pytest.raises(ValueError):
        resolve_labels(fixture(),['1'],requested)


def test_explicit_unknown_can_suppress_but_not_invent_labels():
    labels,_=resolve_labels(fixture(),['1'],{'1':0})
    assert labels=={'1':0}


def test_access_extents_are_explicit_and_geometry_bound():
    from vv_toolbox.anatomical_labels import assign_access_labels
    from vv_toolbox.case_io import case_digest
    from test_synthetic_routes import fixture as source_fixture
    case,_=source_fixture()
    before=deepcopy(case)
    for entry in REGISTRY['labels'][12:]:
        result=assign_access_labels(case,[dict(edge_id='a',label_id=entry['id'],
            evidence_refs=['synthetic whole-edge fixture'])],expected_revision=case_digest(case))
        assert resolve_labels(result,['a'])[0]=={'a':entry['id']}
        for field in ('radii_mm','centerline_mm','anatomy'):
            changed=deepcopy(result)
            edge=changed['edges'][0]
            if field=='radii_mm': edge[field][0]+=.1
            elif field=='centerline_mm': edge[field][0][1]+=.1
            else: edge[field]['side']='unknown'
            assert resolve_labels(changed,['a'])[0]=={'a':0}
    assert case==before


def test_access_names_and_cerebral_records_do_not_imply_extent_review():
    case=fixture()
    case['edges'][0]['anatomy']=dict(side='L',artery='femoral',segment='whole')
    assert resolve_labels(case,['1'])[0]=={'1':0}
    with pytest.raises(ValueError):
        resolve_labels(case,['1'],{'1':13})


@pytest.mark.parametrize('kind',['revision','missing_refs','wrong_id','duplicate','unknown_edge'])
def test_access_assignment_rejects_invalid_request_without_mutation(kind):
    from vv_toolbox.anatomical_labels import assign_access_labels
    from vv_toolbox.case_io import case_digest
    from test_synthetic_routes import fixture as source_fixture
    case,_=source_fixture(); before=deepcopy(case)
    assignments=[dict(edge_id='a',label_id=13,evidence_refs=['fixture'])]
    revision=case_digest(case)
    if kind=='revision': revision='stale'
    elif kind=='missing_refs': assignments[0]['evidence_refs']=[]
    elif kind=='wrong_id': assignments[0]['label_id']=1
    elif kind=='duplicate': assignments*=2
    else: assignments[0]['edge_id']='absent'
    with pytest.raises(ValueError):
        assign_access_labels(case,assignments,expected_revision=revision)
    assert case==before


@pytest.mark.parametrize('with_lesion',[False,True])
def test_access_labels_reach_mask_and_saved_metadata(tmp_path,with_lesion):
    import json
    import numpy as np
    from vv_toolbox.anatomical_labels import assign_access_labels
    from vv_toolbox.case_io import case_digest
    from vv_toolbox.case_surface import build_case_surface
    from vv_toolbox.case_masks import build_case_masks
    from vv_toolbox.volume_cli import save_volume
    from vv_toolbox.lesions import concentric_stenosis
    from test_batch import two_vessel_fixture
    case,operation=two_vessel_fixture()
    if with_lesion:
        case=concentric_stenosis(case,case_id='label-fixture',seed=0,**operation)
    else:
        case['model_kind']='synthetic'
        case['generation']=dict(seed=0,generator_version='synthetic-label-fixture/1',config={})
    case=assign_access_labels(case,[
        dict(edge_id=edge['id'],label_id=13+index*5,evidence_refs=['synthetic extent fixture'])
        for index,edge in enumerate(case['edges'])],expected_revision=case_digest(case))
    ids=[e['id'] for e in case['edges']]
    vertices,faces,_=build_case_surface(case,ids,spacing_mm=.3)
    volume,lesion_labels,lesion_meta,quality=build_case_masks(case,ids,vertices,faces,spacing_mm=.3,
        grid_config=dict(shape_zyx=[7,17,27],spacing_xyz_mm=[1,1,1],
                         origin_xyz_mm=[-3,-3,-3],frame_id='fixture'))
    assert volume.anatomical[3,3,13]==13
    assert volume.anatomical[3,13,13]==18
    assert quality['anatomical_label_registry']==dict(zip(ids,[13,18]))
    path=tmp_path/'access.npz'
    save_volume(path,volume,lesion_labels=lesion_labels,lesion_metadata=lesion_meta)
    with np.load(path) as output:
        metadata=json.loads(str(output['metadata']))
        assert len(metadata['anatomical_registry']['labels'])==26
        assert set(np.unique(output['anatomical']))=={0,13,18}
        if not with_lesion:
            assert not output['lesion_instance'].any()
            assert quality['lesion_sampling']=='NOT APPLICABLE'
            assert json.loads(str(output['lesion_metadata']))['lesion_presence']=='none_declared'
    if not with_lesion:
        with pytest.raises(ValueError,match='target lesions'):
            build_case_masks(case,ids,vertices,faces,spacing_mm=.3,
                grid_config=dict(shape_zyx=[7,17,27],spacing_xyz_mm=[1,1,1],
                                 origin_xyz_mm=[-3,-3,-3],frame_id='fixture'),
                coverage='lesion_roi')
