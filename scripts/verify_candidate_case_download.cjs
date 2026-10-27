const {chromium}=require('playwright');
const fs=require('node:fs'),assert=require('node:assert/strict'),crypto=require('node:crypto');
(async()=>{
 const bend=process.argv.includes('--bend');
 const id=bend?'access-femoral-bend-inspection':'resampled-access-protected';
 const base='http://127.0.0.1:8093',out=bend?'exports/bend-case-download':'exports/candidate-case-download';
 fs.mkdirSync(out,{recursive:true});
 const browser=await chromium.launch({headless:true});
 const page=await browser.newPage({acceptDownloads:true,viewport:{width:1440,height:1100}});
 page.setDefaultTimeout(60000);
 const errors=[],report={status:'RUNNING',scope:`Actual browser ${id} case download; not anatomy acceptance`,browser_path:'Playwright: Browser plugin not available'};
 page.on('pageerror',e=>errors.push(e.message));
 let selected=false;
 try{
  const initial=await page.request.get(base+'/api/state').then(r=>r.json());
  assert.equal(initial.source,'atlas');assert.equal(initial.candidate_radius_busy,false);
  assert.deepEqual(initial.atlas_modifications,{});assert.deepEqual(initial.atlas_interval_edits,{});
  await page.route('http://127.0.0.1:8094/**',r=>r.abort());
  await page.goto(base,{waitUntil:'domcontentloaded'});
  await page.waitForFunction(()=>state?.source==='atlas');
  await page.locator('#candidateSelect').selectOption(id);
  await page.locator('#showCandidate').click();selected=true;
  await page.waitForFunction(id=>state?.candidate?.id===id,id);
  const generation=await page.evaluate(()=>state.generation);
  const stale=await page.request.get(base+'/api/candidate-case-snapshot',{headers:{'X-Expected-Generation':String(generation-1)}});
  assert.equal(stale.status(),409);
  const button=page.locator('#candidateCaseSave');assert.equal(await button.isEnabled(),true);
  assert.match(await page.locator('#candidateExport').innerText(),/승인된 생성 데이터가 아닙니다/);
  await button.scrollIntoViewIfNeeded();
  const waiting=page.waitForEvent('download');await button.click();const download=await waiting;
  await download.saveAs(out+'/case.snapshot.json');
  const bytes=fs.readFileSync(out+'/case.snapshot.json'),doc=JSON.parse(bytes);
  assert.equal(doc.schema,'vv-toolbox.case-snapshot/1');
  assert.equal(doc.case.edges.length,65);assert.equal(doc.case.surface_parts[0].faces.length,50188);
  assert.equal(doc.case.inspection.access_candidate.accepted_for_generation,false);
  if(bend){
   assert.equal(doc.case.inspection.access_candidate.context.status,'FAIL');
   assert.equal(doc.case.inspection.access_candidate.context.rows.length,788);
   assert.equal(await page.locator('#candidateRadius').isVisible(),false);
   assert.equal(doc.case.generation.config.parent_graph_revision,await page.evaluate(()=>state.candidate.access_graph.revision));
  }
  assert.equal((await page.request.get(base+'/api/state').then(r=>r.json())).generation,generation);
  await page.locator('#candidateExport').screenshot({path:out+'/controls.png'});
  assert.deepEqual(errors,[]);
  Object.assign(report,{status:'PASS',stale_generation_status:409,revision:doc.revision,
    file_sha256:crypto.createHash('sha256').update(bytes).digest('hex'),file:out+'/case.snapshot.json',
    browser_errors:errors,geometry_reload:'NOT RUN',visual_review:'NOT RUN'});
 }catch(error){report.status='FAIL';report.error=String(error);process.exitCode=1;}
 finally{
  try{if(selected){await page.request.post(base+'/api/source',{data:{source:'atlas'}});
    report.atlas_restored=(await page.request.get(base+'/api/state').then(r=>r.json())).source==='atlas';
    assert.equal(report.atlas_restored,true);}}
  catch(error){report.status='FAIL';report.cleanup_error=String(error);process.exitCode=1;}
  await browser.close();fs.writeFileSync(bend?'docs/evidence/bend-case-download-ui.json':'docs/evidence/candidate-case-download-ui.json',JSON.stringify(report,null,2)+'\n');
 }
 console.log(JSON.stringify(report));
})().catch(error=>{console.error(error);process.exitCode=1});
