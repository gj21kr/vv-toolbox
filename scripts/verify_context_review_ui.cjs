const {chromium}=require('playwright');
const fs=require('node:fs'),assert=require('node:assert/strict');
(async()=>{
 const live=process.argv.includes('--live');
 const out=live?'exports/context-review-live-ui':'exports/context-review-ui';
 fs.mkdirSync(out,{recursive:true});
 const input=JSON.parse(fs.readFileSync('exports/registered-context-fresh/case.snapshot.json'));
 const context=input.case.inspection.registered_shape_edit.context;
 const expected=context.rows.filter(r=>r.before.status!=='SEPARATED'||r.after.status!=='SEPARATED'||r.added_contact_pairs.length||r.removed_contact_pairs.length);
 const report={status:'RUNNING',scope:live?'Actual demo HTTP display of full saved 788-neighbor result; no new measurements':'Full saved 788-neighbor result displayed with current HTML and real inspect API; no new measurements'};
 const browser=await chromium.launch({headless:true});
 const page=await browser.newPage({viewport:{width:1280,height:1000}});page.setDefaultTimeout(60000);
 try{
  if(!live)await page.route('http://127.0.0.1:8093/case-labels',r=>r.fulfill({contentType:'text/html',body:fs.readFileSync(out+'/workbench.html','utf8')}));
  await page.goto('http://127.0.0.1:8093/case-labels');
  await page.locator('#file').setInputFiles('exports/registered-context-fresh/case.snapshot.json');
  await page.waitForFunction(()=>data&&!busy);
  await page.locator('#contactReview summary').click();
  assert.equal(await page.locator('#contactRows tr').count(),expected.length);
  for(const id of context.new_or_extended_contacts){assert(await page.locator('#contactRows').innerText().then(t=>t.includes(id)));}
  const actual=await page.locator('#contactRows tr').evaluateAll(rows=>rows.map(r=>[...r.children].map(c=>c.textContent)));
  for(const row of expected){assert.deepEqual(actual.find(r=>r[0]===row.neighbor_id),[row.neighbor_id,row.before.status,row.after.status,String(row.added_contact_pairs.length),String(row.removed_contact_pairs.length)]);}
  assert.equal(await page.evaluate(()=>data.snapshot.revision),input.revision);
  await page.locator('#contactReview').screenshot({path:out+'/contacts.png'});
  Object.assign(report,{status:'PASS',displayed_rows:expected.length,changed_neighbors:context.new_or_extended_contacts,all_displayed_values_match:true,saved_case_unchanged:true,visual_review:'NOT RUN'});
 }catch(e){report.status='FAIL';report.error=String(e);process.exitCode=1;}
 finally{await browser.close();fs.writeFileSync(live?'docs/evidence/context-review-live-ui.json':'docs/evidence/context-review-ui.json',JSON.stringify(report,null,2)+'\n');}
 console.log(JSON.stringify(report));
})().catch(e=>{console.error(e);process.exitCode=1});
