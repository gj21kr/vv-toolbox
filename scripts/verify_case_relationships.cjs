const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
(async()=>{
 const browser=await chromium.connectOverCDP('http://127.0.0.1:9222');
 const page=await browser.contexts()[0].newPage(),errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 try{
  await page.setViewportSize({width:1280,height:1000});
  await page.goto('http://127.0.0.1:8093/case-labels');
  await page.locator('#file').setInputFiles('exports/label-workbench/relationships.snapshot.json');
  await page.waitForFunction(()=>!document.querySelector('#search').disabled);
  await page.locator('#edge').selectOption('selected');
  for(const end of ['start','end']){
   assert.equal(await page.locator(`[data-endpoint="${end}"] button`).count(),5);
   assert.match(await page.locator(`[data-endpoint="${end}"]`).innerText(),/evidence: unresolved/);
  }
  assert.equal(await page.locator('#relationships [data-edge-id="not-a-neighbor"]').count(),0);
  await page.locator('#relationships').scrollIntoViewIfNeeded();
  await page.screenshot({path:'exports/label-workbench/relationships-desktop.png'});
  await page.locator('#relationships [data-edge-id="last-4"]').click();
  assert.equal(await page.locator('#edge').inputValue(),'last-4');
  assert.equal(await page.locator('#relationships [data-edge-id="selected"]').count(),1);
  await page.locator('#relationships [data-edge-id="selected"]').click();
  assert.equal(await page.locator('#edge').inputValue(),'selected');
  await page.setViewportSize({width:390,height:844});
  await page.locator('#relationships').scrollIntoViewIfNeeded();
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  assert.equal(await page.locator('#relationships button').count(),10);
  await page.screenshot({path:'exports/label-workbench/relationships-mobile.png',fullPage:true});
  assert.deepEqual(errors,[]);
  const report={status:'PASS',url:page.url(),checks:['five neighbors at each endpoint',
   'uncertainty visible','coincident distinct node not connected','neighbor selection and return',
   'mobile no horizontal overflow, all neighbors retained'],page_errors:errors,
   scope:'synthetic saved-graph incidence UI; not anatomical validation'};
  fs.writeFileSync('docs/evidence/case-relationships-browser.json',JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify(report));
 }finally{await page.close();await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
