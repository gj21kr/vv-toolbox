from copy import deepcopy

import pytest

from vv_toolbox.case_io import case_digest
from vv_toolbox.synthetic_routes import build_synthetic_routes,extend_synthetic_routes
from test_synthetic_routes import fixture


def parent_and_extension():
    source, spec = fixture()
    edge = deepcopy(source['edges'][-1])
    edge.update(id='c',start='4',end='5',centerline_mm=[[40,0,0],[50,0,0]],radii_mm=[4,4])
    source['edges'].append(edge)
    for node,point in zip(['4','5'],edge['centerline_mm']):
        source['nodes'][node]=dict(source['nodes']['0'],position_mm=point)
    spec['source_case_sha256']=case_digest(source)
    parent = build_synthetic_routes(source,spec,case_id='first')
    extension = dict(schema='vv-toolbox.synthetic-route-extension/1',parent_case_sha256=case_digest(parent),
        bridges=[dict(id='second-bridge',**{'from':dict(edge_id='b',endpoint='end'),
            'to':dict(edge_id='c',endpoint='start')},handle_lengths_mm=[10,10],samples=11,
            rationale='synthetic fixture extension',evidence_refs=['fixture'])])
    return parent,extension


def test_extension_preserves_existing_bridges_and_parent_provenance():
    parent,spec = parent_and_extension(); before=deepcopy(parent)
    result=extend_synthetic_routes(parent,spec,case_id='extended')
    assert parent==before
    assert result['edges'][:-1]==parent['edges'] and result['nodes']==parent['nodes']
    assert result['synthetic_route_inspection']['bridge_ids']==['bridge','second-bridge']
    assert result['generation']['config']['parent_generation']==parent['generation']
    assert result['synthetic_route_inspection']['parent_case_sha256']==case_digest(parent)
    assert result['synthetic_route_inspection']['collision_check']=='NOT RUN'


def test_extension_rejects_stale_parent_and_direct_source():
    parent,spec=parent_and_extension()
    spec['parent_case_sha256']='a'*64
    with pytest.raises(ValueError,match='hash'): extend_synthetic_routes(parent,spec,case_id='bad')
    source,_=fixture()
    with pytest.raises(ValueError,match='synthetic'): extend_synthetic_routes(source,spec,case_id='bad')


def test_side_branch_uses_explicit_radius_not_large_parent_radius():
    from vv_toolbox.synthetic_junctions import split_synthetic_junction
    from vv_toolbox.junction_continuity import inspect_bridge_continuity
    parent,_=parent_and_extension()
    split=split_synthetic_junction(parent,dict(schema='vv-toolbox.synthetic-junction/1',
        parent_case_sha256=case_digest(parent),source_hashes={s['id']:s['sha256'] for s in parent['sources']},
        edge_id='a',interval_index=0,fraction=.5,node_id='junction',child_edge_ids=['a1','a2'],
        rationale='fixture internal junction',evidence_refs=['fixture']),case_id='split')
    spec=dict(schema='vv-toolbox.synthetic-route-extension/1',parent_case_sha256=case_digest(split),
        bridges=[dict(id='side',**{'from':dict(edge_id='a1',endpoint='end'),
            'to':dict(edge_id='c',endpoint='start')},attachment_mode='side_branch',
            from_direction_xyz=[0,1,0],from_radius_mm=.5,handle_lengths_mm=[10,10],samples=1001,
            rationale='fixture side branch',evidence_refs=['fixture'])])
    result=extend_synthetic_routes(split,spec,case_id='branch')
    edge=result['edges'][-1]
    assert edge['radii_mm'][0]==.5
    assert sum('junction' in (e['start'],e['end']) for e in result['edges'])==3
    measurement=inspect_bridge_continuity(result,max_angle_deg=5,max_radius_jump_mm=0)
    row=next(r for r in measurement['attachments'] if r['bridge_id']=='side' and r['attachment']=='start')
    assert row['status']=='PASS'
    assert row['parent_radius_difference_mm']==1
    assert row['reference']=='declared side-branch direction/radius'
    assert split['edges']!=result['edges']
