from copy import deepcopy

import pytest

from vv_toolbox.case_io import case_digest
from vv_toolbox.synthetic_routes import build_synthetic_routes, inspect_four_access_routes
from test_access_routes import make_case


def fixture():
    case = make_case()
    # Two disconnected collinear source fragments with unresolved anatomy.
    case['nodes'] = {str(i): {'kind': 'unresolved', 'evidence_status': 'unresolved',
                              'position_mm': [i*10, 0, 0]} for i in range(4)}
    template = case['edges'][0]
    case['edges'] = []
    for name, start, end in [('a', '0', '1'), ('b', '2', '3')]:
        edge = deepcopy(template)
        edge.update(id=name, start=start, end=end, evidence_status='unresolved',
                    centerline_mm=[case['nodes'][start]['position_mm'], case['nodes'][end]['position_mm']],
                    radii_mm=[1, 2] if name == 'a' else [3, 4])
        case['edges'].append(edge)
    spec = {'schema': 'vv-toolbox.synthetic-routes/1', 'source_case_sha256': case_digest(case),
            'bridges': [{'id': 'bridge', 'from': {'edge_id': 'a', 'endpoint': 'end'},
                         'to': {'edge_id': 'b', 'endpoint': 'start'},
                         'handle_lengths_mm': [10, 10], 'samples': 11,
                         'rationale': 'explicit synthetic fixture gap', 'evidence_refs': ['fixture']}]}
    return case, spec


def test_bridge_preserves_source_and_endpoint_radius_tangent():
    case, spec = fixture()
    before = deepcopy((case, spec))
    result = build_synthetic_routes(case, spec, case_id='derived')
    assert (case, spec) == before
    assert result['nodes'] == case['nodes']
    assert result['edges'][:2] == case['edges']
    bridge = result['edges'][2]
    for i, point in enumerate(bridge['centerline_mm']):
        assert point == pytest.approx([10+i, 0, 0], abs=1e-12)
    assert bridge['radii_mm'][0] == 2 and bridge['radii_mm'][-1] == 3
    assert bridge['evidence_status'] == 'synthetic_estimate'
    assert all(n['evidence_status'] == 'unresolved' for n in result['nodes'].values())
    assert build_synthetic_routes(case, spec, case_id='derived') == result


@pytest.mark.parametrize('endpoint', ['from', 'to'])
def test_continuation_rejects_backward_endpoint_without_mutation(endpoint):
    case, spec = fixture()
    spec['bridges'][0][endpoint]['endpoint'] = 'start' if endpoint == 'from' else 'end'
    before = deepcopy((case, spec))
    with pytest.raises(ValueError, match='reverses'):
        build_synthetic_routes(case, spec, case_id='backward')
    assert (case, spec) == before


def test_continuation_rejects_interior_reversal_even_with_sparse_samples():
    case, spec = fixture()
    # End derivatives face forward, but long handles fold back between samples.
    spec['bridges'][0].update(handle_lengths_mm=[50, 50], samples=3)
    with pytest.raises(ValueError, match='reverses'):
        build_synthetic_routes(case, spec, case_id='folded')


def test_continuation_allows_stationary_projection_without_reversal():
    case, spec = fixture()
    spec['bridges'][0].update(handle_lengths_mm=[30, 30], samples=4)
    assert build_synthetic_routes(case, spec, case_id='stationary')['edges'][-1]['id'] == 'bridge'


@pytest.mark.parametrize('mutation', ['hash', 'anchor', 'endpoint', 'samples', 'handles', 'evidence', 'duplicate'])
def test_bad_spec_cannot_mutate_source(mutation):
    case, spec = fixture()
    before = deepcopy(case)
    b = spec['bridges'][0]
    if mutation == 'hash': spec['source_case_sha256'] = 'b'*64
    if mutation == 'anchor': b['from']['edge_id'] = 'absent'
    if mutation == 'endpoint': b['from']['endpoint'] = 'nearest'
    if mutation == 'samples': b['samples'] = True
    if mutation == 'handles': b['handle_lengths_mm'] = [float('nan'), 10]
    if mutation == 'evidence': b['evidence_refs'] = []
    if mutation == 'duplicate': spec['bridges'].append(deepcopy(b))
    with pytest.raises(ValueError): build_synthetic_routes(case, spec, case_id='derived')
    assert case == before


def routes_fixture():
    case = make_case()
    for edge in case['edges']:
        edge['anatomy']['side'] = 'L' if edge['id'].startswith('l') else 'R'
    routes = [{'femoral_side': f.upper(), 'carotid_side': c.upper(),
               'femoral_edge': f+'f', 'carotid_edge': c+'c',
               'start': f+'f', 'end': 'target', 'required_edges': [f+'f', c+'c', c+'t']}
              for f in ['l', 'r'] for c in ['l', 'r']]
    return case, routes


def test_four_paths_never_claim_anatomical_acceptance():
    case, routes = routes_fixture()
    report = inspect_four_access_routes(case, routes)
    assert all(r['result']['status'] == 'PASS' for r in report['routes'])
    assert report['anatomical_acceptance'] == 'UNKNOWN'
    case['nodes']['a']['evidence_status'] = 'unresolved'
    assert all(r['result']['status'] == 'UNKNOWN' for r in inspect_four_access_routes(case, routes)['routes'])


def test_four_paths_reject_duplicate_combinations_and_wrong_side():
    case, routes = routes_fixture()
    with pytest.raises(ValueError): inspect_four_access_routes(case, [routes[0]]*4)
    routes[0]['carotid_edge'] = 'rc'
    with pytest.raises(ValueError): inspect_four_access_routes(case, routes)


def test_nonobject_declarations_and_degenerate_source_are_rejected():
    case, spec = fixture()
    with pytest.raises(ValueError): build_synthetic_routes(case, [], case_id='derived')
    broken = deepcopy(spec)
    broken['bridges'] = [None]
    with pytest.raises(ValueError): build_synthetic_routes(case, broken, case_id='derived')
    route_case, routes = routes_fixture()
    with pytest.raises(ValueError): inspect_four_access_routes(route_case, [None]*4)
    case['edges'][0]['centerline_mm'].append(case['edges'][0]['centerline_mm'][-1])
    case['edges'][0]['radii_mm'].append(2)
    with pytest.raises(ValueError, match='duplicate consecutive'):
        build_synthetic_routes(case, spec, case_id='derived')
