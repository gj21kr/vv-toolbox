import numpy as np
import pytest
from vv_toolbox.atlas import parse_obj,groups_from_tables,load_atlas,ROOT


def test_original_positions_preserved_and_face_tokens_decoded():
    v,f=parse_obj(b'v 100 200 300\nv 101 200 300\nv 101 202 300\nv 100 202 300\nf 1/1/1 2/2/1 3/3/1 4/4/1\n')
    np.testing.assert_array_equal(v[0],[100,200,300])
    np.testing.assert_array_equal(f,[[0,1,2],[0,2,3]])


def test_negative_indices_supported_but_zero_rejected():
    obj=b'v 0 0 0\nv 1 0 0\nv 0 1 0\n'
    _,f=parse_obj(obj+b'f -3 -2 -1\n')
    np.testing.assert_array_equal(f,[[0,1,2]])
    with pytest.raises(ValueError):parse_obj(obj+b'f 0 1 2\n')


def test_venous_compartments_disjoint_context_deduplicated():
    def row(concept,element):return {'concept id':concept,'element file id':element,'name':element}
    tables={'isa':[row('FMA66464','A'),row('FMA66644','V'),row('FMA66645','P')],
            'partof':[row('FMA7088','H'),row('FMA7088','A')]}
    groups,_=groups_from_tables(tables)
    assert groups['context']=={'H'}
    tables['isa'].append(row('FMA66644','P'))
    with pytest.raises(ValueError,match='portal'):groups_from_tables(tables)


def test_central_trunks_added_when_systemic_groups_omit_them():
    def row(concept,element,name):return {'concept id':concept,'element file id':element,'name':name}
    tables={'isa':[row('FMA66464','A','systemic artery'),row('FMA66644','V','systemic vein'),row('FMA66645','P','portal'),
                   row('FMA3768','ARCH','arch of aorta'),row('FMA4720','SVC','superior vena cava')],
            'partof':[row('FMA7088','H','heart')]}
    groups,labels=groups_from_tables(tables)
    assert 'ARCH' in groups['arterial'] and 'SVC' in groups['systemic_venous']
    assert labels['ARCH'][1]=='arch of aorta'


def test_vessel_subdivision_classes_are_selected_without_nonvascular_organs():
    def row(concept,element,name):return {'concept id':concept,'element file id':element,'name':name}
    tables={'isa':[row('FMA66464','A','systemic artery'),row('FMA66644','V','systemic vein'),row('FMA66645','P','portal'),
                   row('FMA66332','M1','zone of artery'),row('FMA86256','THORAX','segment of arterial trunk'),
                   row('FMA14329','PORTALTRUNK','trunk of portal vein'),row('FMA22917','HANDVEIN','tributary of venous anastomosis'),
                   row('FMA61820','BRAIN','segment of cerebral hemisphere')],
            'partof':[row('FMA7088','H','heart')]}
    groups,_=groups_from_tables(tables)
    assert {'M1','THORAX'}<=groups['arterial']
    assert 'PORTALTRUNK' in groups['hepatic_portal']
    assert 'HANDVEIN' in groups['systemic_venous']
    assert 'BRAIN' not in set().union(*groups.values())


@pytest.mark.skipif(not (ROOT/'isa_BP3D_4.0_obj_99.zip').exists(),reason='Official atlas is an explicit optional local acquisition')
def test_acquired_atlas_contains_required_thoracic_structures_in_source_frame():
    atlas=load_atlas()
    by_id={p['id']:p for p in atlas.metadata['parts']}
    for element in ['FJ3411','FJ3413','FJ3427','FJ1932']:
        assert by_id[element]['layer']=='arterial'
    for element in ['FJ3645','FJ3441','FJ3659']:
        assert by_id[element]['layer']=='systemic_venous'
    names={p['name'] for p in by_id.values()}
    assert {'left brachiocephalic vein','right brachiocephalic vein'}<=names
    assert atlas.metadata['coverage']['context']>0
    assert len(by_id)==len(atlas.meshes)
    low,high=atlas.focus_bounds['Aortic arch']
    assert low[2]>1000 and high[2]>low[2]  # Native atlas height retained, not recentered.


@pytest.mark.skipif(not (ROOT/'isa_BP3D_4.0_obj_99.zip').exists(),reason='Official atlas is an explicit optional local acquisition')
def test_neck_source_elements_present_and_intrinsic_gap_reported_honestly():
    atlas=load_atlas()
    by_id={p['id']:p for p in atlas.meshes}
    required={'FJ3564','FJ3483','FJ1682','FJ1682M','FJ3585','FJ3485','FJ1725','FJ1725M'}
    assert required<=set(by_id)
    for gap in atlas.metadata['neck_discontinuity']['carotids'].values():
        assert gap['status']=='SOURCE GAP'
        assert gap['vertical_separation_source_units']>60
        assert gap['nearest_vertex_distance_source_units']>gap['vertical_separation_source_units']
    low,high=np.asarray(atlas.focus_bounds['Cerebral'])
    for element in required:
        assert np.all(by_id[element]['vertices'].min(0)>=low)
        assert np.all(by_id[element]['vertices'].max(0)<=high)


@pytest.mark.skipif(not (ROOT/'isa_BP3D_4.0_obj_99.zip').exists(),reason='Official atlas is an explicit optional local acquisition')
def test_acquired_vascular_regions_restore_native_trunk_and_cerebral_coverage():
    from scipy.spatial import cKDTree
    atlas=load_atlas();by_id={p['id']:p for p in atlas.meshes}
    for element in ['FJ1931','FJ1692','FJ1692M','FJ1660','FJ1660M','FJ1694','FJ1694M',
                    'FJ1723','FJ1723M','FJ1714','FJ1714M','FJ1718','FJ1718M','FJ2068','FJ2085','FJ2136','FJ2169']:
        assert by_id[element]['layer']=='arterial'
    for element in ['FJ3102','FJ3122']:
        assert by_id[element]['layer']=='hepatic_portal'
    tree=cKDTree(by_id['FJ1931']['vertices'])
    # Native descending-thoracic piece really abuts adjacent existing source parts.
    for neighbor in ['FJ3427','FJ1932']:
        assert tree.query(by_id[neighbor]['vertices'])[0].min()<1
    assert len(by_id)==len(atlas.meshes)
