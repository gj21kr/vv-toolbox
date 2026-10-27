// Browser-only verification against a local Shiplight CDP session.
const {chromium} = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const base = 'http://127.0.0.1:8093';

(async () => {
  const browser = await chromium.connectOverCDP('http://127.0.0.1:9222');
  try {
    const page = browser.contexts()[0].pages().find(p => p.url().startsWith('http://127.0.0.1:8093/'));
    assert(page);
    page.setDefaultTimeout(60000);
    const errors = [];
    page.on('pageerror', e => errors.push(e.message));
    const initial = await (await page.request.get(base+'/api/case-workspace')).json();
    if (initial.file_exists) throw new Error('Use a fresh verification snapshot; preserve existing saved data');
    const before = await (await page.request.get(base+'/api/state')).json();
    async function click(id) {
      const response = page.waitForResponse(r => r.url().endsWith('/api/case-workspace') && r.request().method() === 'POST');
      await page.locator(id).click();
      const r = await response;
      const body = await r.json();
      assert.equal(r.status(), 200, JSON.stringify(body));
      return body;
    }
    await page.locator('#casePrepare').scrollIntoViewIfNeeded();
    const prepared = await click('#casePrepare');
    assert(prepared.summary.edges > 1000);
    assert.equal(prepared.rendered, false);
    assert.equal(prepared.includes_atlas_edits, false);
    const saved = await click('#caseSave');
    assert(saved.saved_revision);
    const loaded = await click('#caseReload');
    assert.equal(saved.summary.digest, loaded.summary.digest);
    const stale = await page.request.post(base+'/api/case-workspace', {data:{action:'save',version:initial.version}});
    assert.equal(stale.status(),409);
    const downloaded = await (await page.request.get(base+'/api/case-download')).json();
    assert.equal(downloaded.revision, loaded.summary.digest);
    assert.equal(downloaded.case.edges.length, loaded.summary.edges);
    const after = await (await page.request.get(base+'/api/state')).json();
    assert.equal(before.generation, after.generation);
    await page.locator('#caseSummary').scrollIntoViewIfNeeded();
    await page.screenshot({path:'exports/case-app-verification/source-case-workspace.png'});
    assert.deepEqual(errors, []);
    const report = {prepare:true,save_reload_equal:true,stale_revision_rejected:true,
      download_equal:true,scene_generation_unchanged:true,edges:loaded.summary.edges,
      unresolved_edges:loaded.summary.unresolved_edges,page_errors:errors};
    fs.writeFileSync('exports/case-app-verification/browser-result.json',JSON.stringify(report,null,2));
    console.log(JSON.stringify(report));
  } finally { await browser.close(); }
})().catch(e=>{console.error(e);process.exitCode=1;});
