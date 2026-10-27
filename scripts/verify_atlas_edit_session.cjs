// Run with a local Shiplight browser on CDP 9222 and the Atlas app on 8093.
const {chromium} = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const crypto = require('node:crypto');
const base = 'http://127.0.0.1:8093';
const combined = process.argv.includes('--combined');
const out = combined ? 'exports/atlas-edit-combined-verification' : 'exports/atlas-edit-session-verification';
const parameters = {radius_scale:1.3,tortuosity:combined ? .3 : 0,torsion_deg:combined ? 35 : 0};
const digest = value => crypto.createHash('sha256').update(JSON.stringify(value)).digest('hex');

(async () => {
  fs.mkdirSync(out, {recursive: true});
  const browser = await chromium.connectOverCDP('http://127.0.0.1:9222');
  try {
    const page = browser.contexts()[0].pages().find(p => p.url().startsWith(base+'/'));
    assert(page, 'Open the app in Shiplight first');
    page.setDefaultTimeout(60000);
    const get = async path => {
      const r = await page.request.get(base+path);
      assert.equal(r.status(), 200);
      return r.json();
    };
    const initial = await get('/api/state');
    const savedStatus = await get('/api/atlas-edit-session');
    assert.equal(initial.source, 'atlas');
    assert.deepEqual(initial.atlas_modifications, {}, 'Preserve existing user edits');
    assert.equal(savedStatus.file_exists, false, 'Preserve an existing saved session');
    const baseline = await get('/api/export');
    const originalEdges=baseline.centerlines.edges.filter(e=>e.part_id==='FJ1692');
    console.log('Ready: isolated storage, original geometry');
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    const click = async (selector, endpoint) => {
      const waiting = page.waitForResponse(r => r.url().endsWith(endpoint) && r.request().method()==='POST');
      await page.locator(selector).click();
      const response = await waiting;
      const data = await response.json();
      assert([200,202].includes(response.status()), JSON.stringify(data));
      return data;
    };
    await page.locator('#atlasModificationSearch').fill('FJ1692');
    const selection = page.waitForResponse(r => r.url().endsWith('/api/atlas-selection') && r.request().method()==='POST');
    await page.locator('#atlasModificationVessel').selectOption('FJ1692');
    assert([200,202].includes((await selection).status()));
    await page.waitForFunction(() => !document.querySelector('#atlasModificationControls').disabled);
    for(const [selector,key] of [['#atlasRadius','radius_scale'],['#atlasTortuosity','tortuosity'],['#atlasTorsion','torsion_deg']]){
      await page.locator(selector).evaluate((input,value) => {
        input.value=String(value);input.dispatchEvent(new Event('input',{bubbles:true}));
      },parameters[key]);
    }
    await click('#applyAtlasModification','/api/atlas-modification');
    const changed = await get('/api/export');
    assert.deepEqual(changed.modifications.FJ1692,parameters);
    const editedEdges=changed.centerlines.edges.filter(e=>e.part_id==='FJ1692');
    for(const original of originalEdges){
      const edited=editedEdges.find(e=>e.id===original.id);
      assert(edited,'Original edge must remain');
      assert.equal(edited.start,original.start);assert.equal(edited.end,original.end);
      for(const index of [0,original.points.length-1]){
        assert.deepEqual(edited.points[index],original.points[index]);
        assert.equal(edited.radii[index],original.radii[index]);
      }
    }
    console.log('Modified: parameters and endpoint anchors verified');
    const shapeDigest = digest(changed.modified_surfaces.FJ1692);
    const pathDigest = digest(changed.centerlines.edges.filter(e=>e.part_id==='FJ1692'));
    const saved = await click('#atlasEditsSave','/api/atlas-edit-session');
    assert(saved.saved_revision);
    console.log('Saved: restoring original then reloading');
    await click('#resetAtlasModification','/api/atlas-modification');
    assert.deepEqual((await get('/api/state')).atlas_modifications,{});
    await click('#atlasEditsReload','/api/atlas-edit-session');
    const restored = await get('/api/export');
    assert.equal(digest(restored.modified_surfaces.FJ1692),shapeDigest);
    assert.equal(digest(restored.centerlines.edges.filter(e=>e.part_id==='FJ1692')),pathDigest);
    await page.waitForFunction(p =>
      Number(document.querySelector('#atlasRadius').value)===p.radius_scale &&
      Number(document.querySelector('#atlasTortuosity').value)===p.tortuosity &&
      Number(document.querySelector('#atlasTorsion').value)===p.torsion_deg &&
      !document.querySelector('#atlasModificationControls').disabled,parameters);
    await page.locator('#atlasEditsMessage').scrollIntoViewIfNeeded();
    await page.screenshot({path:out+'/restored-vessel-edits.png'});
    const stale = await page.request.post(base+'/api/atlas-edit-session', {
      data:{action:'reload',expected_generation:initial.generation},
    });
    assert.equal(stale.status(),409);
    assert.equal(digest((await get('/api/export')).modified_surfaces.FJ1692),shapeDigest);
    // End at the user's original unmodified geometry; no test deformation remains.
    await click('#resetAtlasModification','/api/atlas-modification');
    await click('#atlasEditsSave','/api/atlas-edit-session');
    assert.deepEqual((await get('/api/state')).atlas_modifications,{});
    assert.deepEqual(errors,[]);
    const report={status:'PASS',part_id:'FJ1692',parameters,
      endpoint_positions_and_radii_preserved:true,
      save_restore_reload:true,restored_surface_sha256:shapeDigest,
      restored_centerline_sha256:pathDigest,stale_generation_rejected:true,
      original_geometry_restored_at_end:true,page_errors:errors,
      scope:'Atlas parameter persistence and derived geometry replay; anatomical and collision validity not assessed'};
    fs.writeFileSync(out+'/result.json',JSON.stringify(report,null,2)+'\n');
    console.log(JSON.stringify(report));
  } finally { await browser.close(); }
})().catch(error=>{console.error(error);process.exitCode=1;});
