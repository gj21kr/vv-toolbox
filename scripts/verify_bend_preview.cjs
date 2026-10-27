const {chromium}=require('playwright');
const fs=require('node:fs'),assert=require('node:assert/strict');
(async()=>{
 const base='http://127.0.0.1:8093',output='exports/access-bend-ui';
 fs.mkdirSync(output,{recursive:true});
 const browser=await chromium.launch({headless:true});
 const page=await browser.newPage({viewport:{width:1440,height:1100}});
 page.setDefaultTimeout(60000);
 const errors=[],report={status:'RUNNING',scope:'Actual read-only bend candidate surface/centerline viewer'};
 page.on('pageerror',e=>errors.push(e.message));
 let selected=false;
 try{
  const initial=await page.request.get(base+'/api/state').then(r=>r.json());
  assert.equal(initial.source,'atlas');assert.equal(initial.candidate_radius_busy,false);
  assert.deepEqual(initial.atlas_modifications,{});assert.deepEqual(initial.atlas_interval_edits,{});
  await page.route('http://127.0.0.1:8094/**',r=>r.abort());
  await page.goto(base,{waitUntil:'domcontentloaded'});
  await page.waitForFunction(()=>state?.source==='atlas');
  await page.locator('#candidateSelect').selectOption('access-femoral-bend-inspection');
  await page.locator('#showCandidate').click();selected=true;
  await page.waitForFunction(()=>state?.candidate?.id==='access-femoral-bend-inspection');
  report.candidate=await page.evaluate(()=>state.candidate);
  assert.equal(report.candidate.access_union.checked_paths,65);
  assert.equal(report.candidate.read_only,true);
  assert.equal(await page.locator('#candidateRadius').isVisible(),false);
  assert.match(await page.locator('#candidateChecks').innerText(),/읽기 전용 검사 후보/);
  await page.locator('#candidateSource').selectOption('FJ2074');
  await page.waitForFunction(()=>state.candidate.selected_source==='FJ2074');
  await page.locator('#candidateChecks').screenshot({path:output+'/checks.png'});
  await page.unroute('http://127.0.0.1:8094/**');
  await page.locator('#stage iframe').evaluate(f=>{f.src=f.src;});
  await page.frameLocator('#stage iframe').locator('canvas').first().waitFor({state:'visible'});
  await page.waitForTimeout(2000);
  await page.locator('#stage').screenshot({path:output+'/surface.png'});
  await page.locator('#candidateView').click();
  await page.waitForFunction(()=>state.mode==='Centerlines');
  await page.waitForTimeout(1200);
  await page.locator('#stage').screenshot({path:output+'/centerlines.png'});
  assert.deepEqual(errors,[]);report.status='PASS';report.browser_errors=errors;
 }catch(error){report.status='FAIL';report.error=String(error);process.exitCode=1;}
 finally{
  try{if(selected){await page.locator('#stage iframe').evaluateAll(frames=>frames.forEach(f=>f.remove()));
    await page.request.post(base+'/api/source',{data:{source:'atlas'}});
    report.atlas_restored=(await page.request.get(base+'/api/state').then(r=>r.json())).source==='atlas';
    assert.equal(report.atlas_restored,true);}}
  catch(error){report.status='FAIL';report.cleanup_error=String(error);process.exitCode=1;}
  await browser.close();fs.writeFileSync('docs/evidence/access-bend-ui.json',JSON.stringify(report,null,2)+'\n');
 }
 console.log(JSON.stringify({status:report.status,error:report.error,atlas_restored:report.atlas_restored}));
})().catch(error=>{console.error(error);process.exitCode=1});
