const {chromium}=require('playwright');
const fs=require('node:fs'),assert=require('node:assert/strict');
const resampled=process.argv.includes('--resampled');
const graph=resampled||process.argv.includes('--graph');
const candidateId=resampled?'resampled-access-protected':'femoral-anterior-solid-union';
(async()=>{
 const browser=await chromium.launch({headless:true});
 const page=await browser.newPage();
 const base='http://127.0.0.1:8093',errors=[];
 const output=resampled?'exports/resampled-access-ui':graph?'exports/access-graph-ui':'exports/access-union-ui';
 fs.mkdirSync(output,{recursive:true});
 page.setDefaultTimeout(60000);
 page.on('pageerror',e=>errors.push(e.message));
 let summary,selection;
 try {
  const initial=await page.request.get(base+'/api/state').then(r=>r.json());
  assert.equal(initial.source,'atlas');
  assert.deepEqual(initial.atlas_modifications,{});
  assert.deepEqual(initial.atlas_interval_edits,{});
  await page.setViewportSize({width:1440,height:1100});
  await page.route('http://127.0.0.1:8094/**',r=>r.abort());
  await page.goto(base,{waitUntil:'domcontentloaded'});
  console.log('Controls loaded');
  await page.waitForFunction(()=>state?.source==='atlas');
  await page.locator('#candidateSelect').selectOption(candidateId);
  await page.locator('#showCandidate').click();
  await page.waitForFunction(id=>state?.source==='candidate'&&state.candidate.id===id,candidateId);
  console.log('Candidate selected');
  assert.match(await page.locator('#candidateChecks').innerText(),/22개 원본 부분/);
  assert.match(await page.locator('#candidateChecks').innerText(),/미확인/);
  assert.equal(await page.locator('#candidateRadius').isVisible(),resampled);
  if(resampled){
   await page.locator('#candidateSource').selectOption('FJ2074');
   await page.waitForFunction(()=>state.candidate.selected_source==='FJ2074');
   assert.equal(await page.locator('#candidateRadiusPreview').isEnabled(),true);
   assert.equal(await page.locator('#candidateRadiusApply').isEnabled(),false);
   await page.locator('#candidateRadius').scrollIntoViewIfNeeded();
   await page.locator('#candidateRadius').screenshot({path:output+'/radius-controls.png'});
   await page.locator('#candidateSource').selectOption('FJ1931');
   await page.waitForFunction(()=>state.candidate.selected_source==='FJ1931');
   assert.equal(await page.locator('#candidateRadiusPreview').isEnabled(),false);
   assert.match(await page.locator('#candidateRadiusStatus').innerText(),/분지 경로 지정/);
  }
  await page.locator('#candidateSource').selectOption('FJ3411');
  await page.waitForFunction(()=>state.candidate.selected_source==='FJ3411');
  selection=await page.evaluate(()=>state.candidate.source_selection);
  assert(selection.faces>0);
  await page.locator('#candidateSource').selectOption('');
  await page.waitForFunction(()=>state.candidate.selected_source===null);
  summary=await page.evaluate(()=>state.candidate);
  if(resampled){
   assert.equal(summary.triangles,50188);
   assert.equal(summary.read_only,true);
   assert.equal(summary.access_union.checked_paths,65);
   assert.match(await page.locator('#candidateChecks').innerText(),new RegExp(`${summary.access_union.context_completed}/${summary.access_union.context_neighbors}`));
  }
  if(graph){
   assert.equal(summary.access_graph.nodes,65);assert.equal(summary.access_graph.edges,65);
   assert.equal(summary.access_graph.routes.length,8);
   assert(summary.access_graph.routes.every(r=>r.status==='UNKNOWN'&&r.edge_count>0));
   await page.locator('#candidateRoutes summary').click();
   assert.equal(await page.locator('#candidateRoutes span').count(),36);
  }
  await page.unroute('http://127.0.0.1:8094/**');
  await page.locator('#stage iframe').evaluate(frame=>{frame.src=frame.src;});
  const canvas=page.frameLocator('#stage iframe').locator('canvas').first();
  await canvas.waitFor({state:'visible'});
  await canvas.evaluate(()=>new Promise(resolve=>setTimeout(resolve,3000)));
  await page.locator('#candidateCard').screenshot({path:output+'/controls.png'});
  await page.locator('#stage').screenshot({path:output+'/render.png'});
  if(graph){
   await page.locator('#candidateView').click();
   await page.waitForFunction(()=>state.mode==='Centerlines');
   assert.equal(await page.locator('#candidateSource').isDisabled(),true);
   await canvas.evaluate(()=>new Promise(resolve=>setTimeout(resolve,1500)));
   await page.locator('#stage').screenshot({path:output+'/centerlines.png'});
   await page.locator('#candidateView').click();
   await page.waitForFunction(()=>state.mode==='Surface');
  }
  assert.deepEqual(errors,[]);
 } finally {
  try {
   await page.locator('#stage iframe').evaluateAll(frames=>frames.forEach(frame=>frame.remove()));
   await page.request.post(base+'/api/source',{data:{source:'atlas'}});
   assert.equal((await page.request.get(base+'/api/state').then(r=>r.json())).source,'atlas');
  } finally { await browser.close(); }
 }
 fs.writeFileSync(resampled?'docs/evidence/resampled-access-ui.json':graph?'docs/evidence/access-graph-ui.json':'docs/evidence/access-union-ui.json',JSON.stringify({
  status:'PASS',scope:'Actual candidate controls, source selection and Viser canvas capture',
  summary,selection,browser_errors:errors,atlas_restored:true,
  radius_request_roundtrip:resampled?'NOT RUN':'NOT APPLICABLE',
  viewer_visual:'SCREENSHOT_REQUIRES_INSPECTION'},null,2)+'\n');
 console.log(JSON.stringify({status:'PASS',triangles:summary.triangles,selection}));
})().catch(e=>{console.error(e);process.exitCode=1});
