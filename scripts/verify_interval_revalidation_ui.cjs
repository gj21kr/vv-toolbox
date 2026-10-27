const {chromium}=require('playwright'),fs=require('node:fs'),crypto=require('node:crypto');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.connectOverCDP('http://127.0.0.1:9222');
 const page=await browser.contexts()[0].newPage();page.setDefaultTimeout(300000);
 const base='http://127.0.0.1:8093',errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 const hash=()=>crypto.createHash('sha256').update(fs.readFileSync('reference-data/bodyparts3d/atlas-edits.snapshot.json')).digest('hex');
 let initial;
 try{
  initial=await page.request.get(base+'/api/state').then(r=>r.json());const originalHash=hash();
  assert.equal(initial.busy,false);assert.equal(initial.interval_preview_busy,false);
  await page.route('http://127.0.0.1:8094/**',r=>r.abort());
  await page.setViewportSize({width:1440,height:1000});
  await page.goto(base,{waitUntil:'domcontentloaded'});
  await page.waitForFunction(()=>typeof atlasCenterlineData!=='undefined'&&atlasCenterlineData);
  await page.request.post(base+'/api/atlas-selection',{data:{part_id:'FJ1692'}});
  await page.waitForFunction(()=>state?.atlas_selection==='FJ1692');
  await page.locator('#intervalPreviewPanel summary').click();
  await page.locator('#intervalFile').setInputFiles('exports/interval-snapshot-ui/candidate.json');
  await page.waitForFunction(()=>document.querySelector('#intervalMessage').textContent.startsWith('저장 후보 열림'));
  const responsePromise=page.waitForResponse(r=>r.url().endsWith('/api/atlas-interval-revalidate'));
  const started=Date.now();await page.locator('#intervalRevalidate').click();
  console.log('Current-scene revalidation started');
  const response=await responsePromise,result=await response.json();
  assert.equal(response.status(),200,JSON.stringify(result));
  assert.equal(result.revalidation.status,'PASS');assert.equal(result.revalidation.geometry_exact,true);
  assert.equal(result.applied,false);
  await page.waitForFunction(()=>document.querySelector('#intervalMessage').textContent.startsWith('현재 장면 재생성·검사 완료'));
  fs.mkdirSync('exports/interval-revalidation-ui',{recursive:true});
  await page.locator('#intervalResult').screenshot({path:'exports/interval-revalidation-ui/revalidated.png'});
  const after=await page.request.get(base+'/api/state').then(r=>r.json());
  assert.equal(after.generation,initial.generation);assert.deepEqual(after.atlas_modifications,initial.atlas_modifications);
  assert.equal(hash(),originalHash);assert.deepEqual(errors,[]);
  fs.writeFileSync('docs/evidence/interval-revalidation-ui.json',JSON.stringify({
   status:'PASS',scope:'Actual saved Atlas candidate import and current-scene regeneration',
   duration_ms:Date.now()-started,revalidation:result.revalidation,checks:result.checks,
   source_sha256:originalHash,source_unchanged:true,synthetic_response:false,
   full_viser_scene:'NOT RUN',errors
  },null,2)+'\n');
  console.log('PASS: actual saved candidate regenerated; exact geometry; source unchanged');
 }finally{
  if(initial?.atlas_selection)await page.request.post(base+'/api/atlas-selection',{data:{part_id:initial.atlas_selection}});
  await page.close();await browser.close();
 }
})().catch(e=>{console.error(e);process.exitCode=1});
