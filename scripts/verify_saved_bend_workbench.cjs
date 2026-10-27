const {chromium}=require('playwright');
const fs=require('node:fs'),assert=require('node:assert/strict'),crypto=require('node:crypto');
(async()=>{
 const surface=process.argv.includes('--surface');
 const smooth=process.argv.includes('--smooth');
 const out=smooth?'exports/saved-bend-smoothing-ui':surface?'exports/saved-bend-surface':'exports/saved-bend-workbench',input='exports/bend-case-download/case.snapshot.json';
 fs.mkdirSync(out,{recursive:true});
 const browser=await chromium.launch({headless:true});
 const page=await browser.newPage({acceptDownloads:true,viewport:{width:1280,height:1000}});
 page.setDefaultTimeout(60000);
 const errors=[],report={status:'RUNNING',scope:'Saved bend case import, inspection banner, graph search and unchanged download',browser_path:'Playwright: Browser plugin not available'};
 if(smooth)report.scope='Saved bend centerline smoothing, fixed surface, undo/redo and edited download';
 page.on('pageerror',e=>errors.push(e.message));
 try{
  const before=await page.request.get('http://127.0.0.1:8093/api/state').then(r=>r.json());
  await page.goto('http://127.0.0.1:8093/case-labels');
  await page.locator('#file').setInputFiles(input);
  await page.waitForFunction(()=>data?.edges.length===65&&!busy);
  assert.match(await page.locator('#savedInspection').innerText(),/FAIL/);
  assert.match(await page.locator('#savedInspection').innerText(),/미승인/);
  await page.locator('#search').fill('FJ2074');
  assert.equal(await page.locator('#edge option').count(),1);
  assert.equal(await page.locator('#edge').inputValue(),'FJ2074:e0');
  if(smooth){
   await page.locator('details:not(#shapePanel) summary').click();
   await page.locator('#sigma').fill('0.5');await page.locator('#bound').fill('0.3');
   const prior=await page.evaluate(()=>data.snapshot.revision);
   await page.locator('#smooth').click();
   await page.waitForFunction(prior=>!busy&&data.snapshot.revision!==prior,prior);
   const edited=await page.evaluate(()=>data.snapshot);
   assert.equal(edited.case.inspection.centerline_edit.checked_paths[0].containment.status,'PASS');
   assert.equal(edited.case.inspection.centerline_edit.accepted_for_generation,false);
   await page.locator('#undo').click();assert.equal(await page.evaluate(()=>data.snapshot.revision),prior);
   await page.locator('#redo').click();assert.equal(await page.evaluate(()=>data.snapshot.revision),edited.revision);
   Object.assign(report,{smoothing:true,undo_redo:true,changed_revision:edited.revision});
  }
  if(surface){
   assert.equal(await page.evaluate(()=>preview.surfaceError),'');
   assert.equal(await page.evaluate(()=>preview.surface.count),50188*3);
   await page.locator('#showCenterlines').uncheck();
   await page.locator('#focus').click();
   assert.equal(await page.evaluate(()=>preview.segments.length),0);
   const first=await page.locator('#preview').screenshot({path:out+'/surface.png'});
   const pixels=await page.evaluate(()=>{const g=preview.surface.gl,d=new Uint8Array(g.drawingBufferWidth*g.drawingBufferHeight*4);
    g.readPixels(0,0,g.drawingBufferWidth,g.drawingBufferHeight,g.RGBA,g.UNSIGNED_BYTE,d);
    let n=0;for(let i=3;i<d.length;i+=4)if(d[i])n++;return n;});
   assert(pixels>100,'Surface must draw nontransparent pixels');
   await page.locator('#preview').focus();await page.keyboard.press('ArrowRight');
   const rotated=await page.locator('#preview').screenshot({path:out+'/rotated.png'});
   assert.notDeepEqual(first,rotated);
   await page.locator('#showSurface').uncheck();
   const hidden=await page.locator('#preview').screenshot({path:out+'/hidden.png'});
   assert.notDeepEqual(hidden,rotated);
   await page.locator('#showCenterlines').check();
   assert(await page.evaluate(()=>preview.segments.length>0));
   await page.locator('#showSurface').check();
   Object.assign(report,{surface_triangles:50188,rendered_pixels:pixels,surface_toggles:true,rotation:true});
  }
  const waiting=page.waitForEvent('download');await page.locator('#download').click();
  await (await waiting).saveAs(out+'/case.snapshot.json');
  const original=JSON.parse(fs.readFileSync(input)),saved=JSON.parse(fs.readFileSync(out+'/case.snapshot.json'));
  if(smooth){
   assert.deepEqual(saved.case.surface_parts[0].vertices_mm,original.case.surface_parts[0].vertices_mm);
   assert.deepEqual(saved.case.surface_parts[0].faces,original.case.surface_parts[0].faces);
   assert.deepEqual(saved.case.inspection.access_candidate,original.case.inspection.access_candidate);
   assert.deepEqual(saved,await page.evaluate(()=>data.snapshot));
  }else assert.deepEqual(saved,original);
  await page.locator('#savedInspection').screenshot({path:out+'/inspection.png'});
  await page.locator('#preview').screenshot({path:out+'/centerlines.png'});
  await page.setViewportSize({width:390,height:844});
  await page.locator('#savedInspection').screenshot({path:out+'/inspection-mobile.png'});
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
  const after=await page.request.get('http://127.0.0.1:8093/api/state').then(r=>r.json());
  assert.equal(after.source,before.source);assert.equal(after.generation,before.generation);
  assert.deepEqual(errors,[]);
  Object.assign(report,{status:'PASS',revision:saved.revision,edges:saved.case.edges.length,
   file_sha256:crypto.createHash('sha256').update(fs.readFileSync(out+'/case.snapshot.json')).digest('hex'),
   exact_document_roundtrip:!smooth,edited_document_download:smooth,atlas_unchanged:true,browser_errors:errors,visual_review:'NOT RUN'});
 }catch(e){report.status='FAIL';report.error=String(e);process.exitCode=1;}
 finally{await browser.close();fs.writeFileSync(smooth?'docs/evidence/saved-bend-smoothing-ui.json':surface?'docs/evidence/saved-bend-surface-ui.json':'docs/evidence/saved-bend-workbench-ui.json',JSON.stringify(report,null,2)+'\n');}
 console.log(JSON.stringify(report));
})().catch(e=>{console.error(e);process.exitCode=1});
