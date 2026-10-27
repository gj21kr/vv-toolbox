const {chromium}=require('playwright');
const fs=require('node:fs'),assert=require('node:assert/strict');
(async()=>{
 const out='exports/registered-shape-ui';fs.mkdirSync(out,{recursive:true});
 const browser=await chromium.launch({headless:true});
 const page=await browser.newPage({acceptDownloads:true,viewport:{width:1280,height:1000}});
 page.setDefaultTimeout(300000);
 const errors=[],report={status:'RUNNING',scope:'Actual registered wall/graph UI edit, failure preservation, undo/redo and download',
  browser_path:'Playwright: Browser plugin not available'};
 const record=()=>fs.writeFileSync('docs/evidence/registered-shape-ui.json',JSON.stringify(report,null,2)+'\n');
 record();page.on('pageerror',e=>errors.push(e.message));
 try{
  const before=await page.request.get('http://127.0.0.1:8093/api/state').then(r=>r.json());
  await page.goto('http://127.0.0.1:8093/case-labels');
  await page.locator('#file').setInputFiles('exports/candidate-case-download/case.snapshot.json');
  await page.waitForFunction(()=>data?.edges.length===65&&!busy);
  await page.locator('#search').fill('FJ2074');await page.locator('#shapePanel summary').click();
  const prior=await page.evaluate(()=>data.snapshot.revision);
  await page.locator('#shapeBend').fill('1000');await page.locator('#shape').click();
  await page.waitForFunction(()=>!busy&&document.querySelector('#status').textContent.includes('현재 사례와 편집 이력'));
  assert.equal(await page.evaluate(()=>data.snapshot.revision),prior);
  assert.equal(await page.evaluate(()=>undoStack.length),0);
  assert.match(await page.locator('#status').innerText(),/displacement bound/);
  await page.locator('#shapeBend').fill('0.25');await page.locator('#shape').click();
  await page.waitForFunction(()=>busy);
  assert(await page.locator('#shapeBend').isDisabled());assert(await page.locator('#file').isDisabled());
  Object.assign(report,{failure_preserved:true,busy_controls_locked:true});record();
  await page.waitForFunction(prior=>!busy&&data.snapshot.revision!==prior,prior);
  const edited=await page.evaluate(()=>data.snapshot);
  assert.equal(edited.case.inspection.registered_shape_edit.checked_paths.length,65);
  assert.equal(edited.case.inspection.registered_shape_edit.accepted_for_generation,false);
  assert.match(await page.locator('#savedInspection').innerText(),/NOT RUN/);
  await page.locator('#undo').click();assert.equal(await page.evaluate(()=>data.snapshot.revision),prior);
  await page.locator('#redo').click();assert.equal(await page.evaluate(()=>data.snapshot.revision),edited.revision);
  const waiting=page.waitForEvent('download');await page.locator('#download').click();
  await (await waiting).saveAs(out+'/case.snapshot.json');
  const saved=JSON.parse(fs.readFileSync(out+'/case.snapshot.json'));
  assert.deepEqual(saved,edited);
  assert.deepEqual(saved,JSON.parse(fs.readFileSync('exports/registered-shape-case/case.snapshot.json')));
  await page.locator('#shapePanel').screenshot({path:out+'/controls.png'});
  await page.locator('#preview').screenshot({path:out+'/surface.png'});
  const after=await page.request.get('http://127.0.0.1:8093/api/state').then(r=>r.json());
  assert.equal(after.source,before.source);assert.equal(after.generation,before.generation);assert.deepEqual(errors,[]);
  Object.assign(report,{status:'PASS',revision:saved.revision,independent_run_equal:true,
   undo_redo:true,atlas_unchanged:true,browser_errors:errors,visual_review:'NOT RUN'});
 }catch(e){report.status='FAIL';report.error=String(e);process.exitCode=1;}
 finally{await browser.close();record();}
 console.log(JSON.stringify(report));
})().catch(e=>{console.error(e);process.exitCode=1});
