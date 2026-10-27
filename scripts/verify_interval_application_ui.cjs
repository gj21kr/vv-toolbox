const {chromium}=require('playwright'),fs=require('node:fs'),crypto=require('node:crypto');
const assert=require('node:assert/strict');
const sessionMode=process.argv.includes('--session');
(async()=>{
 const browser=await chromium.connectOverCDP('http://127.0.0.1:9222');
 const page=await browser.contexts()[0].newPage();page.setDefaultTimeout(300000);
 const base='http://127.0.0.1:8093',errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 const hash=()=>crypto.createHash('sha256').update(fs.readFileSync('reference-data/bodyparts3d/atlas-edits.snapshot.json')).digest('hex');
 let initial,appliedGeneration;
 try{
  initial=await page.request.get(base+'/api/state').then(r=>r.json());const originalHash=hash();
  assert.equal(initial.busy,false);assert.equal(initial.interval_preview_busy,false);
  assert.deepEqual(initial.atlas_interval_edits,{});
  await page.route('http://127.0.0.1:8094/**',r=>r.abort());
  await page.setViewportSize({width:1440,height:1100});
  await page.goto(base,{waitUntil:'domcontentloaded'});
  await page.waitForFunction(()=>typeof atlasCenterlineData!=='undefined'&&atlasCenterlineData);
  await page.request.post(base+'/api/atlas-selection',{data:{part_id:'FJ1692'}});
  await page.waitForFunction(()=>state?.atlas_selection==='FJ1692');
  await page.locator('#intervalPreviewPanel summary').click();
  await page.locator('#intervalFile').setInputFiles('exports/interval-snapshot-ui/candidate.json');
  await page.waitForFunction(()=>document.querySelector('#intervalMessage').textContent.startsWith('저장 후보 열림'));
  const responsePromise=page.waitForResponse(r=>r.url().endsWith('/api/atlas-interval-apply'));
  const started=Date.now();await page.locator('#intervalApply').click();
  console.log('Current-scene candidate application started');
  const response=await responsePromise,result=await response.json();
  assert.equal(response.status(),200,JSON.stringify(result));
  appliedGeneration=result.generation;assert.equal(result.status,'APPLIED');
  await page.waitForFunction(()=>state?.atlas_interval_edits?.FJ1692===1);
  assert.equal(await page.locator('#intervalUndo').isEnabled(),true);
  const editStatus=await page.request.get(base+'/api/atlas-edit-session').then(r=>r.json());
  assert.equal(editStatus.available,false);assert.equal(editStatus.dirty,true);
  const applied=await page.request.get(base+'/api/state').then(r=>r.json());
  assert.equal(applied.generation,initial.generation+1);
  assert.equal(applied.atlas_edit_checks.FJ1692.section_targets.status,'PASS');
  fs.mkdirSync('exports/interval-application-ui',{recursive:true});
  await page.locator('#intervalPreviewPanel').screenshot({path:'exports/interval-application-ui/applied.png'});
  let sessionFile;
  if(sessionMode){
   const downloading=page.waitForEvent('download');
   await page.locator('#intervalSessionDownload').click();
   const download=await downloading;
   sessionFile='exports/interval-application-ui/session.json';
   await download.saveAs(sessionFile);
   assert.equal(JSON.parse(fs.readFileSync(sessionFile)).schema,'vv-toolbox.interval-session/1');
  }
  const undoPromise=page.waitForResponse(r=>r.url().endsWith('/api/atlas-interval-undo'));
  await page.locator('#intervalUndo').click();
  const undoResponse=await undoPromise;assert.equal(undoResponse.status(),200);
  await page.waitForFunction(()=>Object.keys(state?.atlas_interval_edits||{}).length===0&&!state?.atlas_interval_undo_available);
  appliedGeneration=null;
  const after=await page.request.get(base+'/api/state').then(r=>r.json());
  assert.equal(after.generation,initial.generation+2);
  assert.deepEqual(after.atlas_modifications,initial.atlas_modifications);
  assert.deepEqual(after.atlas_edit_checks,initial.atlas_edit_checks);
  if(sessionMode){
   const restoring=page.waitForResponse(r=>r.url().endsWith('/api/atlas-interval-session'));
   await page.locator('#intervalSessionFile').setInputFiles(sessionFile);
   console.log('Downloaded session restoration started');
   const response=await restoring,data=await response.json();
   assert.equal(response.status(),200,JSON.stringify(data));assert.equal(data.status,'RESTORED');
   appliedGeneration=data.generation;
   await page.waitForFunction(()=>state?.atlas_interval_edits?.FJ1692===1);
   await page.locator('#intervalPreviewPanel').screenshot({path:'exports/interval-application-ui/session-restored.png'});
   const undoing=page.waitForResponse(r=>r.url().endsWith('/api/atlas-interval-undo'));
   await page.locator('#intervalUndo').click();assert.equal((await undoing).status(),200);
   appliedGeneration=null;
   const restored=await page.request.get(base+'/api/state').then(r=>r.json());
   assert.equal(restored.generation,initial.generation+4);
   assert.deepEqual(restored.atlas_interval_edits,{});
   assert.deepEqual(restored.atlas_edit_checks,initial.atlas_edit_checks);
  }
  assert.equal(hash(),originalHash);assert.deepEqual(errors,[]);
  fs.writeFileSync(sessionMode?'docs/evidence/interval-session-ui.json':'docs/evidence/interval-application-ui.json',JSON.stringify({
   status:'PASS',scope:'Actual saved Atlas candidate application and undo through browser controls',
   duration_ms:Date.now()-started,part_id:'FJ1692',source_sha256:originalHash,
   generations:[initial.generation,applied.generation,after.generation],
   source_unchanged:true,active_edit_checks_restored:true,synthetic_response:false,
   full_viser_scene:'NOT RUN',errors,
   session_download_restore_undo:sessionMode?'PASS':'NOT RUN'
  },null,2)+'\n');
  console.log('PASS: candidate applied and undone; source and prior edits preserved');
 }finally{
  if(appliedGeneration!==undefined&&appliedGeneration!==null){
   const response=await page.request.post(base+'/api/atlas-interval-undo',{data:{},headers:{'X-Expected-Generation':String(appliedGeneration)}});
   if(!response.ok())console.error('Cleanup undo rejected; inspect active interval edits');
  }
  if(initial?.atlas_selection)await page.request.post(base+'/api/atlas-selection',{data:{part_id:initial.atlas_selection}});
  await page.close();await browser.close();
 }
})().catch(e=>{console.error(e);process.exitCode=1});
