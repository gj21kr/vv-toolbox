import shutil
import subprocess

import pytest

from vv_toolbox.case_preview_ui import JS


def test_projection_pick_rotation_and_source_immutability():
    node=shutil.which('node')
    if node is None:
        pytest.skip('Node required for browser projection logic')
    setup=r"""
global.window={devicePixelRatio:1};
global.ResizeObserver=class {observe(){}};
const assert=require('node:assert/strict');
const listeners={};
const ctx=new Proxy({}, {get:(obj,key)=>obj[key]||(()=>{})});
const canvas={getContext:()=>ctx,getBoundingClientRect:()=>({width:800,height:400,left:0,top:0}),
 addEventListener:(name,fn)=>{listeners[name]=fn},setPointerCapture:()=>{}};
"""
    checks=r"""
const data={frame:{axes:'LPS',units:'mm'},edges:[
 {id:'first',centerline_mm:[[0,0,0],[10,0,0]]},
 {id:'second',centerline_mm:[[20,0,0],[30,0,0]]},
 {id:'missing',centerline_mm:null}]};
const before=JSON.stringify(data);
let chosen=null;
const view=new VVCasePreview(canvas,id=>{chosen=id});
view.setCase(data);
assert.match(view.frame,/2\/3/);
for(const angle of [0,.3,.7]){
 view.yaw=angle;view.pitch=-.6;view.draw();
 for(const [x,id] of [[5,'first'],[25,'second']]){
  const p=view.project([x,0,0]);
  assert.equal(view.pick(...p),id);
 }
}
assert.equal(view.pick(0,0),null);
view.select('second');
assert.equal(view.selected,'second');
view.focus();assert.deepEqual(view.center,[25,0,0]);assert.equal(view.extent,10);
view.fit();assert.deepEqual(view.center,[15,0,0]);assert.equal(view.extent,30);
const [x,y]=view.project([25,0,0]);
listeners.pointerdown({pointerId:1,clientX:x,clientY:y});
listeners.pointerup({clientX:x,clientY:y});
assert.equal(chosen,'second');
assert.equal(JSON.stringify(data),before);
view.setCase({frame:{axes:'LPS',units:'mm'},edges:[]});
assert.equal(view.pick(400,200),null);
const surfaceOnly={frame:{axes:'LPS',units:'mm'},edges:[],surface_parts:[{
 vertices_mm:[[0,0,0],[40,0,0],[0,20,0]],faces:[[0,1,2]]}]};
const unchanged=JSON.stringify(surfaceOnly);
view.setCase(surfaceOnly);
assert.equal(view.surfaceTriangles,1);
assert.deepEqual(view.center,[20,10,0]);
assert.equal(view.extent,Math.hypot(40,20));
assert(view.surfaceError.length>0,'No browser WebGL must be reported, not silently drawn');
assert.equal(JSON.stringify(surfaceOnly),unchanged);
view.setCase(data);view.showCenterlines=false;view.draw();
assert.equal(view.segments.length,0);assert.equal(view.pick(...view.project([5,0,0])),null);
view.showCenterlines=true;view.draw();assert(view.segments.length>0);
"""
    result=subprocess.run([node],input=setup+JS+checks,text=True,capture_output=True)
    assert result.returncode==0,result.stderr
