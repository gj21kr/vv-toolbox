const {chromium}=require('playwright');
const fs=require('node:fs'),assert=require('node:assert/strict');
const downloadCase=process.argv.includes('--download-case');
const reuse=process.argv.includes('--reuse')||downloadCase;
const output=downloadCase?'exports/access-radius-case-download':reuse?'exports/access-radius-roundtrip-reuse':'exports/access-radius-roundtrip';
const record=downloadCase?'docs/evidence/access-radius-case-download.json':reuse?'docs/evidence/access-radius-roundtrip-reuse.json':'docs/evidence/access-radius-roundtrip.json';
fs.mkdirSync(output,{recursive:true});
const report={status:'RUNNING',scope:'Actual browser request, result, apply gate, discard and restore',
  parameters:{scale:1.05,transition_mm:10,max_displacement_mm:1},phase:'starting',
  started_at:new Date().toISOString(),progress_history:[]};
function save(){fs.writeFileSync(record,JSON.stringify(report,null,2)+'\n');}
(async()=>{
 const browser=await chromium.launch({headless:true});
 const page=await browser.newPage({viewport:{width:1440,height:1100}});
 const base='http://127.0.0.1:8093',errors=[];
 page.setDefaultTimeout(60000);
 page.on('pageerror',e=>errors.push(e.message));
 let progressTimer;
 save();
 try{
  const initial=await page.request.get(base+'/api/state').then(r=>r.json());
  assert.equal(initial.source,'atlas');
  assert.deepEqual(initial.atlas_modifications,{});assert.deepEqual(initial.atlas_interval_edits,{});
  await page.route('http://127.0.0.1:8094/**',r=>r.abort());
  await page.goto(base,{waitUntil:'domcontentloaded'});
  await page.waitForFunction(()=>state?.source==='atlas');
  await page.locator('#candidateSelect').selectOption('resampled-access-protected');
  await page.locator('#showCandidate').click();
  await page.waitForFunction(()=>state?.source==='candidate');
  report.parent_sha256=await page.evaluate(()=>state.candidate.surface_sha256);
  await page.locator('#candidateSource').selectOption('FJ2074');
  await page.waitForFunction(()=>state.candidate.selected_source==='FJ2074');
  await page.locator('#candidateRadiusScale').fill('1.05');
  await page.locator('#candidateRadiusTransition').fill('10');
  await page.locator('#candidateRadiusBound').fill('1');
  const response=page.waitForResponse(r=>r.url()===base+'/api/candidate-radius-preview',{timeout:1800000});
  await page.locator('#candidateRadiusPreview').click();
  await page.waitForFunction(()=>state.candidate_radius_busy||radiusPending);
  assert.equal(await page.locator('#candidateRadiusPreview').isDisabled(),true);
  report.phase='computing';save();console.log('Radius request running');
  if(downloadCase){
   await page.waitForFunction(()=>state.candidate_radius_busy===true);
   assert.equal(await page.locator('#candidateCaseSave').isDisabled(),true);
   const generation=await page.evaluate(()=>state.generation);
   const blocked=await page.request.get(base+'/api/candidate-case-snapshot',{
    headers:{'X-Expected-Generation':String(generation)}});
   assert.equal(blocked.status(),400);report.busy_download_blocked=400;save();
  }
  progressTimer=setInterval(async()=>{
   try{
    const progress=await page.evaluate(()=>state?.candidate_radius_progress);
    if(progress?.phase&&JSON.stringify(progress)!==JSON.stringify(report.progress_history.at(-1))){
     report.progress_history.push(progress);save();
    }
   }catch{}
  },5000);
  const reply=await response;report.http_status=reply.status();
  // Long-running requests can outlive Chromium's response-body cache.
  // Verify HTTP status, then inspect the actual polled application state.
  assert.equal(reply.status(),200,`Radius request HTTP ${reply.status()}`);
  await page.waitForFunction(()=>!!state.candidate_radius?.preview_token&&!radiusPending);
  report.candidate=await page.evaluate(()=>state.candidate);
  if(reuse){
   const baseline=JSON.parse(fs.readFileSync('docs/evidence/access-radius-roundtrip.json','utf8').replace(/^\uFEFF/,''));
   assert.equal(baseline.status,'PASS');
   assert.equal(report.parent_sha256,baseline.parent_sha256);
   assert.equal(report.candidate.geometry_sha256,baseline.candidate.geometry_sha256);
   assert.deepEqual(report.candidate.radius_edit,baseline.candidate.radius_edit);
   report.baseline_geometry_and_audit_equal=true;
   report.baseline_elapsed_seconds=baseline.elapsed_seconds;
  }
  assert.equal(report.candidate.radius_edit.centerline_containment.expected_edges,65);
  assert.equal(report.candidate.radius_edit.centerline_containment.rows.length,65);
  assert.equal(report.candidate.radius_edit.neighbor_context.neighbors,788);
  if(downloadCase){
   const pending=page.waitForEvent('download');
   await page.locator('#candidateCaseSave').click();
   const file=await pending;await file.saveAs(output+'/case.snapshot.json');
   const doc=JSON.parse(fs.readFileSync(output+'/case.snapshot.json','utf8'));
   assert.equal(doc.schema,'vv-toolbox.case-snapshot/1');
   assert.equal(doc.case.edges.length,65);assert.equal(doc.case.surface_parts[0].faces.length,50188);
   const inspection=doc.case.inspection.access_candidate;
   assert.equal(inspection.accepted_for_generation,false);
   assert.equal(inspection.summary.geometry_sha256,report.candidate.geometry_sha256);
   assert.deepEqual(inspection.summary.radius_edit,report.candidate.radius_edit);
   report.download={status:'PASS',file:output+'/case.snapshot.json',revision:doc.revision,
     geometry_sha256:inspection.summary.geometry_sha256,failed_checks_preserved:true,
     independent_reload:'NOT RUN'};save();
  }
  const allowed=report.candidate.radius_edit.neighbor_contact==='PASS'&&report.candidate.radius_edit.centerline_containment.status==='PASS';
  assert.equal(await page.locator('#candidateRadiusApply').isEnabled(),allowed);
  if(!allowed){
   const s=await page.request.get(base+'/api/state').then(r=>r.json());
   const blocked=await page.request.post(base+'/api/candidate-radius-action',{
    headers:{'X-Expected-Generation':String(s.generation)},data:{action:'apply',token:s.candidate_radius.preview_token}});
   assert.equal(blocked.ok(),false);report.apply_blocked_status=blocked.status();
  }
  await page.unroute('http://127.0.0.1:8094/**');
  await page.locator('#stage iframe').evaluate(f=>{f.src=f.src;});
  await page.frameLocator('#stage iframe').locator('canvas').first().waitFor({state:'visible'});
  await page.waitForTimeout(2000);
  await page.locator('#stage').screenshot({path:output+'/preview.png'});
  await page.locator('#candidateRadius').scrollIntoViewIfNeeded();
  await page.locator('#candidateRadius').screenshot({path:output+'/controls.png'});
  await page.locator('#candidateRadiusDiscard').click();
  await page.waitForFunction(()=>!radiusPending&&!state.candidate_radius?.preview_token&&!state.candidate.radius_edit);
  assert.equal(await page.evaluate(()=>state.candidate.surface_sha256),report.parent_sha256);
  report.discard_restored_parent=true;report.status='PASS';report.phase='complete';
  report.browser_errors=errors;assert.deepEqual(errors,[]);
 }catch(error){report.status='FAIL';report.error=String(error);throw error;}
 finally{
  clearInterval(progressTimer);
  try{
   const s=await page.request.get(base+'/api/state').then(r=>r.json());
   if(!s.candidate_radius_busy){
    if(s.candidate_radius?.preview_token)await page.request.post(base+'/api/candidate-radius-action',{
     headers:{'X-Expected-Generation':String(s.generation)},data:{action:'discard',token:s.candidate_radius.preview_token}});
    await page.locator('#stage iframe').evaluateAll(frames=>frames.forEach(f=>f.remove()));
    await page.request.post(base+'/api/source',{data:{source:'atlas'}});
    report.atlas_restored=(await page.request.get(base+'/api/state').then(r=>r.json())).source==='atlas';
   }else report.atlas_restored=false;
  }finally{report.elapsed_seconds=(Date.now()-Date.parse(report.started_at))/1000;save();await browser.close();}
 }
 console.log(JSON.stringify({status:report.status,atlas_restored:report.atlas_restored}));
})().catch(error=>{console.error(error);process.exitCode=1});
