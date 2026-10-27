// Regression for readiness changing without a new anatomy generation.
const {chromium}=require('playwright');
const fs=require('node:fs');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.connectOverCDP('http://127.0.0.1:9222');
 const page=browser.contexts()[0].pages().find(p=>p.url().startsWith('http://127.0.0.1:8093/'));
 assert(page);
 let loading=true;
 const route=async r=>{
  const response=await r.fetch();const data=await response.json();
  if(loading)data.atlas_centerlines.available=false;
  await r.fulfill({response,json:data});
 };
 try{
  const initial=await (await page.request.get('http://127.0.0.1:8093/api/state')).json();
  assert.equal(initial.atlas_centerlines.available,true);
  await page.route('**/api/state',route);
  await page.waitForFunction(()=>document.querySelector('#atlasEditsSave').disabled,null,{polling:250,timeout:30000});
  loading=false;
  await page.waitForFunction(()=>!document.querySelector('#atlasEditsSave').disabled,null,{polling:250,timeout:30000});
  const final=await (await page.request.get('http://127.0.0.1:8093/api/state')).json();
  assert.equal(final.generation,initial.generation);
  assert.deepEqual(final.atlas_modifications,initial.atlas_modifications);
  const report={status:'PASS',scope:'Simulated client loading -> ready transition with unchanged server generation',
   generation:final.generation,save_button_reenabled:true,server_geometry_unchanged:true};
  fs.writeFileSync('exports/atlas-contact-gate-verification/readiness.json',JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify(report));
 }finally{await page.unrouteAll({behavior:'wait'});await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
