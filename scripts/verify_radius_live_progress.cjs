const {chromium}=require('playwright');
const fs=require('node:fs'),assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true});
 const page=await browser.newPage({viewport:{width:1440,height:1100}});
 const base='http://127.0.0.1:8093',errors=[];
 const output='exports/radius-live-progress';fs.mkdirSync(output,{recursive:true});
 page.on('pageerror',error=>errors.push(error.message));
 try{
  const before=await page.request.get(base+'/api/state').then(r=>r.json());
  assert.equal(before.candidate_radius_busy,true);
  await page.route('http://127.0.0.1:8094/**',route=>route.abort());
  await page.goto(base,{waitUntil:'domcontentloaded'});
  await page.waitForFunction(()=>state?.candidate_radius_busy&&state.candidate_radius_progress?.total>0);
  const progress=await page.evaluate(()=>state.candidate_radius_progress);
  const text=await page.locator('#candidateRadiusStatus').innerText();
  assert.match(text,/형상 계산|중심선 검사|주변 혈관 검사/);
  assert.match(text,/\d+\/\d+/);
  assert.equal(await page.locator('#candidateRadiusPreview').isDisabled(),true);
  assert.equal(await page.locator('#candidateReturn').isDisabled(),true);
  assert(before.candidate_radius_request);
  for(const [id,key] of [['candidateRadiusScale','scale'],['candidateRadiusTransition','transition_mm'],['candidateRadiusBound','max_displacement_mm']]){
   assert.equal(await page.locator('#'+id).inputValue(),String(before.candidate_radius_request[key]));
   assert.equal(await page.locator('#'+id).isDisabled(),true);
  }
  await page.locator('#candidateRadius').scrollIntoViewIfNeeded();
  await page.locator('#candidateRadius').screenshot({path:output+'/progress.png'});
  const after=await page.request.get(base+'/api/state').then(r=>r.json());
  assert.equal(after.generation,before.generation);
  assert.equal(after.candidate.surface_sha256,before.candidate.surface_sha256);
  assert.deepEqual(errors,[]);
  fs.writeFileSync('docs/evidence/radius-live-progress-ui.json',JSON.stringify({
   status:'PASS',scope:'Observe actual running request; no model mutation',progress,text,
   generation:before.generation,surface_sha256:before.candidate.surface_sha256,
   running_parameters:before.candidate_radius_request,parameter_inputs_locked:true,
   viewer_visual:'SCREENSHOT_REQUIRES_INSPECTION',browser_errors:errors,
   roundtrip_completion:'NOT CHECKED'},null,2)+'\n');
  console.log(JSON.stringify({status:'PASS',progress}));
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1});
