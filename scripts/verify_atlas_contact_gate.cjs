// Isolated storage only; uses the existing local browser and never writes user snapshots.
const {chromium}=require('playwright');
const fs=require('node:fs');
const crypto=require('node:crypto');
const assert=require('node:assert/strict');
const base='http://127.0.0.1:8093';
const out='exports/atlas-contact-gate-verification';
const file=out+'/isolated.snapshot.json';
const hash=x=>crypto.createHash('sha256').update(x).digest('hex');
(async()=>{
 const b=await chromium.connectOverCDP('http://127.0.0.1:9222');
 try{
  const page=b.contexts()[0].pages().find(p=>p.url().startsWith(base+'/'));
  assert(page);
  page.setDefaultTimeout(60000);
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  const get=async path=>{const r=await page.request.get(base+path);assert.equal(r.status(),200);return r.json()};
  const initial=await get('/api/state');
  assert.equal(initial.source,'atlas');assert.equal(initial.busy,false);
  assert.deepEqual(initial.atlas_modifications,{});
  assert.equal((await get('/api/atlas-edit-session')).file_exists,false);
  assert(!fs.existsSync(file));
  fs.mkdirSync(out,{recursive:true});
  if(!process.argv.includes('--loaded'))await page.reload();
  await page.locator('#atlasModificationSearch').fill('FJ1692');
  const selected=page.waitForResponse(r=>r.url().endsWith('/api/atlas-selection')&&r.request().method()==='POST');
  await page.locator('#atlasModificationVessel').selectOption('FJ1692');
  assert([200,202].includes((await selected).status()));
  await page.waitForFunction(()=>!document.querySelector('#atlasModificationControls').disabled,null,{polling:250});
  const click=async(selector,endpoint,status)=>{
   await page.waitForFunction(s=>!document.querySelector(s).disabled,selector,{polling:250});
   const pending=page.waitForResponse(r=>r.url().endsWith(endpoint)&&r.request().method()==='POST');
   await page.locator(selector).click();
   const response=await pending;const data=await response.json();
   assert(status===200 ? [200,202].includes(response.status()) : response.status()===status,JSON.stringify(data));return data;
  };
  const set=async values=>{
   for(const [selector,value] of [['#atlasRadius',values[0]],['#atlasTortuosity',values[1]],['#atlasTorsion',values[2]]]){
    await page.locator(selector).evaluate((el,v)=>{el.value=String(v);el.dispatchEvent(new Event('input',{bubbles:true}))},value);
   }
  };
  await click('#atlasEditsSave','/api/atlas-edit-session',200);
  assert(fs.existsSync(file),'Server must use this isolated path');
  const savedHash=hash(fs.readFileSync(file));
  const before=await get('/api/export');const beforeState=await get('/api/state');
  await set([2,1,180]);
  const rejected=await click('#applyAtlasModification','/api/atlas-modification',422);
  assert.equal(rejected.code,'atlas_edit_checks_failed');
  await page.waitForFunction(()=>document.querySelector('#error').textContent.includes('self-contact check FAIL'),null,{polling:250});
  const after=await get('/api/export'),state=await get('/api/state');
  assert.equal(state.generation,beforeState.generation);
  assert.deepEqual(after.centerlines,before.centerlines);
  assert.deepEqual(after.modified_surfaces,before.modified_surfaces);
  assert.deepEqual(state.atlas_modifications,{});
  assert.equal(hash(fs.readFileSync(file)),savedHash);
  await page.locator('#error').scrollIntoViewIfNeeded();
  await page.screenshot({path:out+'/rejected-edit.png'});
  console.log('Rejected self-contact edit: state and snapshot unchanged');
  await set([1.3,0,0]);
  await click('#applyAtlasModification','/api/atlas-modification',200);
  const changed=await get('/api/export');
  assert.equal(changed.edit_checks.FJ1692.self_intersection,'PASS');
  await click('#atlasEditsSave','/api/atlas-edit-session',200);
  await click('#resetAtlasModification','/api/atlas-modification',200);
  await click('#atlasEditsReload','/api/atlas-edit-session',200);
  const reloaded=await get('/api/export');
  assert.deepEqual(reloaded.modified_surfaces.FJ1692,changed.modified_surfaces.FJ1692);
  assert.equal(reloaded.edit_checks.FJ1692.self_intersection,'PASS');
  await page.locator('#atlasModificationStatus').scrollIntoViewIfNeeded();
  await page.screenshot({path:out+'/accepted-edit.png'});
  await click('#resetAtlasModification','/api/atlas-modification',200);
  await click('#atlasEditsSave','/api/atlas-edit-session',200);
  assert.deepEqual((await get('/api/state')).atlas_modifications,{});
  assert.deepEqual(errors,[]);
  const report={status:'PASS',url:page.url(),title:await page.title(),viewport:page.viewportSize(),
   browser_path:'Playwright over existing CDP; Browser plugin not available',
   initial_load:process.argv.includes('--loaded')?'Already loaded tab; cold-load timing not validated':'Reloaded tab',
   failed_parameters:{radius_scale:2,tortuosity:1,torsion_deg:180},rejection:rejected,
   rejected_edit_preserves_generation_graph_surfaces_and_snapshot:true,
   normal_radius_edit_save_reset_reload:true,original_geometry_restored:true,page_errors:errors,
   scope:'Live UI/HTTP edit rejection and successful self-contact-screened save/reload. Does not validate surrounding collision or radius accuracy.'};
  fs.writeFileSync(out+'/result.json',JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify(report));
 }finally{await b.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
