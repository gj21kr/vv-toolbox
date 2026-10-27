const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const crypto=require('node:crypto');
(async()=>{
 const atlasFile='reference-data/bodyparts3d/atlas-edits.snapshot.json';
 const hash=()=>crypto.createHash('sha256').update(fs.readFileSync(atlasFile)).digest('hex');
 const before=hash(),errors=[],results=[];
 const browser=await chromium.connectOverCDP('http://127.0.0.1:9222');
 const page=await browser.contexts()[0].newPage();
 page.on('pageerror',e=>errors.push(e.message));
 async function check(){
  const response=page.waitForResponse(r=>r.url().endsWith('/api/case-labels')&&r.request().method()==='POST');
  await page.locator('#containment').click();
  const r=await response;assert.equal(r.status(),200);
  const report=(await r.json()).inspection;results.push(report);
  await page.waitForFunction(()=>!document.querySelector('#containment').disabled);
  assert((await page.locator('#containmentResult').innerText()).startsWith(report.status));
  return report;
 }
 try{
  await page.setViewportSize({width:1280,height:1000});
  await page.goto('http://127.0.0.1:8093/case-labels');
  assert(await page.locator('#containment').isDisabled());
  await page.locator('#file').setInputFiles('exports/label-workbench/smoothing.snapshot.json');
  await page.waitForFunction(()=>!document.querySelector('#search').disabled);
  assert.equal((await check()).status,'UNKNOWN');
  await page.locator('#file').setInputFiles('exports/atlas-case-inspection/all-arterial.snapshot.json');
  await page.waitForFunction(()=>document.querySelector('#status').textContent.includes('1081 edges'));
  await page.locator('#search').fill('FJ1692:e0');
  await page.locator('#edge').selectOption('FJ1692:e0');
  const original=await check();assert.equal(original.status,'PASS');
  assert.equal(original.source_part_id,'FJ1692');
  await page.locator('summary').filter({hasText:'Modify selected centerline'}).click();
  await page.locator('#smooth').click();
  await page.waitForFunction(()=>document.querySelector('#status').textContent.includes('Synthetic copy created'));
  assert((await page.locator('#containmentResult').innerText()).startsWith('NOT RUN'));
  const modified=await check();assert.equal(modified.status,'PASS');
  assert.notEqual(original.case_revision,modified.case_revision);
  await page.locator('#containment').scrollIntoViewIfNeeded();
  await page.screenshot({path:'exports/label-workbench/containment.png'});
  await page.locator('#undo').click();
  assert((await page.locator('#containmentResult').innerText()).startsWith('NOT RUN'));
  await page.locator('#search').fill('FJ1654:e0');
  await page.locator('#edge').selectOption('FJ1654:e0');
  assert((await page.locator('#containmentResult').innerText()).startsWith('NOT RUN'));
  await page.setViewportSize({width:390,height:844});
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  assert.deepEqual(errors,[]);assert.equal(hash(),before);
  const report={status:'PASS',browser_path:'Browser plugin not available; Playwright CDP',
   checks:['disabled without case','unbound fixture UNKNOWN','native source PASS',
    'smoothing invalidates result','smoothed centerline PASS at new revision',
    'undo and selection invalidate result','mobile no horizontal overflow','Atlas file unchanged'],
   page_errors:errors,atlas_edit_sha256:before,results};
  fs.writeFileSync('docs/evidence/workbench-containment-browser.json',JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify({status:report.status,checks:report.checks}));
 }finally{await page.close();await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1});
