from copy import deepcopy

import pytest

from test_access_routes import make_case
from vv_toolbox.case_io import case_digest
from vv_toolbox.junction_regions import inspect_junction_regions


def fixture():
    c = make_case()
    c['model_kind'] = 'synthetic'
    c['generation'] = {'seed': 0, 'generator_version': 'fixture', 'config': {}}
    points = {'o': [0, 0, 0], 'b': [0, 1, 0], 'l': [-10, 0, 0], 'r': [10, 0, 0], 'u': [0, 11, 0]}
    c['nodes'] = {k: {'kind': 'unresolved', 'evidence_status': 'unresolved', 'position_mm': v} for k, v in points.items()}
    template = deepcopy(c['edges'][0]); c['edges'] = []
    for ident, a, b in [('left', 'o', 'l'), ('right', 'o', 'r'), ('bridge', 'o', 'b'), ('up', 'b', 'u')]:
        e = deepcopy(template)
        e.update(id=ident, start=a, end=b, centerline_mm=[points[a], points[b]], radii_mm=[.1, .1], evidence_status='unresolved')
        c['edges'].append(e)
    c['edges'][2]['derivation'] = {'attachment_mode': 'side_branch'}
    c['synthetic_route_inspection'] = {'bridge_ids': ['bridge']}
    r = {'id': 'junction', 'case_sha256': case_digest(c), 'root_node_id': 'o',
         'rationale': 'bounded numerical fixture', 'evidence_refs': ['fixture'],
         'portions': [{'edge_id': e, 'endpoint': 'start', 'length_mm': 1 if e == 'bridge' else 2} for e in ['left', 'right', 'bridge', 'up']]}
    return c, [r]


def run(c, regions, **kwargs):
    for r in regions:
        r['case_sha256'] = case_digest(c)
    return inspect_junction_regions(c, [e['id'] for e in c['edges']], regions, **kwargs)


def test_internal_bridge_bounded_exemption_and_preservation():
    c, regions = fixture(); original = deepcopy((c, regions))
    result = run(c, regions)
    assert result['status'] == 'PASS' and result['exempt_segment_pairs'] > 0
    assert (c, regions) == original
    assert result['inside_regions'] == 'NOT CHECKED'


def test_full_split_connector_requires_reciprocal_lineage():
    from test_synthetic_bridge_split import parent_and_spec
    from vv_toolbox.synthetic_junctions import split_synthetic_bridge
    parent, spec = parent_and_spec()
    case = split_synthetic_bridge(parent, spec, case_id='split')
    edge = deepcopy(case['edges'][0])
    edge.update(id='daughter', start='junction', end='tip',
                centerline_mm=[[14.5, 0, 0], [14.5, 20, 0]], radii_mm=[.1, .1])
    case['edges'].append(edge)
    case['nodes']['tip'] = dict(kind='unresolved', evidence_status='unresolved', position_mm=[14.5, 20, 0])
    region = dict(id='compound', case_sha256=case_digest(case), root_node_id='junction',
                  rationale='fixture short split connector', evidence_refs=['fixture'], portions=[
        dict(edge_id='a', endpoint='end', length_mm=5.),
        dict(edge_id='b0', endpoint='start', length_mm=4.5),
        dict(edge_id='b1', endpoint='start', length_mm=2.),
        dict(edge_id='daughter', endpoint='start', length_mm=2.)])
    result = inspect_junction_regions(case, [e['id'] for e in case['edges']], [region])
    assert result['exempt_segment_pairs'] > 0
    next(e for e in case['edges'] if e['id'] == 'b1')['bridge_split']['sibling_edge_id'] = 'wrong'
    region['case_sha256'] = case_digest(case)
    with pytest.raises(ValueError, match='reciprocal split connector'):
        inspect_junction_regions(case, [e['id'] for e in case['edges']], [region])


def test_coarse_interval_clipped_at_boundary_and_remote_recross_detected():
    c, regions = fixture()
    e = c['edges'][3]
    e['centerline_mm'] = [[0, 1, 0], [6, 0, 0], [0, 11, 0]]; e['radii_mm'] = [.1]*3
    result = run(c, regions)
    assert result['status'] == 'UNKNOWN'
    witness = next(x for x in result['potential_contacts'] if x['edges'] == ['right', 'up'])
    assert witness['arc_intervals_mm'][0][0] == 2


def test_inside_outside_contact_not_exempt():
    c, regions = fixture()
    c['edges'][0]['radii_mm'] = [3, 3]
    result = run(c, regions)
    assert result['status'] == 'UNKNOWN'
    assert any(x['arc_intervals_mm'][0] == [0., 2.] and x['arc_intervals_mm'][1][0] == 2
               for x in result['potential_contacts'])


def test_unrelated_selected_edge_still_checked():
    c, regions = fixture()
    e = deepcopy(c['edges'][0]); e.update(id='other', start='x', end='y', centerline_mm=[[5,-1,0],[5,1,0]])
    for n, p in zip(['x','y'], e['centerline_mm']):
        c['nodes'][n] = {'kind':'unresolved','evidence_status':'unresolved','position_mm':p}
    c['edges'].append(e)
    assert any('other' in x['edges'] for x in run(c, regions)['potential_contacts'])


def test_degree_two_region_allowed_without_full_bridge():
    c, regions = fixture()
    c['edges'] = c['edges'][:2]
    c['nodes'] = {k: v for k, v in c['nodes'].items() if k in ('o', 'l', 'r')}
    regions[0]['portions'] = regions[0]['portions'][:2]
    assert run(c, regions)['status'] == 'PASS'


def test_budget_exhaustion_unknown():
    c, regions = fixture()
    assert run(c, regions, max_segment_pairs=1)['reason'] == 'pair_budget_exhausted'


def test_returned_provenance_is_detached():
    c, regions = fixture()
    result = run(c, regions)
    regions[0]['rationale'] = 'later mutation'
    assert result['regions'][0]['rationale'] == 'bounded numerical fixture'


@pytest.mark.parametrize('extent', [8, 9])
def test_regions_cannot_touch_or_overlap_on_edge(extent):
    c, regions = fixture()
    other = deepcopy(regions[0]); other['id'] = 'other'
    other['portions'][0].update(endpoint='end', length_mm=extent)
    with pytest.raises(ValueError, match='overlap or touch'):
        run(c, regions+[other])


def test_end_prefix_reversal_equivalent():
    c, regions = fixture()
    e = c['edges'][0]
    e['start'], e['end'] = e['end'], e['start']
    e['centerline_mm'].reverse(); e['radii_mm'].reverse()
    regions[0]['portions'][0]['endpoint'] = 'end'
    assert run(c, regions)['status'] == 'PASS'


def test_different_regions_do_not_exempt_cross_contacts():
    c, regions = fixture()
    # Keep the arch arms in one region, and bridge/upper arm in another.
    first = deepcopy(regions[0]); first['portions'] = first['portions'][:2]
    second = deepcopy(regions[0]); second['id'] = 'separate'; second['root_node_id'] = 'b'
    second['portions'] = [{'edge_id': 'bridge', 'endpoint': 'end', 'length_mm': .9},
                          {'edge_id': 'up', 'endpoint': 'start', 'length_mm': 2}]
    result = run(c, [first, second])
    assert result['status'] == 'UNKNOWN'
    assert any('bridge' in x['edges'] and 'left' in x['edges'] for x in result['potential_contacts'])


@pytest.mark.parametrize('bad', ['hash', 'region', 'portion', 'disconnected', 'extent', 'whole_arm', 'refs', 'duplicate', 'bridge_role', 'source', 'nan'])
def test_invalid_declarations(bad):
    c, regions = fixture(); r = regions[0]
    if bad == 'hash': r['case_sha256'] = '0'*64
    if bad == 'region': regions[0] = None
    if bad == 'portion': r['portions'][0] = None
    if bad == 'disconnected': r['portions'].pop(2)
    if bad == 'extent': r['portions'][0]['length_mm'] = 11
    if bad == 'whole_arm': r['portions'][0]['length_mm'] = 10
    if bad == 'refs': r['evidence_refs'] = []
    if bad == 'duplicate': r['portions'].append(deepcopy(r['portions'][0]))
    if bad == 'bridge_role': c['edges'][2]['derivation']['attachment_mode'] = 'continuation'
    if bad == 'source': c['model_kind'] = 'source'; c['generation'] = None
    if bad == 'nan': r['portions'][0]['length_mm'] = float('nan')
    if bad in ('bridge_role', 'source'): r['case_sha256'] = case_digest(c)
    with pytest.raises(ValueError):
        inspect_junction_regions(c, [e['id'] for e in c['edges']], regions)
