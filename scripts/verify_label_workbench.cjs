const {chromium}=require('playwright');
const fs=require('node:fs');
const path=require('node:path');
const assert=require('node:assert/strict');
const crypto=require('node:crypto');
(async()=>{
 const root=process.cwd(),out=path.join(root,'exports/label-workbench');
 fs.mkdirSync(out,{recursive:true});
 const userFile=path.join(root,'reference-data/bodyparts3d/atlas-edits.snapshot.json');
 const hash=()=>crypto.createHash('sha256').update(fs.readFileSync(userFile)).digest('hex');
 const before=hash();
 const browser=await chromium.connectOverCDP('http://127.0.0.1:9222');
 const page=await browser.contexts()[0].newPage();
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 page.on('console',m=>{if(m.type()==='error')errors.push(m.text())});
 try{
  await page.setViewportSize({width:1200,height:1000});
  await page.goto('http://127.0.0.1:8093/case-labels');
  assert.equal(await page.title(),'VV Toolbox · Saved case labels');
  await page.locator('#file').setInputFiles(path.join(out,'fixture.snapshot.json'));
  await page.waitForFunction(()=>!document.querySelector('#search').disabled);
  await page.locator('#search').fill('no-such-edge');
  assert.equal(await page.locator('#edge option').count(),0);
  assert(await page.locator('#apply').isDisabled());
  await page.locator('#search').fill('');
  // Pick the second disjoint centerline, then rotate and reset the view.
  const canvas=page.locator('#preview'),box=await canvas.boundingBox();
  await canvas.click({position:{x:box.width/2+box.height*.8/30*25-box.height*.8/30*15,y:box.height/2}});
  assert.equal(await page.locator('#edge').inputValue(),'b');
  await canvas.focus();await page.keyboard.press('ArrowRight');
  await page.locator('#fit').click();
  await page.locator('#edge').selectOption('a');
  await page.locator('#label').selectOption('13');
  await page.locator('#apply').click();
  assert.match(await page.locator('#status').innerText(),/at least one/);
  await page.locator('#refs').fill('Synthetic fixture extent review');
  await page.locator('#apply').click();
  await page.waitForFunction(()=>!document.querySelector('#download').disabled);
  assert.match(await page.locator('#selection').innerText(),/current mask ID 13/);
  await page.locator('#file').setInputFiles({name:'invalid.json',mimeType:'application/json',buffer:Buffer.from('{broken')});
  await page.waitForFunction(()=>document.querySelector('#status').textContent.includes('history kept'));
  assert.match(await page.locator('#selection').innerText(),/current mask ID 13/);
  page.once('dialog',dialog=>dialog.dismiss());
  await page.locator('#file').setInputFiles(path.join(out,'fixture.snapshot.json'));
  await page.waitForFunction(()=>document.querySelector('#status').textContent==='Current case and edit history kept.');
  assert.match(await page.locator('#selection').innerText(),/current mask ID 13/);
  await page.locator('#undo').click();
  assert.match(await page.locator('#selection').innerText(),/current mask ID 0/);
  const undone=page.waitForEvent('download');
  await page.locator('#download').click();
  await (await undone).saveAs(path.join(out,'undone.snapshot.json'));
  assert.deepEqual(JSON.parse(fs.readFileSync(path.join(out,'undone.snapshot.json'),'utf8')),
   JSON.parse(fs.readFileSync(path.join(out,'fixture.snapshot.json'),'utf8')));
  await page.locator('#redo').click();
  assert.match(await page.locator('#selection').innerText(),/current mask ID 13/);
  // A new edit after undo discards the redo branch.
  await page.locator('#undo').click();
  await page.locator('#label').selectOption('18');
  await page.locator('#refs').fill('Synthetic alternative extent review');
  await page.locator('#apply').click();
  await page.waitForFunction(()=>document.querySelector('#selection').textContent.includes('current mask ID 18'));
  assert(await page.locator('#redo').isDisabled());
  await page.locator('#undo').click();
  await page.locator('#label').selectOption('13');
  await page.locator('#refs').fill('Synthetic fixture extent review');
  await page.locator('#apply').click();
  await page.waitForFunction(()=>document.querySelector('#selection').textContent.includes('current mask ID 13'));
  const downloaded=page.waitForEvent('download');
  await page.locator('#download').click();
  const download=await downloaded;
  const filename=path.join(out,'download.snapshot.json');
  await download.saveAs(filename);
  const result=JSON.parse(fs.readFileSync(filename,'utf8'));
  assert.equal(result.case.edges.find(e=>e.id==='a').anatomy.artery,'femoral');
  assert.equal(result.case.edges.find(e=>e.id==='a').anatomy.side,'L');
  await page.screenshot({path:path.join(out,'desktop.png'),fullPage:true});
  await page.setViewportSize({width:390,height:844});
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await page.screenshot({path:path.join(out,'mobile.png'),fullPage:true});
  assert.deepEqual(errors,[]);
  assert.equal(hash(),before);
  const report={status:'PASS',browser_fallback:'Browser plugin not available; Playwright over existing CDP',
   url:page.url(),title:await page.title(),checks:['upload','search','no matches disables apply',
    'centerline click selects edge','keyboard rotation and reset',
    'missing evidence rejected','apply','invalid upload preserves edits','replacement cancellation preserves edits',
    'undo restores exact source snapshot','redo',
    'new edit discards redo branch','download content','mobile no horizontal overflow'],
   screenshot_paths:['exports/label-workbench/desktop.png','exports/label-workbench/mobile.png'],
   console_errors:errors,user_atlas_snapshot_sha256:before,user_snapshot_preserved:true,
   scope:'synthetic saved-case label workflow; not anatomical validation or Atlas scene editing'};
  fs.writeFileSync('docs/evidence/label-workbench-browser.json',JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify(report));
 }finally{await page.close();await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
