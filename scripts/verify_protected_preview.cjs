const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const crypto=require('node:crypto');
(async()=>{
 const filename='reference-data/bodyparts3d/atlas-edits.snapshot.json';
 const hash=()=>crypto.createHash('sha256').update(fs.readFileSync(filename)).digest('hex');
 const before=hash(),errors=[];
 const failedTransitions=[];
 const browser=await chromium.connectOverCDP('http://127.0.0.1:9222');
 const page=await browser.contexts()[0].newPage();
 page.setDefaultTimeout(120000);
 page.on('pageerror',e=>errors.push(e.message));
 page.on('response',r=>{if(r.url().endsWith('/api/source')&&!r.ok())failedTransitions.push(r.status());});
 fs.mkdirSync('exports/protected-preview',{recursive:true});
 try{
  await page.setViewportSize({width:1560,height:1000});
  const initial=await page.request.get('http://127.0.0.1:8093/api/state').then(r=>r.json());
  const prepare=await page.request.post('http://127.0.0.1:8093/api/source',{data:{source:'candidate',candidate_id:'cerebral-protected-fit'}});
  assert(prepare.ok());
  await page.goto('http://127.0.0.1:8093/');
  await page.waitForFunction(()=>typeof state!=='undefined'&&state?.source==='candidate'&&!state.busy,{},{timeout:120000});
  await page.locator('#candidateSelect').selectOption('cerebral-protected-fit');
  await page.locator('#showCandidate').click();
  await page.waitForFunction(()=>state?.candidate?.id==='cerebral-protected-fit'&&!pending);
  assert(await page.locator('#candidateView').isHidden());
  assert((await page.locator('#candidateChecks').innerText()).includes('4108'));
  const candidate=await page.request.get('http://127.0.0.1:8093/api/state').then(r=>r.json());
  assert.equal(candidate.candidate.protected_comparison.parts,8);
  const frame=page.frameLocator('#stage iframe');
  await frame.locator('canvas').first().waitFor({state:'visible'});
  await page.screenshot({path:'exports/protected-preview/candidate.png'});
  const reject=await page.request.post('http://127.0.0.1:8093/api/atlas-modification',{data:{}});
  assert.equal(reject.status(),400);
  await page.locator('#protectedCompare').click();
  await page.waitForFunction(()=>state?.candidate?.id==='cerebral-protected-reference'&&!pending);
  assert((await page.locator('#candidateScope').innerText()).includes('원본'));
  assert.equal(await page.locator('#sourceBadge').innerText(),'읽기 전용 원본');
  await page.screenshot({path:'exports/protected-preview/reference.png'});
  await page.locator('#protectedCompare').click();
  await page.waitForFunction(()=>state?.candidate?.id==='cerebral-protected-fit'&&!pending);
  await page.setViewportSize({width:390,height:844});
  await page.locator('#protectedCompare').scrollIntoViewIfNeeded();
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await page.locator('#candidateReturn').click();
  await page.waitForFunction(()=>state?.source==='atlas'&&!pending);
  const restored=await page.request.get('http://127.0.0.1:8093/api/state').then(r=>r.json());
  assert.deepEqual(restored.atlas_modifications,initial.atlas_modifications);
  assert.equal(hash(),before);assert.deepEqual(errors,[]);assert.deepEqual(failedTransitions,[]);
  const report={status:'PASS',browser_path:'Browser plugin not available; Playwright CDP',
   checks:['eight surfaces loaded','read-only modification rejected','source/candidate toggle both directions',
    'surface-only controls','mobile no horizontal overflow','Atlas return preserves modifications','snapshot unchanged'],
   candidate:candidate.candidate,page_errors:errors,atlas_snapshot_sha256:before};
  fs.writeFileSync('docs/evidence/protected-preview-browser.json',JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify({status:report.status,checks:report.checks}));
 }finally{await page.close();await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1});
