"""Literature reference junctions, NOT recovered or validated atlas connectivity.

Name matching establishes candidate part identity only. No coordinates, flow,
geometry repairs, or specimen-specific variant claims are inferred here.
"""

SOURCES = {
    'anterior': 'https://pubmed.ncbi.nlm.nih.gov/34437363/',
    'mca': 'https://pubmed.ncbi.nlm.nih.gov/7452329/',
    'mca_divisions': 'https://pmc.ncbi.nlm.nih.gov/articles/PMC11588606/',
    'pca': 'https://pubmed.ncbi.nlm.nih.gov/21492726/',
    'acom': 'https://pubmed.ncbi.nlm.nih.gov/6111033/',
    'aca_orbitofrontal': 'https://pubmed.ncbi.nlm.nih.gov/12924591/',
    'arch': 'https://pmc.ncbi.nlm.nih.gov/articles/PMC2588331/',
    'celiac': 'https://pmc.ncbi.nlm.nih.gov/articles/PMC4725396/',
    'femoral': 'https://pmc.ncbi.nlm.nih.gov/articles/PMC4484058/',
    'portal': 'https://jnhrc.com.np/index.php/jnhrc/article/view/3211',
    'jugular': 'https://elsevier-elibrary.com/contents/fullcontent/58750/epubcontent_v2/OEBPS/B9780443066849500366.htm',
}


# Audited against the pinned BodyParts3D 4.0 tables. IS-A concept members
# are not equivalent to PART-OF territories or recovered proximal trunks.
CONCEPT_RULES = {
    'insular part of right middle cerebral artery': ('isa','FMA50369','direct'),
    'insular part of left middle cerebral artery': ('isa','FMA50370','direct'),
    'basilar artery': ('isa','FMA50542','direct'),
    'splenic artery': ('isa','FMA14773','direct'),
    'pre-hepatic portal vein': ('isa','FMA71904','direct'),
    'right deep femoral artery': ('partof','FMA20796','components'),
    'left deep femoral artery': ('partof','FMA20797','components'),
    'trunk of superior terminal branch of right middle cerebral artery': ('isa','FMA50436','bilateral_components'),
    'trunk of superior terminal branch of left middle cerebral artery': ('isa','FMA50436','bilateral_components'),
}


def resolve_member(parts, layer, role, names):
    member=dict(role=role,expected_names=list(names),part_ids=[],related_part_ids=[],mapping_status='missing',geometry_validated=False)
    rule=CONCEPT_RULES.get(names[0])
    if rule:
        tree,concept,kind=rule
        matched=sorted(p['id'] for p in parts if p.get('layer')==layer and any(
            m['tree']==tree and m['concept_id']==concept for m in p.get('concept_memberships',[])))
        if matched:
            member.update(mapping_basis=dict(tree=tree,concept_id=concept),mapping_status='concept_matched' if len(matched)==1 else 'multiple_elements_same_concept')
            if kind=='direct':member['part_ids']=matched
            else:
                member.update(mapping_status='concept_members_found',related_part_ids=matched,
                    unresolved_reason='Related concept elements found; continuous trunk and junction unresolved.'+
                    (' Source concept is bilateral; side-specific trunk is not identified.' if kind=='bilateral_components' else ' PART-OF membership is not a direct branch connection.'))
            return member
    matches=sorted(p['id'] for p in parts if p.get('layer')==layer and p.get('name','').casefold() in names)
    member.update(part_ids=matches,mapping_status='missing' if not matches else 'ambiguous' if len(matches)>1 else 'name_matched')
    return member


def reference_junctions(parts):
    """Resolve reference slots by exact names and layer; retain all ambiguities."""
    result = []
    def add(key, label, kind, source, layer, slots, note=''):
        members = []
        for role, names in slots:
            members.append(resolve_member(parts,layer,role,names))
        # Do not flood an unrelated atlas with wholly unmapped reference anatomy.
        if not any(m['part_ids'] or m['related_part_ids'] for m in members):
            return
        result.append(dict(id=key, label=label, kind=kind, layer=layer,
                           evidence='literature_reference', specimen_status='unverified',
                           position=None, source_url=SOURCES[source], members=members, note=note))

    for side in ('right', 'left'):
        aca = f'{side} anterior cerebral artery'
        ica = f'{side} internal carotid artery'
        m1 = f'sphenoid part of {side} middle cerebral artery'
        pcom = f'{side} posterior communicating artery'
        p1 = f'precommunicating part of {side} posterior cerebral artery'
        post = f'postcommunicating part of {side} posterior cerebral artery'
        add(f'{side}_ica_terminal', f'{side.title()} ICA terminal bifurcation', 'bifurcation', 'anterior', 'arterial',
            [('parent', (ica,)), ('daughter', (aca,)), ('daughter', (m1,))],
            'ACA part is not segmented into A1/A2; junction location remains unannotated.')
        add(f'{side}_pcom_origin', f'{side.title()} PCom origin', 'branch_origin', 'anterior', 'arterial',
            [('parent', (ica,)), ('branch', (pcom,))])
        add(f'{side}_aca_orbitofrontal', f'{side.title()} ACA / medial frontobasal origin',
            'branch_origin', 'aca_orbitofrontal', 'arterial',
            [('parent', (aca,)), ('branch', (f'{side} medial frontobasal artery',))],
            'Literature describes an orbitofrontal branch of A2. Atlas ACA segment, ostium and lumen connection remain unverified; do not merge a neighboring surface from name or proximity alone.')
        add(f'{side}_pcom_pca', f'{side.title()} PCom / PCA junction', 'communication', 'pca', 'arterial',
            [('proximal_segment', (p1,)), ('communicating_vessel', (pcom,)), ('distal_segment', (post,))],
            'Reference arrangement only; fetal PCA and other variants are not inferred. Distal part is not split into P2/P3.')
        add(f'{side}_mca_transition', f'{side.title()} M1 / M2 transition', 'segment_transition', 'mca', 'arterial',
            [('proximal_segment', (m1,)), ('distal_segment', (f'insular part of {side} middle cerebral artery',))],
            'Topographic transition is not necessarily the first MCA bifurcation. Concept-matched insular elements form a group; individual branch roles remain unannotated.')
        add(f'{side}_mca_divisions', f'{side.title()} MCA divisions (two-trunk reference)', 'bifurcation_reference', 'mca_divisions', 'arterial',
            [('parent', (m1,)), ('daughter', (f'trunk of superior terminal branch of {side} middle cerebral artery',)),
             ('daughter', (f'trunk of inferior terminal branch of {side} middle cerebral artery',))],
            'One common reference pattern, not a claim that this atlas has two trunks. Single-trunk, trifurcation and early branching variants exist. Missing superior-trunk name may reflect source partitioning.')
        add(f'{side}_femoral_profunda', f'{side.title()} profunda femoris origin', 'branch_origin', 'femoral', 'arterial',
            [('parent', (f'{side} femoral artery',)), ('branch', (f'{side} deep femoral artery', f'deep artery of {side} thigh', f'{side} profunda femoris artery'))],
            'Missing name mapping does not prove absence from the original mesh. No substitute vessel is generated.')
        add(f'{side}_venous_angle', f'{side.title()} jugular / subclavian confluence', 'confluence', 'jugular', 'systemic_venous',
            [('tributary', (f'{side} internal jugular vein',)), ('tributary', (f'{side} subclavian vein',)), ('outflow', (f'{side} brachiocephalic vein',))])
    add('acom', 'Anterior communicating connection', 'communication', 'acom', 'arterial',
        [('communicating_vessel', ('anterior communicating artery',)), ('connected_vessel', ('right anterior cerebral artery',)), ('connected_vessel', ('left anterior cerebral artery',))],
        'ACom perforators are not exhaustively represented. This is not a degree-two constraint or a directed flow model.')
    add('basilar_apex', 'Basilar apex', 'bifurcation', 'pca', 'arterial',
        [('parent', ('basilar artery',)), ('daughter', ('precommunicating part of right posterior cerebral artery',)), ('daughter', ('precommunicating part of left posterior cerebral artery',))])
    for key, name in [('brachiocephalic', 'brachiocephalic artery'), ('left_carotid', 'left common carotid artery'), ('left_subclavian', 'left subclavian artery')]:
        add('arch_'+key, 'Aortic arch / '+name, 'branch_origin', 'arch', 'arterial',
            [('parent', ('arch of aorta',)), ('branch', (name,))],
            'Separate reference origins; not a single three-branch junction. Common-origin variants require annotation.')
    # The three named celiac branches need not share one exact trifurcation point.
    for key, name in [('gastric', 'left gastric artery'), ('hepatic', 'common hepatic artery'), ('splenic', 'splenic artery')]:
        add('celiac_'+key, 'Celiac trunk / '+name, 'branch_origin', 'celiac', 'arterial',
            [('parent', ('celiac trunk',)), ('branch', (name,))], 'Branch origin position and individual variant are unverified.')
    add('portal_confluence', 'Splenic / superior mesenteric portal confluence', 'confluence', 'portal', 'hepatic_portal',
            [('tributary', ('splenic vein',)), ('tributary', ('superior mesenteric vein',)), ('outflow', ('pre-hepatic portal vein',))],
        'Pre-hepatic portal concept is the reference outlet. Hepatic portal vein is a distinct concept, not an alias. Junction position and IMV drainage variants need annotation.')
    return result


def build_reference_topology(parts, links):
    """Keep spatial candidates intact and attach independent semantic review."""
    junctions = reference_junctions(parts)
    by_id = {p['id']:p for p in parts}
    assessments = []
    for link in links:
        a, b = link['part_a'], link['part_b']
        shared = [j['id'] for j in junctions if
                  any(a in m['part_ids'] for m in j['members']) and
                  any(b in m['part_ids'] for m in j['members']) and
                  not any(a in m['part_ids'] and b in m['part_ids'] for m in j['members'])]
        names = [by_id.get(pid, {}).get('name','').casefold() for pid in (a,b)]
        suspect = any(set(names)=={f'{side} posterior communicating artery', f'{side} ophthalmic artery'} for side in ('left','right'))
        assessments.append(dict(link_id=link['id'], part_a=a, part_b=b,
            status='review_required' if suspect else 'reference_junction_candidate' if shared else 'unreviewed_proximity',
            junction_ids=shared, reason='Not a standard direct PCom–ophthalmic branch; specimen/variant evidence required.' if suspect else
            'May share a reference junction; does not establish direct parent/child connectivity.' if shared else 'No curated relation covers this pair.'))
    return dict(schema='vv-toolbox.reference-topology/1', junctions=junctions, candidate_assessments=assessments,
                clinical_validation=False, geometry_validated=False,
                scope='Selected standard reference relations, not exhaustive or specimen-validated. No geometry or blood-flow inference.')
