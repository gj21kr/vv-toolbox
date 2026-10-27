from copy import deepcopy

import pytest

from vv_toolbox.route_roles import resolve_source_roles
from vv_toolbox.synthetic_junctions import trim_synthetic_terminal, split_synthetic_junction
from vv_toolbox.case_io import case_digest
from test_synthetic_routes import fixture
from test_synthetic_junctions import spec


def test_source_and_multigeneration_trim_role_binding():
    source, _ = fixture()
    assert resolve_source_roles(source, {'first': ['a'], 'second': ['b']}) == {'first': ['a'], 'second': ['b']}
    split = split_synthetic_junction(source, spec(source), case_id='split')
    request = spec(split)
    request.update(schema='vv-toolbox.synthetic-terminal-trim/1', edge_id='a0',
                   remove_endpoint='start', node_id='cut', child_edge_ids=['removed', 'kept'],
                   parent_case_sha256=case_digest(split))
    trimmed = trim_synthetic_terminal(split, request, case_id='trimmed')
    before = deepcopy(trimmed)
    assert resolve_source_roles(trimmed, {'first': ['a'], 'second': ['b']}) == {'first': ['a1', 'kept'], 'second': ['b']}
    assert trimmed == before


def test_roles_never_fallback_to_same_name():
    source, _ = fixture()
    with pytest.raises(ValueError, match='missing active descendant'):
        resolve_source_roles(source, {'first': ['absent']})


def test_cyclic_or_ambiguous_lineage_rejected():
    source, _ = fixture()
    source['edges'][0]['derived_interval'] = {'parent_edge_id': 'b'}
    source['edges'][1]['derived_interval'] = {'parent_edge_id': 'a'}
    with pytest.raises(ValueError, match='cyclic'):
        resolve_source_roles(source, {'role': ['a']})
    source['edges'][1].pop('derived_interval')
    archived = deepcopy(source['edges'][0])
    archived['derived_interval']['parent_edge_id'] = 'other'
    source['synthetic_junctions'] = {'history': [{'parent_edge': archived}]}
    with pytest.raises(ValueError, match='ambiguous'):
        resolve_source_roles(source, {'role': ['a']})
