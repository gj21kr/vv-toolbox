const {chromium}=require('playwright');
const fs=require('node:fs'),assert=require('node:assert/strict');
(async()=>{
 const live=process.argv.includes('--live');
 const out=live?'exports/language-live-ui':'exports/language-ui',base='http://127.0.0.1:8093';
 fs.mkdirSync(out,{recursive:true});
 const browser=await chromium.launch({headless:true});
 const context=await browser.newContext({viewport:{width:1280,height:1000},locale:'en-US'});
 const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
 page.setDefaultTimeout(60000);page.on('dialog',dialog=>dialog.accept());
 const report={status:'RUNNING',scope:live?'Actual demo language toolbar, initial copy and persistence; dynamic copy coverage is separate':'Language toolbar and initial page copy with local current assets; dynamic copy coverage is separate'};
 try{
  if(!live)for(const [path,file]of [['/','main.html'],['/case-labels','workbench.html'],['/ui-language.js','language.js']])
   await context.route(base+path,r=>r.fulfill({contentType:file.endsWith('.js')?'application/javascript':'text/html',body:fs.readFileSync(out+'/'+file,'utf8')}));
  await page.goto(base+'/case-labels');
  await page.locator('#vv-language [data-language=ko]').click();
  assert.equal(await page.locator('html').getAttribute('lang'),'ko');
  assert.equal(await page.locator('h1').innerText(),'저장 사례 라벨');
  assert.equal(await page.locator('#shape').textContent(),'벽·중심선 변경 후보 만들기');
  await page.reload();assert.equal(await page.locator('html').getAttribute('lang'),'ko');
  await page.locator('#vv-language [data-language=en]').click();
  assert.equal(await page.locator('#shape').textContent(),'Create wall and centerline candidate');
  assert.equal(await page.locator('h1').innerText(),'Saved case labels');
  await page.locator('#file').setInputFiles('exports/source-chain-ui/input.snapshot.json');
  await page.waitForFunction(()=>data&&!busy);
  const before=await page.evaluate(()=>JSON.stringify(data.snapshot));
  await page.locator('#vv-language [data-language=ko]').click();
  await page.locator('#vv-language [data-language=en]').click();
  assert.equal(await page.evaluate(()=>JSON.stringify(data.snapshot)),before);
  await page.locator('#shapePanel summary').click();
  await page.locator('#shapeCollar').fill('0.1');await page.locator('#shapeTransition').fill('1');
  await page.locator('#shapeBend').fill('1000');await page.locator('#shape').click();
  report.step='English edit rejection';
  await page.waitForFunction(()=>!busy&&document.querySelector('#status').textContent.includes('displacement bound'));
  assert.match(await page.locator('#status').textContent(),/Current case and edit history kept/);
  await page.locator('#vv-language [data-language=ko]').click();
  report.step='Korean edit rejection';
  await page.waitForFunction(()=>document.querySelector('#status').textContent.includes('이동 허용값을 초과'));
  assert.equal(await page.evaluate(()=>JSON.stringify(data.snapshot)),before);
  await page.locator('#shapeBend').fill('0.1');await page.locator('#shapeCollar').fill('0.1');await page.locator('#shapeTransition').fill('1');
  await page.locator('#shape').click();await page.waitForFunction(()=>!busy&&data.snapshot.case.inspection?.registered_shape_edit);
  report.step='English edit result';
  await page.locator('#vv-language [data-language=en]').click();
  await page.waitForFunction(()=>document.querySelector('#status').textContent.includes('Wall and centerline candidate created'));
  assert.match(await page.locator('#status').textContent(),/not approved for generation/);
  await page.locator('#vv-language [data-language=ko]').click();
  report.step='Korean edit result';
  await page.waitForFunction(()=>document.querySelector('#status').textContent.includes('벽·중심선 후보 생성'));
  await page.locator('#vv-language [data-language=en]').click();
  await page.setViewportSize({width:390,height:844});
  const rect=await page.locator('#vv-language').boundingBox();assert(rect.x>=0&&rect.x+rect.width<=390&&rect.y<20);
  await page.screenshot({path:out+'/workbench-mobile.png'});
  report.step='Main scene language';
  await page.goto(base+'/');
  if(live)await page.waitForFunction(()=>state?.scene_description);
  await page.locator('#vv-language [data-language=ko]').click();
  assert.equal(await page.locator('label[for=source]').innerText(),'해부 모델 출처');
  if(live){
   await page.waitForFunction(()=>state?.scene_description&&document.querySelector('#sceneLegendText').textContent.includes('공통 좌표'));
   const scene=await page.evaluate(()=>({source:state.source,generation:state.generation,description:state.scene_description}));
   await page.locator('#vv-language [data-language=en]').click();
   await page.waitForFunction(()=>document.querySelector('#sceneLegendText').textContent.includes('shared-coordinate atlas'));
   assert.deepEqual(await page.evaluate(()=>({source:state.source,generation:state.generation,description:state.scene_description})),scene);
   await page.locator('#vv-language [data-language=ko]').click();
   report.scene_description_bilingual=true;report.scene_state_unchanged=true;
  }
  await page.setViewportSize({width:1280,height:1000});await page.screenshot({path:out+'/main-korean.png'});
  const second=await context.newPage();await second.goto(base+'/case-labels');
  assert.equal(await second.locator('html').getAttribute('lang'),'ko');
  await page.locator('#vv-language [data-language=en]').click();
  await second.waitForFunction(()=>document.documentElement.lang==='en');
  assert.deepEqual(errors,[]);
  Object.assign(report,{status:'PASS',reload_persisted:true,cross_page_persisted:true,cross_tab_synced:true,snapshot_unchanged:true,edit_error_bilingual:true,edit_result_bilingual:true,mobile_toolbar_visible:true,browser_errors:errors});
 }catch(e){report.status='FAIL';report.error=String(e);report.last_status=await page.locator('#status').textContent().catch(()=>null);process.exitCode=1;}
 finally{await browser.close();fs.writeFileSync(live?'docs/evidence/ui-language-live-browser.json':'docs/evidence/ui-language-browser.json',JSON.stringify(report,null,2)+'\n');}
 console.log(JSON.stringify(report));
})().catch(e=>{console.error(e);process.exitCode=1});
