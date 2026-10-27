const {chromium}=require('playwright');
const fs=require('node:fs'),assert=require('node:assert/strict');
(async()=>{
 const out='exports/context-job-ui',input=JSON.parse(fs.readFileSync(out+'/input.snapshot.json'));
 const result=fs.readFileSync(out+'/result.snapshot.json','utf8');
 const browser=await chromium.launch({headless:true});
 const page=await browser.newPage({acceptDownloads:true,viewport:{width:1280,height:1000}});
 page.setDefaultTimeout(30000);
 const report={status:'RUNNING',scope:'Controlled job transport with real synthetic numerical result; not full Atlas asynchronous completion',browser_path:'Playwright: Browser plugin not available'};
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 let starts=0,polls=0,mode='complete';
 const state=()=>({id:'test-job',case_revision:mode==='mismatch'?'wrong':input.revision,
  state:polls>=2?'COMPLETE':'RUNNING',completed:polls>=2?1:0,total:1});
 try{
  await page.route('**/api/case-context-jobs**',async route=>{
   const url=route.request().url();
   if(route.request().method()==='POST'){
    starts++;assert.equal(JSON.parse(route.request().postDataJSON().snapshot).revision,input.revision);
    return route.fulfill({status:202,json:state()});}
   if(url.endsWith('/result'))return route.fulfill({status:200,contentType:'application/json',body:result});
   polls++;return route.fulfill({status:200,json:state()});
  });
  await page.goto('http://127.0.0.1:8093/case-labels');
  await page.locator('#file').setInputFiles(out+'/input.snapshot.json');
  await page.waitForFunction(()=>data&&!busy);
  await page.locator('#shapePanel summary').click();
  await page.locator('#shapeContextRun').click();
  await page.waitForFunction(()=>document.querySelector('#contextProgress').textContent.includes('0/1'));
  assert(await page.locator('#file').isDisabled());assert(await page.locator('#shapeContextRun').isDisabled());
  await page.locator('#contextProgress').screenshot({path:out+'/progress.png'});
  await page.waitForFunction(()=>!busy&&document.querySelector('#contextProgress').textContent.includes('검사 완료'));
  assert.equal(starts,1);assert.equal(await page.evaluate(()=>data.snapshot.revision),JSON.parse(result).revision);
  await page.locator('#contextProgress').screenshot({path:out+'/complete.png'});
  await page.locator('#undo').click();assert.equal(await page.evaluate(()=>data.snapshot.revision),input.revision);
  await page.evaluate(revision=>sessionStorage.setItem('vv-context-job',JSON.stringify({id:'test-job',revision})),input.revision);
  await page.locator('#shapeContextRun').click();
  await page.waitForFunction(revision=>!busy&&data.snapshot.revision===revision,JSON.parse(result).revision);
  assert.equal(starts,1,'Resume must not submit another job');
  await page.locator('#undo').click();mode='mismatch';polls=2;
  await page.locator('#shapeContextRun').click();
  await page.waitForFunction(()=>!busy&&document.querySelector('#contextProgress').textContent.includes('달라졌습니다'));
  assert.equal(await page.evaluate(()=>data.snapshot.revision),input.revision);
  assert.deepEqual(errors,[]);
  Object.assign(report,{status:'PASS',progress:true,inputs_locked:true,completed_applied:true,resume_without_duplicate:true,
    wrong_revision_rejected:true,browser_errors:errors,visual_review:'NOT RUN'});
 }catch(e){report.status='FAIL';report.error=String(e);process.exitCode=1;}
 finally{await browser.close();fs.writeFileSync('docs/evidence/context-job-ui.json',JSON.stringify(report,null,2)+'\n');}
 console.log(JSON.stringify(report));
})().catch(e=>{console.error(e);process.exitCode=1});
