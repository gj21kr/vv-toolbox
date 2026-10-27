const {chromium}=require('playwright');
const fs=require('node:fs'),assert=require('node:assert/strict');
const render=process.argv.includes('--render');
const selection=process.argv.includes('--selection');
(async()=>{
 const browser=await chromium.connectOverCDP('http://127.0.0.1:9222');
 const page=await browser.contexts()[0].newPage();
 await page.bringToFront();
 page.setDefaultTimeout(60000);
 const base='http://127.0.0.1:8093',errors=[],rows=[];
 page.on('pageerror',e=>errors.push(e.message));
 const initial=await page.request.get(base+'/api/state').then(r=>r.json());
 assert.equal(initial.source,'atlas');
 assert.deepEqual(initial.atlas_modifications,{});
 assert.deepEqual(initial.atlas_interval_edits,{});
 try{
  await page.setViewportSize({width:1440,height:1100});
  await page.route('http://127.0.0.1:8094/**',r=>r.abort());
  await page.goto(base,{waitUntil:'domcontentloaded'});
  await page.waitForFunction(()=>state?.source==='atlas');
  fs.mkdirSync('exports/carotid-preview-ui',{recursive:true});
  for(const side of ['left','right']){
   const id=side+'-carotid-solid-union';
   await page.locator('#candidateSelect').selectOption(id);
   const switched=page.waitForResponse(r=>r.url().endsWith('/api/source')&&r.request().method()==='POST');
   await page.locator('#showCandidate').click();
   const response=await switched;
   assert([200,202].includes(response.status()),await response.text());
   await page.waitForFunction(id=>state?.source==='candidate'&&state?.candidate?.id===id,id);
   assert.match(await page.locator('#candidateChecks').innerText(),/단일 내강/);
   assert.match(await page.locator('#candidateChecks').innerText(),/미확인/);
   const selected=[];
   if(selection){
    const sources=await page.evaluate(()=>state.candidate.selectable_sources);
    assert.equal(sources.length,3);
    for(const source of sources){
     await page.locator('#candidateSource').selectOption(source.id);
     await page.waitForFunction(id=>state?.candidate?.selected_source===id,source.id);
     const info=await page.evaluate(()=>state.candidate.source_selection);
     assert(info.faces>0);assert(info.shared_vertices>0);
     selected.push({source:source.id,...info});
    }
    await page.locator('#candidateCard').screenshot({path:`exports/carotid-preview-ui/${side}-selection.png`});
    await page.locator('#candidateSource').selectOption('');
    await page.waitForFunction(()=>state.candidate.selected_source===null);
   }
   if(render){
    await page.unroute('http://127.0.0.1:8094/**');
    await page.locator('#stage iframe').evaluate(frame=>{frame.src=frame.src;});
    const frame=page.frameLocator('#stage iframe');
    await frame.locator('canvas').first().waitFor({state:'visible'});
    await frame.getByText(side==='left'?/좌측 경동맥/:/우측 경동맥/).first().waitFor({state:'visible'});
    await page.bringToFront();
    await frame.locator('canvas').first().evaluate(()=>new Promise(resolve=>{
      const timer=setTimeout(()=>resolve('frame wait timed out'),3000);
      requestAnimationFrame(()=>{clearTimeout(timer);resolve('frame');});
    }));
    await page.screenshot({path:`exports/carotid-preview-ui/${side}-render.png`});
   }else await page.locator('#candidateCard').screenshot({path:`exports/carotid-preview-ui/${side}.png`});
   rows.push({side,selected,viewer_visual:render?'SCREENSHOT_REQUIRES_INSPECTION':'NOT RUN',summary:await page.evaluate(()=>state.candidate)});
  }
  assert.deepEqual(errors,[]);
 } finally {
  if(render)await page.locator('#stage iframe').evaluateAll(frames=>frames.forEach(f=>f.remove()));
  const response=await page.request.post(base+'/api/source',{data:{source:'atlas'}});
  assert([200,202].includes(response.status()));
  for(let i=0;i<30;i++){
   const current=await page.request.get(base+'/api/state').then(r=>r.json());
   if(current.source==='atlas'&&!current.busy)break;
   await new Promise(r=>setTimeout(r,500));
  }
  assert.equal((await page.request.get(base+'/api/state').then(r=>r.json())).source,'atlas');
  await page.close();await browser.close();
 }
 fs.writeFileSync(`docs/evidence/carotid-preview-ui${render?'-render':''}${selection?'-selection':''}.json`,JSON.stringify({
  status:'PASS',rows,browser_errors:errors,atlas_restored:true,
  scope:render?'Candidate selection and actual Viser canvas screenshots':'Browser candidate selection and audit text; viewer requests blocked for focused controls test',
  viewer_visual:render?'SCREENSHOT_REQUIRES_INSPECTION':'NOT RUN'
 },null,2)+'\n');
 console.log(JSON.stringify({status:'PASS',sides:rows.map(r=>r.side),render}));
})().catch(e=>{console.error(e);process.exitCode=1});
