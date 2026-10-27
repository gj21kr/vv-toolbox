const {chromium}=require('playwright');
const fs=require('node:fs'),assert=require('node:assert/strict');
(async()=>{
 const priorRun=JSON.parse(fs.readFileSync('docs/evidence/registered-context-fresh.json'));
 assert(['PASS','FAIL','UNKNOWN'].includes(priorRun.status),'Wait for the existing CLI inspection to finish');
 const out='exports/full-context-job-ui';fs.mkdirSync(out,{recursive:true});
 const report={status:'RUNNING',scope:'Actual 788-neighbor UI inspection, reload/resume and saved result comparison',
  browser_path:'Playwright: Browser plugin not available'};
 const record=()=>fs.writeFileSync('docs/evidence/full-context-job-ui.json',JSON.stringify(report,null,2)+'\n');record();
 const browser=await chromium.launch({headless:true});
 const page=await browser.newPage({acceptDownloads:true,viewport:{width:1280,height:1000}});
 page.setDefaultTimeout(1800000);
 const errors=[];let starts=0;page.on('pageerror',e=>errors.push(e.message));page.on('dialog',d=>d.accept());
 page.on('request',r=>{if(r.method()==='POST'&&r.url().endsWith('/api/case-context-jobs'))starts++;});
 try{
  const base='http://127.0.0.1:8093';
  const before=await page.request.get(base+'/api/state').then(r=>r.json());
  const open=async()=>{
   await page.locator('#file').setInputFiles('exports/registered-shape-case/case.snapshot.json');
   await page.waitForFunction(()=>data?.edges.length===65&&!busy);
   await page.locator('#shapePanel summary').click();await page.locator('#shapeContextRun').click();
  };
  await page.goto(base+'/case-labels');await open();
  await page.waitForFunction(()=>sessionStorage.getItem('vv-context-job'));
  const job=await page.evaluate(()=>JSON.parse(sessionStorage.getItem('vv-context-job')));
  report.job_id=job.id;record();
  assert(await page.locator('#file').isDisabled());
  await page.reload({waitUntil:'domcontentloaded'});await open();
  await page.waitForFunction(()=>busy);
  assert.equal(await page.evaluate(()=>JSON.parse(sessionStorage.getItem('vv-context-job')).id),job.id);
  assert.equal(starts,1);report.reload_resumed_without_duplicate=true;record();
  const deadline=Date.now()+1800000;let status;
  while(Date.now()<deadline){
   status=await page.request.get(base+'/api/case-context-jobs/'+job.id).then(r=>r.json());
   Object.assign(report,{job_state:status.state,completed:status.completed,total:status.total});record();
   if(status.state!=='RUNNING')break;
   await page.waitForTimeout(15000);
  }
  assert.equal(status.state,'COMPLETE');assert.equal(status.total,788);
  await page.waitForFunction(()=>!busy&&document.querySelector('#contextProgress').textContent.includes('검사 완료'));
  assert.match(await page.locator('#savedInspection').innerText(),new RegExp(priorRun.status));
  const document=await page.evaluate(()=>data.snapshot);
  const waiting=page.waitForEvent('download');await page.locator('#download').click();
  await (await waiting).saveAs(out+'/case.snapshot.json');
  assert.deepEqual(JSON.parse(fs.readFileSync(out+'/case.snapshot.json')),document);
  assert.deepEqual(document,JSON.parse(fs.readFileSync('exports/registered-context-fresh/case.snapshot.json')));
  await page.locator('#contextProgress').screenshot({path:out+'/complete.png'});
  await page.locator('#savedInspection').screenshot({path:out+'/inspection.png'});
  const after=await page.request.get(base+'/api/state').then(r=>r.json());
  assert.equal(after.source,before.source);assert.equal(after.generation,before.generation);assert.deepEqual(errors,[]);
  Object.assign(report,{status:'PASS',inspection_status:status.inspection_status,revision:document.revision,
   exact_cli_case_match:true,post_count:starts,atlas_unchanged:true,browser_errors:errors,visual_review:'NOT RUN'});
 }catch(e){report.status='FAIL';report.error=String(e);process.exitCode=1;}
 finally{await browser.close();record();}
 console.log(JSON.stringify(report));
})().catch(e=>{console.error(e);process.exitCode=1});
