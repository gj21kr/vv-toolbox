import json
import shutil
import subprocess

import pytest

from vv_toolbox.web_ui import HTML


@pytest.mark.skipif(not shutil.which('node'),reason='Node required for UI logic')
def test_both_ends_use_along_path_distance_and_keep_reciprocal_links():
    fn='function endpointNeighborhood('+HTML.split('function endpointNeighborhood(',1)[1].split('function drawEndpointConnections(',1)[0]
    # Folded centerline: attachment's spatially nearest end is not its along-path end.
    data=dict(nodes=[],edges=[dict(id='e',part_id='v',start='a',end='b',points=[[0,0,0],[10,0,0],[10,.1,0],[0,.1,0],[0,1,0]])],links=[
        dict(id='one',part_a='v',part_b='parent',start='a',distance=1),
        dict(id='two',part_a='child',part_b='v',target_edge='e',target_point=[0,.1,0],distance=2),
        dict(id='three',part_a='v',part_b='parent',start='b',distance=3)])
    script=fn+'\nconst assert=require("node:assert/strict");const data='+json.dumps(data)+r''';
const r=endpointNeighborhood(data,'v');
assert.equal(r.groups.length,2);
assert.deepEqual(r.groups[0].neighbors.map(n=>n[0]),['parent']);
assert.deepEqual(r.groups[1].neighbors.map(n=>n[0]),['child','parent']);
assert.equal(r.unassigned,0);
data.links=[];
assert.equal(endpointNeighborhood(data,'v').groups.length,2);
assert(endpointNeighborhood(data,'v').groups.every(g=>g.neighbors.length===0));
data.edges.push({id:'f',part_id:'v',start:'b',end:'c',points:[[0,1,0],[0,2,0]]});
data.edges.push({id:'g',part_id:'v',start:'b',end:'d',points:[[0,1,0],[0,1,1]]});
assert.equal(endpointNeighborhood(data,'v').groups.filter(g=>g.kind==='end').length,3);
assert.equal(endpointNeighborhood(data,'v').groups.filter(g=>g.kind==='junction').length,1);
'''
    r=subprocess.run(['node'],input=script,encoding='utf-8',capture_output=True)
    assert r.returncode==0,r.stderr
