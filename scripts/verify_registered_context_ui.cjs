const {chromium}=require('playwright');
const fs=require('node:fs'),assert=require('node:assert/strict');
(async()=>{
 const out='exports/registered-context-ui';fs.mkdirSync(out,{recursive:true});
 const browser=await chromium.launch({headless:true});
 const page=await browser.newPage({acceptDownloads:true,viewport:{width:1280,height:1000}});
 page.setDefaultTimeout(60000);
 const errors=[],report={status:'RUNNING',scope:'Exact-case stored contact inspection import, undo/redo and download',browser_path:'Playwright: Browser plugin not available'};
 page.on('pageerror',e=>errors.push(e.message));
 try{
  const base='http://127.0.0.1:8093';
  const before=await page.request.get(base+'/api/state').then(r=>r.json());
  await page.goto(base+'/case-labels');
  await page.locator('#file').setInputFiles('exports/registered-shape-case/case.snapshot.json');
  await page.waitForFunction(()=>data?.edges.length===65&&!busy);
  const prior=await page.evaluate(()=>data.snapshot.revision);
  await page.locator('#shapePanel summary').click();await page.locator('#shapeContext').click();
  await page.waitForFunction(()=>!busy&&data?.snapshot.case.inspection.registered_shape_edit.context_binding);
  assert.match(await page.locator('#savedInspection').innerText(),/FAIL/);
  assert.match(await page.locator('#status').innerText(),/788/);
  assert.match(await page.locator('#status').innerText(),/새 검사 실행은 아닙니다/);
  const doc=await page.evaluate(()=>data.snapshot);
  assert.equal(doc.case.inspection.registered_shape_edit.context.rows.length,788);
  assert.equal(doc.case.inspection.registered_shape_edit.accepted_for_generation,false);
  await page.locator('#undo').click();assert.equal(await page.evaluate(()=>data.snapshot.revision),prior);
  await page.locator('#redo').click();assert.equal(await page.evaluate(()=>data.snapshot.revision),doc.revision);
  const waiting=page.waitForEvent('download');await page.locator('#download').click();
  await (await waiting).saveAs(out+'/case.snapshot.json');
  assert.deepEqual(JSON.parse(fs.readFileSync(out+'/case.snapshot.json')),doc);
  await page.locator('#savedInspection').screenshot({path:out+'/status.png'});
  const after=await page.request.get(base+'/api/state').then(r=>r.json());
  assert.equal(after.generation,before.generation);assert.equal(after.source,before.source);assert.deepEqual(errors,[]);
  Object.assign(report,{status:'PASS',revision:doc.revision,context_status:'FAIL',rows:788,undo_redo:true,
   atlas_unchanged:true,browser_errors:errors,visual_review:'NOT RUN'});
 }catch(e){report.status='FAIL';report.error=String(e);process.exitCode=1;}
 finally{await browser.close();fs.writeFileSync('docs/evidence/registered-context-ui.json',JSON.stringify(report,null,2)+'\n');}
 console.log(JSON.stringify(report));
})().catch(e=>{console.error(e);process.exitCode=1});
