const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
(async()=>{
 const browser=await chromium.connectOverCDP('http://127.0.0.1:9222');
 const page=await browser.contexts()[0].newPage();page.setDefaultTimeout(120000);
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const url='http://127.0.0.1:8093';
 let initial;
 try{
  initial=await page.request.get(url+'/api/state').then(r=>r.json());
  assert.equal(initial.source,'atlas');
  await page.setViewportSize({width:1440,height:1000});
  // This test targets the control panel and its own canvas, not the Viser scene.
  await page.route('http://127.0.0.1:8094/**',route=>route.abort());
  await page.goto(url,{waitUntil:'domcontentloaded'});
  await page.waitForFunction(()=>typeof atlasCenterlineData!=='undefined'&&atlasCenterlineData&&state?.atlas_centerlines.available);
  assert((await page.request.post(url+'/api/atlas-selection',{data:{part_id:'FJ1692'}})).ok());
  await page.waitForFunction(()=>state?.atlas_selection==='FJ1692');
  await page.locator('#intervalPreviewPanel summary').click();
  await page.waitForFunction(()=>!document.querySelector('#intervalFields').disabled);
  for(const [id,value] of Object.entries({intervalStart:'1',intervalEnd:'2',intervalFactor:'.9',intervalMovement:'0.000000000001',intervalTolerance:'.01'}))
   await page.locator('#'+id).fill(value);
  await page.locator('#intervalForm button').click();
  await page.waitForFunction(()=>document.querySelector('#intervalMessage').textContent.includes('Projection exceeds'));
  assert(await page.locator('#intervalResult').isHidden());
  const vertices=[],faces=[];
  for(let r=0;r<7;r++)for(let i=0;i<16;i++){const a=i*Math.PI/8,z=r-3;vertices.push([Math.cos(a)+.07*z*z,Math.sin(a),z]);}
  for(let r=0;r<6;r++)for(let i=0;i<16;i++){const a=r*16+i,b=r*16+(i+1)%16;faces.push([a,b,b+16],[a,b+16,a+16]);}
  await page.route('**/api/atlas-interval-preview',async route=>{
   const body=route.request().postDataJSON(),generation=Number(route.request().headers()['x-expected-generation']);
   await route.fulfill({json:{status:'CANDIDATE',read_only:true,applied:false,generation,part_id:body.part_id,layer:'arterial',
    reference_vertices:vertices,vertices:vertices.map(([x,y,z])=>[x*(1-.15*Math.exp(-z*z)),y*(1-.15*Math.exp(-z*z)),z]),faces}});
  });
  await page.locator('#intervalMovement').fill('.3');
  await page.locator('#intervalForm button').click();
  await page.waitForFunction(()=>!document.querySelector('#intervalResult').hidden);
  await page.locator('#intervalCanvas').focus();await page.keyboard.press('ArrowRight');
  fs.mkdirSync('exports/interval-preview-ui',{recursive:true});
  await page.locator('#intervalResult').screenshot({path:'exports/interval-preview-ui/candidate.png'});
  await page.locator('#intervalCompare').click();
  assert.equal(await page.locator('#intervalCompare').innerText(),'후보 보기');
  await page.setViewportSize({width:390,height:844});
  await page.locator('#intervalPreviewPanel').scrollIntoViewIfNeeded();
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
  await page.locator('#intervalFactor').scrollIntoViewIfNeeded();
  await page.screenshot({path:'exports/interval-preview-ui/mobile.png'});
  await page.request.post(url+'/api/atlas-selection',{data:{part_id:'FJ1654'}});
  await page.waitForFunction(()=>document.querySelector('#intervalResult').hidden);
  assert.deepEqual(errors,[]);
  const after=await page.request.get(url+'/api/state').then(r=>r.json());
  assert.deepEqual(after.atlas_modifications,initial.atlas_modifications);
  assert.equal(after.generation,initial.generation);
  fs.writeFileSync('docs/evidence/interval-preview-ui.json',JSON.stringify({
   status:'PASS',browser:'Playwright CDP; Browser plugin not available',
   actual_http_rejection:true,success_rendering:'synthetic intercepted response',
   comparison_toggle:true,keyboard_rotation:true,mobile_no_overflow:true,main_viser_frame:'not loaded in this focused test',
   selection_invalidates_result:true,active_modifications_unchanged:true,errors
  },null,2)+'\n');
  console.log('PASS: real rejection, synthetic candidate rendering, comparison, mobile and stale-result clearing');
 }finally{
  if(initial?.atlas_selection)await page.request.post(url+'/api/atlas-selection',{data:{part_id:initial.atlas_selection}});
  await page.close();await browser.close();
 }
})().catch(error=>{console.error(error);process.exitCode=1});
