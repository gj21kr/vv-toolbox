const {chromium}=require('playwright'),fs=require('node:fs'),crypto=require('node:crypto');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.connectOverCDP('http://127.0.0.1:9222');
 const page=await browser.contexts()[0].newPage();page.setDefaultTimeout(300000);
 const base='http://127.0.0.1:8093',errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 const hash=()=>crypto.createHash('sha256').update(fs.readFileSync('reference-data/bodyparts3d/atlas-edits.snapshot.json')).digest('hex');
 let initial;
 try{
  initial=await page.request.get(base+'/api/state').then(r=>r.json());const originalHash=hash();
  await page.route('http://127.0.0.1:8094/**',r=>r.abort());
  await page.setViewportSize({width:1440,height:1000});
  await page.goto(base,{waitUntil:'domcontentloaded'});
  await page.waitForFunction(()=>typeof atlasCenterlineData!=='undefined'&&atlasCenterlineData);
  await page.request.post(base+'/api/atlas-selection',{data:{part_id:'FJ1692'}});
  await page.waitForFunction(()=>state?.atlas_selection==='FJ1692');
  await page.locator('#intervalPreviewPanel summary').click();
  await page.waitForFunction(()=>!document.querySelector('#intervalFields').disabled);
  const request=JSON.parse(fs.readFileSync('docs/evidence/live-interval-preview.json')).request;
  const fields={start_mm:'intervalStart',end_mm:'intervalEnd',factor:'intervalFactor',
   max_displacement_mm:'intervalMovement',absolute_scale_tolerance:'intervalTolerance'};
  for(const[k,id]of Object.entries(fields))await page.locator('#'+id).fill(String(request[k]));
  await page.locator('#intervalForm button').click();
  await page.waitForFunction(()=>!document.querySelector('#intervalResult').hidden,{},{timeout:300000});
  console.log('Actual Atlas candidate generated');
  fs.mkdirSync('exports/interval-snapshot-ui',{recursive:true});
  const downloading=page.waitForEvent('download');
  await page.locator('#intervalDownload').click();
  const download=await downloading;
  const file='exports/interval-snapshot-ui/candidate.json';await download.saveAs(file);
  const bytes=fs.readFileSync(file),snapshot=JSON.parse(bytes);
  assert.equal(snapshot.schema,'vv-toolbox.interval-candidate-snapshot/1');
  await page.locator('#intervalFile').setInputFiles(file);
  await page.waitForFunction(()=>document.querySelector('#intervalMessage').textContent.startsWith('저장 후보 열림'));
  const originalCanvas=await page.locator('#intervalCanvas').evaluate(c=>c.toDataURL());
  await page.locator('#intervalResult').screenshot({path:'exports/interval-snapshot-ui/reloaded.png'});
  const changed=JSON.parse(bytes);changed.candidate.vertices[0][0]+=.1;
  await page.locator('#intervalFile').setInputFiles({name:'tampered.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(changed))});
  await page.waitForFunction(()=>document.querySelector('#intervalMessage').textContent.startsWith('파일 열기 중단'));
  assert.equal(await page.locator('#intervalCanvas').evaluate(c=>c.toDataURL()),originalCanvas);
  const after=await page.request.get(base+'/api/state').then(r=>r.json());
  assert.equal(after.generation,initial.generation);assert.deepEqual(after.atlas_modifications,initial.atlas_modifications);
  assert.equal(hash(),originalHash);assert.deepEqual(errors,[]);
  fs.writeFileSync('docs/evidence/interval-snapshot-ui.json',JSON.stringify({
   status:'PASS',scope:'Actual Atlas creation, download, reimport and tamper rejection',
   snapshot_revision:snapshot.revision,snapshot_sha256:crypto.createHash('sha256').update(bytes).digest('hex'),
   source_sha256:originalHash,prior_preview_preserved_after_bad_import:true,source_unchanged:true,
   synthetic_response:false,geometry_revalidation_on_import:'NOT RUN',errors
  },null,2)+'\n');
  console.log('PASS: actual candidate download/reload; tampered file rejected without losing preview');
 }finally{
  if(initial?.atlas_selection)await page.request.post(base+'/api/atlas-selection',{data:{part_id:initial.atlas_selection}});
  await page.close();await browser.close();
 }
})().catch(e=>{console.error(e);process.exitCode=1});
