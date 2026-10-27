const {chromium}=require('playwright');
const fs=require('node:fs');
const crypto=require('node:crypto');
const assert=require('node:assert/strict');
(async()=>{
 const file='exports/atlas-case-inspection/all-arterial.snapshot.json';
 const raw=fs.readFileSync(file),snapshot=JSON.parse(raw);
 const browser=await chromium.connectOverCDP('http://127.0.0.1:9222');
 const page=await browser.contexts()[0].newPage(),errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 try{
  await page.setViewportSize({width:1280,height:1000});
  await page.goto('http://127.0.0.1:8093/case-labels');
  await page.locator('#file').setInputFiles(file);
  await page.waitForFunction(()=>!document.querySelector('#search').disabled,null,{timeout:60000});
  assert.equal(await page.locator('#edge option').count(),snapshot.case.edges.length);
  await page.locator('#search').fill('FJ1692');
  assert(await page.locator('#edge option').count()>0);
  await page.locator('#edge').selectOption('FJ1692:e0');
  await page.locator('#preview').scrollIntoViewIfNeeded();
  await page.screenshot({path:'exports/label-workbench/atlas-preview.png'});
  await page.locator('#focus').click();
  await page.locator('#preview').scrollIntoViewIfNeeded();
  await page.screenshot({path:'exports/label-workbench/atlas-selected-preview.png'});
  const report={status:'PASS',url:page.url(),source_file:file,
   source_sha256:crypto.createHash('sha256').update(raw).digest('hex'),
   source_bytes:raw.length,edge_count:snapshot.case.edges.length,
   selected_edge:await page.locator('#edge').inputValue(),errors,
   screenshot:'exports/label-workbench/atlas-preview.png',
   scope:'Full saved arterial case load, searchable selection and centerline display; no anatomical approval or source edit'};
  assert.deepEqual(errors,[]);
  fs.writeFileSync('docs/evidence/case-preview-atlas-browser.json',JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify(report));
 }finally{await page.close();await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
