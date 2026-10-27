import json
from copy import deepcopy

import pytest

from vv_toolbox.batch import generate_stenosis_batch
from vv_toolbox.case_io import load_case


def fixture():
    case = {'schema':'vv-toolbox.case/1','case_id':'base','base_model_id':'fixture',
      'model_kind':'source','generation':None,'split':'unassigned',
      'frame':{'id':'fixture','origin':'fixture','axes':'LPS','units':'mm'},
      'sources':[{'id':'s','sha256':'a'*64,'license_ref':'fixture'}],
      'nodes':{n:{'kind':'unresolved','evidence_status':'unresolved','position_mm':p}
                for n,p in [('a',[0,0,0]),('b',[20,0,0])]},
      'edges':[{'id':'e','start':'a','end':'b','source_ids':['s'],'geometry_kind':'source',
        'evidence_status':'unresolved','anatomy':{'artery':'ACA','side':'L','segment':'A2','branch_id':'e'},
        'centerline_mm':[[0,0,0],[20,0,0]],'radii_mm':[2,2]}]}
    operation = dict(edge_id='e',lesion_id='l',region='aca',center_mm=10,length_mm=8,
        severity_percent=40,measurement_method='local_baseline_diameter',sample_spacing_mm=.5)
    return case,operation


@pytest.mark.parametrize('flag', [False, None, 0, 'true'])
def test_inspection_generation_restriction_survives_import(tmp_path, flag):
    case, operation = fixture()
    case['inspection'] = {'access_candidate': {'accepted_for_generation': flag}}
    original = deepcopy(case)
    with pytest.raises(ValueError, match='not approved for generation'):
        generate_stenosis_batch(case, [[operation]], tmp_path/'out', target_count=1,
                               max_attempts=1, seed=0, spacing_mm=.3)
    assert not (tmp_path/'out').exists()
    assert case == original


def test_generation_flag_does_not_bypass_lesion_validation(tmp_path):
    case, operation = fixture()
    case['inspection'] = {'access_candidate': {'accepted_for_generation': True}}
    operation['severity_percent'] = 200
    report = generate_stenosis_batch(case, [[operation]], tmp_path/'out', target_count=1,
                                    max_attempts=1, seed=0, spacing_mm=.3)
    assert report['status'] == 'FAIL'
    assert report['accepted_count'] == 0


@pytest.mark.parametrize('damage', ['frame', 'lesion_grid', 'label', 'count', 'edge'])
def test_mask_case_binding_rejects_self_consistent_file_hashes(tmp_path, damage):
    import numpy as np
    from vv_toolbox.case_artifacts import verify_manifest, verify_masks, write_manifest
    case, operation = fixture()
    config = {'grid_config': {'shape_zyx': [7, 7, 27], 'spacing_xyz_mm': [1., 1., 1.],
                             'origin_xyz_mm': [-3., -3., -3.], 'frame_id': 'fixture'}}
    report = generate_stenosis_batch(case, [[operation]], tmp_path/'out', target_count=1,
        max_attempts=1, seed=0, spacing_mm=.3, mask_config=config)
    assert report['status'] == 'PASS'
    folder = tmp_path/'out/case-00000'
    with np.load(folder/'mask.npz', allow_pickle=False) as saved:
        data = {k: saved[k] for k in saved.files}
    metadata = json.loads(str(data['metadata']))
    lesion = json.loads(str(data['lesion_metadata']))
    if damage == 'frame':
        metadata['frame_id'] = lesion['grid']['frame_id'] = 'other-case'
    elif damage == 'lesion_grid':
        lesion['grid']['voxel_xyz_to_world_mm'][0][3] += 1
    elif damage == 'label':
        data['lesion_instance'][data['lesion_instance'] > 0] = 999
    elif damage == 'count':
        lesion['registry'][0]['sampled_voxels'] += 1
    else:
        lesion['registry'][0]['edge_id'] = 'wrong-edge'
    data['metadata'] = np.array(json.dumps(metadata))
    data['lesion_metadata'] = np.array(json.dumps(lesion))
    np.savez_compressed(folder/'mask.npz', **data)
    original = json.loads((folder/'artifacts.json').read_text())
    (folder/'artifacts.json').unlink()
    digest = write_manifest(folder, case_revision=original['case_revision'],
                            generation=original['generation'], coverage=original['surface_coverage'],
                            quality=original['quality'])
    assert verify_manifest(folder, expected_sha256=digest)['status'] == 'PASS'
    with pytest.raises(ValueError, match='Mask'):
        verify_masks(folder, expected_sha256=digest)


def two_vessel_fixture(crosses=False):
    case,operation=fixture()
    points=[[10,-10,0],[10,10,0]] if crosses else [[0,10,0],[20,10,0]]
    edge=deepcopy(case['edges'][0])
    edge.update(id='untouched',start='c',end='d',centerline_mm=points)
    edge['anatomy']['branch_id']='untouched'
    case['edges'].append(edge)
    for node,point in zip(['c','d'],points):
        case['nodes'][node]=dict(case['nodes']['a'],position_mm=point)
    return case,operation


def test_default_batch_includes_unmodified_vessels(tmp_path):
    import numpy as np
    case,operation=two_vessel_fixture()
    mask_config={'grid_config':{'shape_zyx':[7,17,27],'spacing_xyz_mm':[1,1,1],
                               'origin_xyz_mm':[-3,-3,-3],'frame_id':'fixture'}}
    result=generate_stenosis_batch(case,[[operation]],tmp_path/'full',target_count=1,
                                  max_attempts=1,seed=3,spacing_mm=.3,mask_config=mask_config)
    assert result['status']=='PASS'
    assert result['surface_coverage']['mode']=='complete_case'
    assert result['surface_coverage']['omitted_edge_ids']==[]
    with np.load(tmp_path/'full/case-00000/surface.npz') as output:
        meta=json.loads(str(output['metadata']))
        assert meta['edge_ids']==['e','untouched']
        assert meta['graph_component_count']==2
        assert output['vertices_mm'][:,1].max()>11
    with np.load(tmp_path/'full/case-00000/mask.npz') as mask:
        assert mask['foreground'][3,13,13]
        assert mask['lesion_instance'][3,13,13]==0
        assert mask['lesion_instance'][3,3,13]>0
    saved,_=load_case(tmp_path/'full/case-00000/case.snapshot.json')
    assert saved['edges'][1]==case['edges'][1]
    from vv_toolbox.case_artifacts import verify_manifest, main as verify_cli
    verification=verify_manifest(tmp_path/'full/case-00000',
        expected_sha256=result['attempts'][0]['artifact_manifest_sha256'])
    assert verification['status']=='PASS'
    assert verification['quality']['surface']['self_intersection']=='NOT RUN'
    assert verification['quality']['masks']['lesion_sampling']=='PASS'
    assert verify_cli([str(tmp_path/'full/case-00000'),'--expected-sha256',
                       result['attempts'][0]['artifact_manifest_sha256']])==0


@pytest.mark.parametrize('damage',['changed','missing','extra','manifest'])
def test_bundle_integrity_detects_damage(tmp_path,damage):
    from vv_toolbox.case_artifacts import verify_manifest, main as verify_cli
    case,operation=fixture()
    report=generate_stenosis_batch(case,[[operation]],tmp_path/'bundle',target_count=1,
                                   max_attempts=1,seed=3,spacing_mm=.3)
    folder=tmp_path/'bundle/case-00000'
    expected=report['attempts'][0]['artifact_manifest_sha256']
    assert verify_manifest(folder,expected_sha256=expected)['status']=='PASS'
    if damage=='changed':
        with (folder/'surface.npz').open('ab') as stream:stream.write(b'changed')
    elif damage=='missing':
        (folder/'surface.npz').unlink()
    elif damage=='extra':
        (folder/'unexpected.json').write_text('{}')
    else:
        (folder/'artifacts.json').write_text('{}')
    with pytest.raises(ValueError):
        verify_manifest(folder,expected_sha256=expected)
    with pytest.raises(SystemExit) as failure:
        verify_cli([str(folder),'--expected-sha256',expected])
    assert failure.value.code==2


def test_unmodified_crossing_prevents_default_publication(tmp_path):
    case,operation=two_vessel_fixture(True)
    result=generate_stenosis_batch(case,[[operation]],tmp_path/'crossing',target_count=1,
                                  max_attempts=1,seed=3,spacing_mm=.3)
    assert result['status']=='FAIL' and 'clearance' in result['attempts'][0]['reason']
    assert sorted(p.name for p in (tmp_path/'crossing').iterdir())==['report.json']


def test_materialized_left_right_labels_are_exported_with_registry(tmp_path):
    import numpy as np
    case,operation=two_vessel_fixture()
    for index,edge in enumerate(case['edges']):
        edge['anatomy']['side']='L' if index==0 else 'R'
        edge['segment_assignment']=dict(original_edge_id=edge['id'],
            interval_address=[0,1],tolerance_mm=.01,
            boundary_ids=['fixture-boundary'],extent_review_refs=['synthetic fixture only'])
    config={'grid_config':{'shape_zyx':[7,17,27],'spacing_xyz_mm':[1,1,1],
                          'origin_xyz_mm':[-3,-3,-3],'frame_id':'fixture'}}
    result=generate_stenosis_batch(case,[[operation]],tmp_path/'labels',target_count=1,
                                  max_attempts=1,seed=3,spacing_mm=.3,mask_config=config)
    assert result['status']=='PASS'
    with np.load(tmp_path/'labels/case-00000/mask.npz') as output:
        assert output['anatomical'][3,3,13]==2  # Left ACA A2
        assert output['anatomical'][3,13,13]==8  # Right ACA A2
        registry=json.loads(str(output['metadata']))['anatomical_registry']
        assert registry['schema']=='vv-toolbox.segment-label-registry/2'
        assert len(registry['labels'])==26 and len(registry['sha256'])==64


def test_explicit_baseline_batch_exports_zero_lesion_mask_and_preserves_input(tmp_path):
    import numpy as np
    from vv_toolbox.case_io import load_case
    case,_=two_vessel_fixture()
    before=deepcopy(case)
    config={'grid_config':{'shape_zyx':[7,17,27],'spacing_xyz_mm':[1,1,1],
                          'origin_xyz_mm':[-3,-3,-3],'frame_id':'fixture'}}
    result=generate_stenosis_batch(case,[[]],tmp_path/'baseline',target_count=1,
        max_attempts=1,seed=3,spacing_mm=.3,mask_config=config)
    assert result['status']=='PASS' and case==before
    generated,_=load_case(tmp_path/'baseline/case-00000/case.snapshot.json')
    assert generated['model_kind']=='synthetic'
    assert generated['edges']==case['edges']
    assert generated['generation']['generator_version']=='baseline-reconstruction/1'
    with np.load(tmp_path/'baseline/case-00000/mask.npz') as output:
        assert output['foreground'].any()
        assert not output['lesion_instance'].any()
        meta=json.loads(str(output['lesion_metadata']))
        assert meta['registry']==[] and meta['sampling_status']=='NOT APPLICABLE'


def test_baseline_candidate_preserves_existing_lesions(tmp_path):
    from vv_toolbox.lesions import concentric_stenosis
    from vv_toolbox.case_io import load_case
    case,operation=fixture()
    base=concentric_stenosis(case,case_id='existing',seed=0,**operation)
    report=generate_stenosis_batch(base,[[]],tmp_path/'existing',target_count=1,
        max_attempts=1,seed=3,spacing_mm=.3)
    assert report['status']=='PASS'
    generated,_=load_case(tmp_path/'existing/case-00000/case.snapshot.json')
    assert generated['lesions']==base['lesions']
    assert report['attempts'][0]['measured_lesions']==base['lesions']
    assert report['parameter_distribution']['accepted']['baseline_candidate_count']==1


def test_partial_output_requires_explicit_selection_and_records_omissions(tmp_path):
    case,operation=two_vessel_fixture(True)
    result=generate_stenosis_batch(case,[[operation]],tmp_path/'partial',target_count=1,
                                  max_attempts=1,seed=3,spacing_mm=.3,surface_edge_ids=['e'])
    assert result['status']=='PASS'
    assert result['surface_coverage']['mode']=='explicit_subset'
    assert result['surface_coverage']['omitted_edge_ids']==['untouched']
    excluded=generate_stenosis_batch(case,[[operation]],tmp_path/'excluded',target_count=1,
                                  max_attempts=1,seed=3,spacing_mm=.3,surface_edge_ids=['untouched'])
    assert excluded['status']=='FAIL' and 'lesion edge' in excluded['attempts'][0]['reason']


def test_failures_isolated_and_target_counts_successes(tmp_path):
    case, operation = fixture()
    candidates = [[dict(operation,severity_percent=100)],[operation],[operation]]
    result = generate_stenosis_batch(case,candidates,tmp_path/'run',target_count=1,max_attempts=3,seed=7,spacing_mm=.3)
    assert [a['status'] for a in result['attempts']] == ['FAIL','PASS']
    assert result['accepted_count'] == 1
    assert result['stop_reason'] == 'target_reached'
    distributions = result['parameter_distribution']
    assert [distributions[key]['candidate_count'] for key in
            ('candidate_pool','attempted','accepted','rejected','unattempted')] == [3,2,1,1,1]
    assert distributions['accepted']['groups'][0]['parameters']['severity_percent']['empirical_values'] == [{'value':40,'count':1}]
    assert distributions['rejected']['groups'][0]['parameters']['severity_percent']['empirical_values'] == [{'value':100,'count':1}]
    assert json.loads((tmp_path/'run/report.json').read_text())['parameter_distribution'] == distributions
    assert sorted(p.name for p in (tmp_path/'run').iterdir()) == ['case-00000','report.json']
    saved,_ = load_case(tmp_path/'run/case-00000/case.snapshot.json')
    assert saved['generation']['seed'] == result['attempts'][1]['seed']
    assert saved['base_model_id'] == case['base_model_id']
    repeat = generate_stenosis_batch(case,candidates,tmp_path/'repeat',target_count=1,max_attempts=3,seed=7,spacing_mm=.3)
    assert repeat == result


def test_attempt_limit_and_no_overwrite(tmp_path):
    case, operation = fixture()
    result = generate_stenosis_batch(case,[[dict(operation,length_mm=50)],[operation]],tmp_path/'run',
        target_count=1,max_attempts=1,seed=0,spacing_mm=.3)
    assert result['status'] == 'FAIL'
    assert result['remaining_count'] == 1
    assert result['stop_reason'] == 'max_attempts_reached'
    before = (tmp_path/'run/report.json').read_bytes()
    with pytest.raises(FileExistsError):
        generate_stenosis_batch(case,[[operation]],tmp_path/'run',target_count=1,max_attempts=1,seed=0,spacing_mm=.3)
    assert (tmp_path/'run/report.json').read_bytes() == before


def test_cli_reports_insufficient_cases(tmp_path):
    from vv_toolbox.case_cli import main
    from vv_toolbox.case_io import save_case
    case, operation = fixture()
    source, candidates = tmp_path/'source.json',tmp_path/'candidates.json'
    save_case(source,case)
    candidates.write_text(json.dumps([[dict(operation,severity_percent=100)]]))
    assert main(['batch',str(source),str(candidates),str(tmp_path/'out'),'--target-count','1',
        '--max-attempts','2','--seed','3','--spacing-mm','.3']) == 1
    report = json.loads((tmp_path/'out/report.json').read_text())
    assert report['stop_reason'] == 'candidates_exhausted'


def test_mask_and_lesion_archive_required_before_acceptance(tmp_path):
    import numpy as np
    case,operation=fixture()
    config={'grid_config':{'shape_zyx':[7,7,27],'spacing_xyz_mm':[1.,1.,1.],
                           'origin_xyz_mm':[-3.,-3.,-3.],'frame_id':'fixture'},
            'lesion_rois':[{'grid_config':{'shape_zyx':[13,13,29],'spacing_xyz_mm':[.5,.5,.5],
                            'origin_xyz_mm':[3.,-3.,-3.],'frame_id':'fixture'},'required_lesion_ids':['l']}]}
    report=generate_stenosis_batch(case,[[operation]],tmp_path/'complete',target_count=1,
        max_attempts=1,seed=0,spacing_mm=.3,mask_config=config)
    assert report['status']=='PASS'
    assert report['attempts'][0]['mask_output']=='PASS'
    folder=tmp_path/'complete/case-00000'
    from vv_toolbox.case_artifacts import verify_masks
    loaded = verify_masks(folder, expected_sha256=report['attempts'][0]['artifact_manifest_sha256'])
    assert loaded['status'] == 'PASS'
    assert {entry['file'] for entry in loaded['masks']} == {'mask.npz', 'lesion-roi-000.npz'}
    with np.load(folder/'mask.npz',allow_pickle=False) as data:
        assert data['lesion_instance'].any()
        assert not data['anatomical'].any()
        assert not np.any((data['lesion_instance']>0)&~data['foreground'])
    with np.load(folder/'lesion-roi-000.npz',allow_pickle=False) as data:
        assert data['lesion_instance'].any()
        assert data['foreground'].shape==(13,13,29)
    roi_quality=json.loads((folder/'lesion-roi-000-quality.json').read_text())
    transform=np.array(roi_quality['roi_voxel_xyz_to_whole_voxel_xyz'])
    assert np.allclose(transform@np.array([0,0,0,1]),[6,0,0,1])
    assert np.allclose(np.diag(transform),[.5,.5,.5,1])
    config['grid_config']['shape_zyx']=[2,2,2]
    failed=generate_stenosis_batch(case,[[operation]],tmp_path/'failed',target_count=1,
        max_attempts=1,seed=0,spacing_mm=.3,mask_config=config)
    assert failed['status']=='FAIL'
    assert not list((tmp_path/'failed').glob('case-*'))


def test_incomplete_lesion_roi_prevents_publication(tmp_path):
    case,operation=fixture()
    config={'grid_config':{'shape_zyx':[7,7,27],'spacing_xyz_mm':[1.,1.,1.],
                           'origin_xyz_mm':[-3.,-3.,-3.],'frame_id':'fixture'},
            'lesion_rois':[{'grid_config':{'shape_zyx':[3,3,3],'spacing_xyz_mm':[.5,.5,.5],
                            'origin_xyz_mm':[9.,0.,0.],'frame_id':'fixture'},'required_lesion_ids':['l']}]}
    result=generate_stenosis_batch(case,[[operation]],tmp_path/'run',target_count=1,
        max_attempts=1,seed=0,spacing_mm=.3,mask_config=config)
    assert result['status']=='FAIL'
    assert 'cover target lesion support' in result['attempts'][0]['reason']
    assert sorted(p.name for p in (tmp_path/'run').iterdir())==['report.json']
