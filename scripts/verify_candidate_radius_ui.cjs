const {chromium}=require('playwright');
const fs=require('node:fs'),assert=require('node:assert/strict');
const save=process.argv.includes('--save');
const context=process.argv.includes('--context');
(async()=>{
 const browser=await chromium.connectOverCDP('http://127.0.0.1:9222');
 const page=await browser.contexts()[0].newPage();
 const base='http://127.0.0.1:8093',errors=[],rows=[];
 page.setDefaultTimeout(60000);
 page.on('pageerror',e=>errors.push(e.message));
 try{
  const initial=await page.request.get(base+'/api/state').then(r=>r.json());
  assert.equal(initial.source,'atlas');assert.equal(initial.busy,false);
  await page.setViewportSize({width:1440,height:1100});
  // This test verifies controls, not the separate Viser renderer.
  await page.route('http://127.0.0.1:8094/**',r=>r.abort());
  await page.goto(base,{waitUntil:'domcontentloaded'});
  await page.waitForFunction(()=>state?.source==='atlas');
  assert.equal(new URL(page.url()).port,'8093');
  assert.match(await page.title(),/VV Toolbox/);
  fs.mkdirSync('exports/candidate-radius-ui',{recursive:true});
  for(const side of (save||process.argv.includes('--left')?['left']:['left','right'])){
   await page.locator('#candidateSelect').selectOption(side+'-carotid-solid-union');
   await page.locator('#showCandidate').click();
   await page.waitForFunction(id=>state?.candidate?.id===id&&state.source==='candidate',side+'-carotid-solid-union');
   const original=await page.evaluate(()=>state.candidate.surface_sha256);
   const source='estimated_'+side+'_carotid_neck';
   await page.locator('#candidateSource').selectOption(source);
   await page.waitForFunction(id=>state.candidate.selected_source===id,source);
   const response=page.waitForResponse(r=>r.url().endsWith('/api/candidate-radius-preview'),{timeout:context?900000:180000});
   await page.locator('#candidateRadiusPreview').click();
   assert.equal((await response).status(),200);
   await page.waitForFunction(()=>!!state.candidate_radius?.preview_token);
   assert.match(await page.locator('#candidateRadiusStatus').innerText(),/미리보기 표시 중/);
   assert.match(await page.locator('#candidateChecks').innerText(),/재검사 필요/);
   assert.equal(await page.locator('#candidateReturn').isDisabled(),true);
   await page.locator('#candidateCard').screenshot({path:`exports/candidate-radius-ui/${side}-preview.png`});
   if(context){
    const audit=await page.evaluate(()=>state.candidate.radius_edit);
    assert(audit.neighbor_context.neighbors>0);
    assert.equal(await page.locator('#candidateRadiusApply').isDisabled(),audit.neighbor_contact!=='PASS');
    if(audit.neighbor_contact!=='PASS'){
     const rejected=await page.request.post(base+'/api/candidate-radius-action',{
      headers:{'X-Expected-Generation':String(await page.evaluate(()=>state.generation))},
      data:{action:'apply',token:await page.evaluate(()=>state.candidate_radius.preview_token)}});
     assert.equal(rejected.status(),400);
    }
    rows.push({side,audit});
    await page.locator('#candidateCard').screenshot({path:`exports/candidate-radius-ui/${side}-context.png`});
    await page.locator('#candidateRadiusDiscard').click();
    await page.waitForFunction(()=>!state.candidate_radius?.preview_token&&!radiusPending);
    assert.equal(await page.evaluate(()=>state.candidate.surface_sha256),original);
    await page.locator('#candidateReturn').click();
    await page.waitForFunction(()=>state.source==='atlas');
    continue;
   }
   if(side==='left'&&!save){
    await page.locator('#candidateRadiusDiscard').click();
    await page.waitForFunction(()=>!state.candidate_radius?.preview_token&&!radiusPending);
    assert.equal(await page.evaluate(()=>state.candidate.surface_sha256),original);
    await page.locator('#candidateSource').selectOption(source);
    await page.waitForFunction(id=>state.candidate.selected_source===id,source);
    const again=page.waitForResponse(r=>r.url().endsWith('/api/candidate-radius-preview'),{timeout:180000});
    await page.locator('#candidateRadiusPreview').click();assert.equal((await again).status(),200);
    await page.waitForFunction(()=>!!state.candidate_radius?.preview_token&&!radiusPending);
   }
   await page.locator('#candidateRadiusApply').click();
   await page.waitForFunction(()=>state.candidate_radius?.undo_available&&!state.candidate_radius?.preview_token&&!radiusPending);
   assert.match(await page.locator('#candidateRadiusStatus').innerText(),/적용됨/);
   rows.push({side,edit:await page.evaluate(()=>state.candidate.radius_edit)});
   let savedPath,savedHash;
   if(save){
    savedHash=await page.evaluate(()=>state.candidate.geometry_sha256);
    const download=page.waitForEvent('download');
    await page.locator('#candidateRadiusSave').click();
    savedPath='exports/candidate-radius-ui/saved-radius.json';
    await (await download).saveAs(savedPath);
    assert.equal(JSON.parse(fs.readFileSync(savedPath,'utf8')).payload.operations.length,1);
   }
   await page.locator('#candidateRadiusUndo').click();
   await page.waitForFunction(()=>!state.candidate_radius?.undo_available&&!radiusPending);
   assert.equal(await page.evaluate(()=>state.candidate.surface_sha256),original);
   if(save){
    const corrupt=JSON.parse(fs.readFileSync(savedPath,'utf8'));corrupt.sha256='wrong';
    const rejected=await page.request.post(base+'/api/candidate-radius-restore',{
     headers:{'X-Expected-Generation':String(await page.evaluate(()=>state.generation))},
     data:{session_text:JSON.stringify(corrupt)}});
    assert.equal(rejected.status(),400);
    assert.equal((await page.request.get(base+'/api/state').then(r=>r.json())).candidate.surface_sha256,original);
    const restored=page.waitForResponse(r=>r.url().endsWith('/api/candidate-radius-restore'),{timeout:180000});
    await page.locator('#candidateRadiusFile').setInputFiles(savedPath);
    assert.equal((await restored).status(),200);
    await page.waitForFunction(()=>state.candidate_radius?.undo_available&&!radiusPending);
    assert.equal(await page.evaluate(()=>state.candidate.geometry_sha256),savedHash);
    await page.locator('#candidateCard').screenshot({path:'exports/candidate-radius-ui/restored.png'});
    rows[rows.length-1].reloaded_geometry_sha256=savedHash;
    await page.locator('#candidateRadiusUndo').click();
    await page.waitForFunction(()=>!state.candidate_radius?.undo_available&&!radiusPending);
    assert.equal(await page.evaluate(()=>state.candidate.surface_sha256),original);
   }
   await page.locator('#candidateReturn').click();
   await page.waitForFunction(()=>state.source==='atlas');
  }
  assert.deepEqual(errors,[]);
  fs.writeFileSync(context?'docs/evidence/candidate-radius-context-ui.json':save?'docs/evidence/candidate-radius-save-ui.json':'docs/evidence/candidate-radius-ui.json',JSON.stringify({
   status:'PASS',browser:'Playwright; Browser plugin not available',rows,
   original_restored:true,controls:'PASS',viser_visual:'NOT RUN',page_errors:errors},null,2)+'\n');
 }finally{
  await page.close();await browser.close();
 }
})().catch(e=>{console.error(e);process.exitCode=1});
