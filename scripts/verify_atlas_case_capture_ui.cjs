const {chromium}=require('playwright'),fs=require('node:fs'),crypto=require('node:crypto');
const assert=require('node:assert/strict');
const estimates=process.argv.includes('--estimates');
const folder=estimates?'exports/atlas-case-estimates-ui':'exports/atlas-case-capture-ui';
const digest=file=>fs.existsSync(file)?crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex'):null;
(async()=>{
 const browser=await chromium.connectOverCDP('http://127.0.0.1:9222');
 const page=await browser.contexts()[0].newPage();page.setDefaultTimeout(300000);
 const base='http://127.0.0.1:8093',errors=[];
 const files=['reference-data/bodyparts3d/atlas-edits.snapshot.json','reference-data/bodyparts3d/arterial-workspace.snapshot.json'];
 const beforeHashes=files.map(digest);
 page.on('pageerror',e=>errors.push(e.message));
 try{
  const initial=await page.request.get(base+'/api/state').then(r=>r.json());
  assert.deepEqual(initial.atlas_modifications,{});assert.deepEqual(initial.atlas_interval_edits,{});
  await page.route('http://127.0.0.1:8094/**',r=>r.abort());
  await page.setViewportSize({width:1440,height:1100});
  await page.goto(base,{waitUntil:'domcontentloaded'});
  await page.waitForFunction(()=>state?.atlas_centerlines?.available&&caseState);
  const capturing=page.waitForResponse(r=>r.url().endsWith('/api/case-workspace')&&r.request().method()==='POST');
  await page.locator('#casePrepareCurrent').click();console.log('Actual Atlas surface capture started');
  const response=await capturing,status=await response.json();
  assert.equal(response.status(),200,JSON.stringify(status));
  assert(status.summary.surface_parts>0);assert.equal(status.includes_atlas_edits,false);
  const downloading=page.waitForEvent('download');
  await page.locator('#caseDownload').click();
  const download=await downloading;
  fs.mkdirSync(folder,{recursive:true});
  const file=folder+'/case.snapshot.json';
  await download.saveAs(file);
  const snapshot=JSON.parse(fs.readFileSync(file)),c=snapshot.case;
  assert.equal(c.surface_parts.length,status.summary.surface_parts);
  if(estimates){
   assert.equal(status.includes_estimates,true);
   assert.equal(c.model_kind,'synthetic');
   assert.equal(c.surface_parts.filter(p=>p.provenance==='estimated').length,4);
   assert.equal(c.surface_parts.filter(p=>p.provenance==='source').length,517);
  }else assert(c.surface_parts.every(p=>p.provenance==='source'));
  assert.equal(c.inspection.atlas_scene_capture.includes_edits,false);
  await page.locator('#caseSummary').locator('..').screenshot({path:folder+'/captured.png'});
  const after=await page.request.get(base+'/api/state').then(r=>r.json());
  assert.equal(after.generation,initial.generation);assert.deepEqual(files.map(digest),beforeHashes);
  assert.deepEqual(errors,[]);
  fs.writeFileSync(estimates?'docs/evidence/atlas-case-estimates-ui.json':'docs/evidence/atlas-case-capture-ui.json',JSON.stringify({
   status:'PASS',scope:'Actual unmodified Atlas current-surface capture and browser download',
   summary:status.summary,capture:c.inspection.atlas_scene_capture,
   file_bytes:fs.statSync(file).size,file_sha256:digest(file),original_files_unchanged:true,
   scene_generation_unchanged:true,full_viser_scene:'NOT RUN',modified_atlas_capture:'NOT RUN',errors
  },null,2)+'\n');
  console.log(`PASS: downloaded ${c.surface_parts.length} registered surfaces`);
 }finally{await page.close();await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
