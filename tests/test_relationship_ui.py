"""Exercise the actual relationship renderer with incoming and outgoing links."""
import shutil
import subprocess

import pytest

from vv_toolbox.web_ui import HTML


@pytest.mark.skipif(not shutil.which('node'), reason='Node is needed for UI logic')
def test_relationships_keep_both_attachment_sides_and_more_than_four_neighbors():
    function = HTML.split('function drawAtlasCenterlines(){', 1)[1].split(
        'async function updateAtlasCenterlines()', 1)[0]
    script = r'''
const assert=require('node:assert/strict');
class Element {
 constructor(){this.children=[];this.attrs={};this.style={};this.parentElement={style:{}};}
 replaceChildren(){this.children=[];}
 setAttribute(k,v){this.attrs[k]=v;}
 append(el){this.children.push(el);}
}
const elements={atlasCenterlineGraph:new Element(),atlasRelationSummary:new Element(),atlasRelationMode:{value:'proximity'},atlasRelationEvidence:new Element()};
const $=id=>elements[id],document={createElementNS:()=>new Element()};
let atlasCenterlineLastSelection=null;
const state={atlas_selection:'selected',atlas:{parts:[{id:'selected',name:'Selected',layer:'arterial'}]}};
const atlasCenterlineData={nodes:[],edges:[{part_id:'selected',points:[[0,0,0],[0,0,100]]}],links:[]};
for(let i=0;i<6;i++){
 const id='neighbor'+i,point=[0,0,i<3?0:100];
 state.atlas.parts.push({id,name:id,layer:'arterial'});
 atlasCenterlineData.nodes.push({id:'attach'+i,point});
 atlasCenterlineData.links.push(i%2?
  {part_a:id,part_b:'selected',end:'attach'+i,distance:i}:
  {part_a:'selected',part_b:id,start:'attach'+i,distance:i});
}
''' + 'function drawAtlasCenterlines(){' + function + r'''
drawAtlasCenterlines();
const nodes=elements.atlasCenterlineGraph.children.filter(e=>e.attrs.role==='button');
assert.equal(nodes.length,7);
const selected=nodes.find(e=>e.attrs['aria-label']==='Focus vessel Selected');
const selectedY=selected.children[0].attrs.y;
assert.equal(nodes.filter(e=>e.children[0].attrs.y<selectedY).length,3);
assert.equal(nodes.filter(e=>e.children[0].attrs.y>selectedY).length,3);
assert.match(elements.atlasRelationSummary.textContent,/6 neighboring candidates.*all shown/);
'''
    result = subprocess.run(['node'], input=script, encoding='utf-8', capture_output=True)
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(not shutil.which('node'), reason='Node is needed for UI logic')
def test_reference_renderer_keeps_unresolved_slots_out_of_vessel_diagram():
    function=HTML.split('function drawReferenceJunctions(',1)[1].split('function drawAtlasCenterlines()',1)[0]
    script=r'''
const assert=require('node:assert/strict');
class Element {
 constructor(tag){this.tag=tag;this.children=[];this.attrs={};this.style={};this.parentElement={style:{}};this.textContent='';}
 replaceChildren(){this.children=[];}
 setAttribute(k,v){this.attrs[k]=v;}
 append(...els){this.children.push(...els);}
}
const elements={atlasCenterlineGraph:new Element(),atlasRelationSummary:new Element(),atlasRelationEvidence:new Element()};
const $=id=>elements[id],document={createElementNS:(_,tag)=>new Element(tag),createElement:tag=>new Element(tag)};
const parts=new Map([['a',{name:'Parent'}],['b',{name:'Element one'}],['c',{name:'Element two'}]]);
const data={reference_topology:{junctions:[{label:'Test',kind:'branch',source_url:'https://example.org',members:[
 {role:'parent',part_ids:['a'],expected_names:['Parent'],mapping_status:'concept_matched'},
 {role:'branch',part_ids:['b','c'],expected_names:['One concept'],mapping_status:'multiple_elements_same_concept'},
 {role:'branch',part_ids:[],related_part_ids:['b'],expected_names:['Missing trunk'],mapping_status:'concept_members_found'}]}]}};
'''+'function drawReferenceJunctions('+function+r'''
drawReferenceJunctions(data,'a',parts);
const text=e=>e.textContent+' '+e.children.map(text).join(' ');
assert(!text(elements.atlasCenterlineGraph).includes('Missing trunk'));
assert(text(elements.atlasRelationEvidence).includes('Needs review'));
assert(text(elements.atlasCenterlineGraph).includes('2 elements · one concept'));
assert.equal(elements.atlasCenterlineGraph.children.filter(e=>e.tag==='g').length,2);
'''
    result=subprocess.run(['node'],input=script,encoding='utf-8',capture_output=True)
    assert result.returncode==0,result.stderr
