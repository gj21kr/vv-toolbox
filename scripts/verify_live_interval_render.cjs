const {chromium}=require('playwright');
const fs=require('node:fs'),crypto=require('node:crypto'),assert=require('node:assert/strict');
(async()=>{
 const raw=fs.readFileSync('exports/live-interval-preview/candidate.json'),candidate=JSON.parse(raw);
 const evidence=JSON.parse(fs.readFileSync('docs/evidence/live-interval-preview.json'));
 assert.equal(evidence.http_status,200);
 assert.deepEqual(candidate.checks,evidence.checks);
 const browser=await chromium.connectOverCDP('http://127.0.0.1:9222');
 const page=await browser.contexts()[0].newPage();page.setDefaultTimeout(120000);
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const base='http://127.0.0.1:8093';
 let initial;
 try{
  initial=await page.request.get(base+'/api/state').then(r=>r.json());
  assert.equal(initial.generation,candidate.generation);
  assert.equal(initial.source,'atlas');
  await page.route('http://127.0.0.1:8094/**',r=>r.abort());
  await page.route('**/api/atlas-interval-preview',async r=>{
   assert.deepEqual(r.request().postDataJSON(),evidence.request);
   await r.fulfill({contentType:'application/json',body:raw});
  });
  await page.setViewportSize({width:1440,height:1000});
  await page.goto(base,{waitUntil:'domcontentloaded'});
  await page.waitForFunction(()=>typeof atlasCenterlineData!=='undefined'&&atlasCenterlineData);
  await page.request.post(base+'/api/atlas-selection',{data:{part_id:candidate.part_id}});
  await page.waitForFunction(()=>state?.atlas_selection==='FJ1692');
  await page.locator('#intervalPreviewPanel summary').click();
  await page.waitForFunction(()=>!document.getElementById('intervalFields').disabled);
  const names={start_mm:'intervalStart',end_mm:'intervalEnd',factor:'intervalFactor',
   max_displacement_mm:'intervalMovement',absolute_scale_tolerance:'intervalTolerance'};
  for(const [field,id] of Object.entries(names))await page.locator('#'+id).fill(String(evidence.request[field]));
  await page.locator('#intervalForm button').click();
  await page.waitForFunction(()=>!document.getElementById('intervalResult').hidden);
  fs.mkdirSync('exports/live-interval-preview-render',{recursive:true});
  await page.locator('#intervalResult').screenshot({path:'exports/live-interval-preview-render/candidate.png'});
  await page.locator('#intervalCompare').click();
  await page.locator('#intervalResult').screenshot({path:'exports/live-interval-preview-render/reference.png'});
  assert.deepEqual(errors,[]);
  fs.writeFileSync('docs/evidence/live-interval-render.json',JSON.stringify({
   status:'PASS',scope:'Replay of recorded actual Atlas HTTP candidate; no geometry regeneration',
   candidate_sha256:crypto.createHash('sha256').update(raw).digest('hex'),
   vertices:candidate.vertices.length,faces:candidate.faces.length,
   original_candidate_comparison:true,errors,main_viser_frame:'not loaded'
  },null,2)+'\n');
  console.log('PASS: recorded actual Atlas candidate and original comparison rendered');
 }finally{
  if(initial?.atlas_selection)await page.request.post(base+'/api/atlas-selection',{data:{part_id:initial.atlas_selection}});
  await page.close();await browser.close();
 }
})().catch(e=>{console.error(e);process.exitCode=1});
