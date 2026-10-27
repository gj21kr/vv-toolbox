import copy

from vv_toolbox.atlas_topology import build_reference_topology, reference_junctions


def part(id, name, layer='arterial'):
    return dict(id=id, name=name, layer=layer)


def test_orbitofrontal_reference_is_side_specific_and_not_geometry_approval():
    parts=[part('a','right anterior cerebral artery'),part('b','right medial frontobasal artery'),
           part('c','left medial frontobasal artery')]
    links=[dict(id='same',part_a='a',part_b='b'),dict(id='opposite',part_a='a',part_b='c')]
    before=copy.deepcopy((parts,links))
    result=build_reference_topology(parts,links)
    relation=next(j for j in result['junctions'] if j['id']=='right_aca_orbitofrontal')
    assert relation['source_url']=='https://pubmed.ncbi.nlm.nih.gov/12924591/'
    assert relation['position'] is None and relation['specimen_status']=='unverified'
    assert result['candidate_assessments'][0]['status']=='reference_junction_candidate'
    assert result['candidate_assessments'][1]['status']=='unreviewed_proximity'
    assert not result['geometry_validated'] and (parts,links)==before


def test_ica_siblings_share_junction_not_parent_child_and_no_geometry_is_inferred():
    parts=[part('ica','right internal carotid artery'),part('aca','right anterior cerebral artery'),
           part('m1','sphenoid part of right middle cerebral artery')]
    links=[dict(id='near',part_a='aca',part_b='m1')]
    before=copy.deepcopy((parts,links))
    result=build_reference_topology(parts,links)
    j=next(j for j in result['junctions'] if j['id']=='right_ica_terminal')
    assert [(m['role'],m['part_ids']) for m in j['members']]==[('parent',['ica']),('daughter',['aca']),('daughter',['m1'])]
    assert j['position'] is None and j['specimen_status']=='unverified'
    assert result['candidate_assessments'][0]['status']=='reference_junction_candidate'
    assert (parts,links)==before


def test_names_cannot_resolve_ambiguous_parts_or_wrong_layers():
    parts=[part('m1','sphenoid part of right middle cerebral artery'),
           part('m2a','insular part of right middle cerebral artery'),
           part('m2b','insular part of right middle cerebral artery'),
           part('wrong','right internal carotid artery','systemic_venous')]
    js={j['id']:j for j in reference_junctions(parts)}
    assert js['right_mca_transition']['members'][1]['mapping_status']=='ambiguous'
    assert js['right_ica_terminal']['members'][0]['part_ids']==[]


def test_missing_profunda_is_not_fabricated_and_unknown_pairs_stay_unknown():
    parts=[part('f','right femoral artery'),part('x','unknown artery')]
    result=build_reference_topology(parts,[dict(id='x',part_a='f',part_b='x')])
    missing=result['junctions'][0]['members'][1]
    assert missing['mapping_status']=='missing' and missing['part_ids']==[]
    assert result['candidate_assessments'][0]['status']=='unreviewed_proximity'


def test_pcom_ophthalmic_requires_review_but_is_preserved():
    parts=[part('p','right posterior communicating artery'),part('o','right ophthalmic artery')]
    result=build_reference_topology(parts,[dict(id='x',part_a='o',part_b='p')])
    assert result['candidate_assessments'][0]['status']=='review_required'


def test_confluence_includes_missing_spatial_link_without_claiming_validation():
    parts=[part('s','splenic vein','hepatic_portal'),part('m','superior mesenteric vein','hepatic_portal'),
           part('p','pre-hepatic portal vein','hepatic_portal'),part('p2','hepatic portal vein','hepatic_portal')]
    result=build_reference_topology(parts,[])
    j=result['junctions'][0]
    assert j['kind']=='confluence'
    assert [m['role'] for m in j['members']]==['tributary','tributary','outflow']
    assert j['members'][2]['part_ids']==['p']
    assert not result['geometry_validated']


def test_arch_origins_are_separate_not_a_fabricated_common_origin():
    parts=[part('a','arch of aorta'),part('b','brachiocephalic artery'),
           part('c','left common carotid artery'),part('s','left subclavian artery')]
    js=reference_junctions(parts)
    assert len(js)==3 and all(len(j['members'])==2 for j in js)


def test_concept_members_do_not_become_direct_trunks():
    from vv_toolbox.atlas_topology import resolve_member
    p=part('component','a different displayed name')
    p['concept_memberships']=[dict(tree='partof',concept_id='FMA20796')]
    m=resolve_member([p],'arterial','branch',('right deep femoral artery',))
    assert m['mapping_status']=='concept_members_found'
    assert m['part_ids']==[] and m['related_part_ids']==['component']
    assert not m['geometry_validated']


def test_multiple_meshes_same_concept_are_grouped_without_name_dependence():
    from vv_toolbox.atlas_topology import resolve_member
    parts=[part('a','one'),part('b','two'),part('c','unrelated')]
    for p in parts[:2]:p['concept_memberships']=[dict(tree='isa',concept_id='FMA50542')]
    # PART-OF contains branches too, which must not be mistaken for trunk elements.
    parts[2]['concept_memberships']=[dict(tree='partof',concept_id='FMA50542')]
    m=resolve_member(parts,'arterial','parent',('basilar artery',))
    assert m['mapping_status']=='multiple_elements_same_concept'
    assert m['part_ids']==['a','b']


def test_bilateral_superior_members_do_not_claim_side_or_direct_incidence():
    from vv_toolbox.atlas_topology import resolve_member
    p=part('c','artery of central sulcus')
    p['concept_memberships']=[dict(tree='isa',concept_id='FMA50436')]
    m=resolve_member([p],'arterial','daughter',('trunk of superior terminal branch of right middle cerebral artery',))
    assert m['part_ids']==[] and m['related_part_ids']==['c']
    assert 'bilateral' in m['unresolved_reason']
