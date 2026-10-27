const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
(async()=>{
 const source=JSON.parse(fs.readFileSync('exports/label-workbench/smoothing.snapshot.json','utf8'));
 const browser=await chromium.connectOverCDP('http://127.0.0.1:9222');
 const page=await browser.contexts()[0].newPage(),errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 async function download(name){
  const pending=page.waitForEvent('download');await page.locator('#download').click();
  const file=`exports/label-workbench/${name}.json`;await(await pending).saveAs(file);
  return JSON.parse(fs.readFileSync(file,'utf8'));
 }
 try{
  await page.setViewportSize({width:1280,height:1000});
  await page.goto('http://127.0.0.1:8093/case-labels');
  await page.locator('#file').setInputFiles('exports/label-workbench/smoothing.snapshot.json');
  await page.waitForFunction(()=>!document.querySelector('#search').disabled);
  await page.locator('#edge').selectOption('b');assert(await page.locator('#smooth').isDisabled());
  await page.locator('#edge').selectOption('a');
  await page.locator('summary').filter({hasText:'Modify selected centerline'}).click();
  await page.locator('#smooth').click();
  await page.waitForFunction(()=>document.querySelector('#status').textContent.includes('Synthetic copy created'));
  const changed=await download('smoothed');
  assert.equal(changed.case.model_kind,'synthetic');
  assert.deepEqual(changed.case.nodes,source.case.nodes);
  assert.deepEqual(changed.case.edges.slice(1),source.case.edges.slice(1));
  const old=source.case.edges[0],next=changed.case.edges[0];
  assert.notDeepEqual(next.centerline_mm,old.centerline_mm);
  for(const i of [0,1,7,8])assert.deepEqual(next.centerline_mm[i],old.centerline_mm[i]);
  assert.deepEqual(next.radii_mm,old.radii_mm);
  await page.locator('#undo').click();
  assert.deepEqual(await download('smoothing-undone'),source);
  await page.locator('#redo').click();
  assert.deepEqual(await download('smoothing-redone'),changed);
  await page.locator('#smooth').scrollIntoViewIfNeeded();
  await page.screenshot({path:'exports/label-workbench/smoothing.png'});
  assert.deepEqual(errors,[]);
  const report={status:'PASS',url:page.url(),page_errors:errors,
   checks:['short edge disabled','synthetic copy created','frozen endpoint chords and radii',
    'other edges unchanged','undo exact source','redo exact result','download'],
   maximum_displacement_mm:changed.case.centerline_regularization.metrics[0].max_displacement_mm,
   geometry_quality:changed.case.centerline_regularization.geometry_quality,
   scope:'synthetic fixture centerline editing; surface collisions and anatomical validation NOT RUN'};
  fs.writeFileSync('docs/evidence/workbench-smoothing-browser.json',JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify(report));
 }finally{await page.close();await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
