const fs = require('node:fs');
const crypto = require('node:crypto');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const base = 'http://127.0.0.1:8093';
const digest = () => crypto.createHash('sha256').update(
  fs.readFileSync(path.join(root, 'reference-data/bodyparts3d/atlas-edits.snapshot.json'))).digest('hex');
const assert = (condition, message) => { if (!condition) throw new Error(message); };
(async () => {
  const before = await (await fetch(base + '/api/state')).json();
  assert(before.source === 'atlas' && !before.busy && before.atlas_centerlines.available,
    'Idle Atlas with available centerlines required');
  const saved = digest();
  const results = [];
  async function request(name, body, headers, expected) {
    const response = await fetch(base + '/api/atlas-interval-preview', {
      method: 'POST', headers: {'Content-Type': 'application/json', ...headers},
      body: JSON.stringify(body), signal: AbortSignal.timeout(180000)
    });
    const content = await response.json();
    assert(response.status === expected, `${name}: ${response.status} ${JSON.stringify(content)}`);
    results.push({name, status: response.status, response: content});
  }
  await request('missing_generation', {}, {}, 409);
  const headers = {'X-Expected-Generation': String(before.generation)};
  await request('invalid_input', {}, headers, 400);
  await request('foreign_origin', {}, {...headers, Origin: 'http://example.invalid'}, 403);
  const graph = await (await fetch(base + '/api/atlas-centerlines')).json();
  const edges = graph.edges.filter(e => e.part_id === 'FJ1692');
  assert(edges.length === 1 && edges[0].points.length >= 5, 'Frozen negative-probe vessel unavailable');
  await request('actual_atlas_displacement_rejection', {
    part_id: 'FJ1692', edge_id: edges[0].id, start_mm: 1, end_mm: 2, factor: .9,
    max_displacement_mm: 1e-12, absolute_scale_tolerance: .01
  }, headers, 422);
  const after = await (await fetch(base + '/api/state')).json();
  assert(after.generation === before.generation, 'Generation changed');
  assert(JSON.stringify(after.atlas_modifications) === JSON.stringify(before.atlas_modifications),
    'Active modifications changed');
  assert(digest() === saved, 'Saved Atlas changed');
  const report = {status: 'PASS', scope: 'HTTP rejection and state preservation, not accepted-edit rendering',
    results, generation: before.generation, saved_atlas_sha256: saved,
    accepted_preview: 'NOT RUN', browser_rendering: 'NOT RUN'};
  fs.writeFileSync(path.join(root, 'docs/evidence/interval-preview-http.json'),
    JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify({status: report.status, checks: results.map(r => [r.name, r.status])}));
})().catch(error => { console.error(error); process.exitCode = 1; });
