// Browser-only verification against a local, already running CDP session.
const { chromium } = require('playwright');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');

(async () => {
  const browser = await chromium.connectOverCDP('http://127.0.0.1:9222');
  let restoreDraft = null;
  try {
    const page = browser.contexts()[0].pages().find(p => p.url().startsWith('http://127.0.0.1:8093/'));
    assert(page, 'Open local VV Toolbox page required');
    page.setDefaultTimeout(60000);
    await page.reload({ waitUntil: 'domcontentloaded', timeout: 60000 });
    console.log('Page reloaded');
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    const before = await (await page.request.get('http://127.0.0.1:8093/api/atlas-annotations')).json();
    const boundaryId = 'B.L.ACA.A1_A2';
    const previous = before.document.boundaries.find(b => b.boundary_id === boundaryId);
    const priorCandidate = before.candidate_positions[boundaryId] ?? null;
    assert.equal(previous.evidence_status, 'unresolved');
    restoreDraft = async () => {
      const current = await (await page.request.get('http://127.0.0.1:8093/api/atlas-annotations')).json();
      const response = await page.request.post('http://127.0.0.1:8093/api/atlas-annotations', { data: {
        revision: current.revision, boundary_id: boundaryId, reason: previous.reason,
        review_note: previous.review_note, source_refs: previous.source_refs, candidate_position: priorCandidate,
      }});
      assert.equal(response.status(), 200);
    };
    await page.locator('#boundarySelect').selectOption(boundaryId);
    console.log('Boundary selected');
    const xyz = [2.06185, -113.234, 1538.05];
    for (const [i, axis] of ['X', 'Y', 'Z'].entries())
      await page.locator('#boundary' + axis).fill(String(xyz[i]));
    await page.locator('#boundaryNote').fill('Browser verification: inspected ACom surface navigation candidate, not an approved junction.');
    await page.locator('#boundaryRefs').fill('docs/evidence/cerebral-boundary-adjudication.json');
    const saved = page.waitForResponse(r => r.url().endsWith('/api/atlas-annotations') && r.request().method() === 'POST');
    await page.locator('#boundarySave').click();
    assert.equal((await saved).status(), 200);
    console.log('Draft saved');
    await page.locator('#boundaryReload').click();
    await page.waitForFunction(() => document.querySelector('#boundaryX').value === '2.06185');
    const state = await (await page.request.get('http://127.0.0.1:8093/api/atlas-annotations')).json();
    assert.deepEqual(state.candidate_positions[boundaryId], xyz);
    assert.equal(state.document.boundaries.find(b => b.boundary_id === boundaryId).position, null);
    await page.locator('#boundaryContext').check();
    const focused = page.waitForResponse(r => r.url().endsWith('/api/annotation-focus'));
    await page.locator('#boundaryFocus').click();
    assert.equal((await focused).status(), 202);
    await page.locator('#boundaryFocus').scrollIntoViewIfNeeded();
    fs.mkdirSync('exports/annotation-ui', { recursive: true });
    await page.screenshot({ path: 'exports/annotation-ui/boundary-draft.png', timeout: 60000 });
    // Restore the user's previous draft; verification does not approve or retain test notes.
    await restoreDraft();
    restoreDraft = null;
    await page.locator('#boundaryReload').click();
    assert.deepEqual(errors, []);
    console.log(JSON.stringify({ saved_reloaded: true, authoritative_position_null: true,
      context_toggle: true, focus: true, draft_restored: true, page_errors: errors,
      screenshot: path.resolve('exports/annotation-ui/boundary-draft.png') }));
  } finally {
    try { if (restoreDraft) await restoreDraft(); }
    finally { await browser.close(); }
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
