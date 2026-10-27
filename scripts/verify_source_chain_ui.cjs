const {chromium}=require('playwright');
const fs=require('node:fs'),assert=require('node:assert/strict');
const {execFileSync}=require('node:child_process');
(async()=>{
 const live=process.argv.includes('--live');
 const out=live?'exports/source-chain-live-ui':'exports/source-chain-ui',errors=[];
 fs.mkdirSync(out,{recursive:true});
 const report={status:'RUNNING',scope:live?'Actual demo HTTP split-source editing with synthetic fixture; not anatomical acceptance':'Synthetic split-source edit using isolated Docker request handler and controlled browser transport; not live Atlas acceptance'};
 const browser=await chromium.launch({headless:true});
 const page=await browser.newPage({acceptDownloads:true,viewport:{width:1280,height:1000}});
 page.on('pageerror',e=>errors.push(e.message));
 try{
  if(!live)await page.route('**/case-labels',route=>route.fulfill({contentType:'text/html',body:fs.readFileSync(out+'/workbench.html','utf8')}));
  if(!live)await page.route('**/api/case-labels',route=>{
   const body=execFileSync('docker',['exec','-i','-e','PYTHONPATH=src','-w','/workspace','vv-annotation-ui','python','scripts/workbench_request_stdio.py'],{input:route.request().postData(),encoding:'utf8',timeout:60000});
   return route.fulfill({contentType:'application/json',body});
  });
  await page.goto('http://127.0.0.1:8093/case-labels');
  await page.locator('#file').setInputFiles('exports/source-chain-ui/input.snapshot.json');
  await page.waitForFunction(()=>data&&!busy);
  await page.locator('#shapePanel summary').click();
  assert.match(await page.locator('#shapeEligibility').innerText(),/2개: e, e2/);
  assert(await page.locator('#shape').isEnabled());
  const before=await page.evaluate(()=>data.snapshot);
  await page.locator('#shapeBend').fill('0.1');await page.locator('#shapeTwist').fill('0');
  await page.locator('#shapeCollar').fill('0.1');await page.locator('#shapeTransition').fill('1');
  await page.locator('#shape').click();
  await page.waitForFunction(rev=>!busy&&data.snapshot.revision!==rev,before.revision);
  const edited=await page.evaluate(()=>data.snapshot);
  assert.deepEqual(edited.case.nodes,before.case.nodes);
  assert.equal(edited.case.inspection.registered_shape_edit.checked_paths.length,2);
  assert.deepEqual(edited.case.inspection.registered_shape_edit.audit.affected_edge_ids,['e','e2']);
  await page.locator('#undo').click();assert.equal(await page.evaluate(()=>data.snapshot.revision),before.revision);
  await page.locator('#redo').click();assert.equal(await page.evaluate(()=>data.snapshot.revision),edited.revision);
  const download=page.waitForEvent('download');await page.locator('#download').click();
  await (await download).saveAs(out+'/result.snapshot.json');
  assert.deepEqual(JSON.parse(fs.readFileSync(out+'/result.snapshot.json')),edited);
  await page.locator('#shapePanel').screenshot({path:out+'/controls.png'});
  assert.deepEqual(errors,[]);
  Object.assign(report,{status:'PASS',affected_edges:['e','e2'],nodes_preserved:true,undo_redo:true,download_match:true,browser_errors:errors,visual_review:'NOT RUN'});
 }catch(e){report.status='FAIL';report.error=String(e);process.exitCode=1;}
 finally{await browser.close();fs.writeFileSync(live?'docs/evidence/source-chain-live-ui.json':'docs/evidence/source-chain-ui.json',JSON.stringify(report,null,2)+'\n');}
 console.log(JSON.stringify(report));
})().catch(e=>{console.error(e);process.exitCode=1});
