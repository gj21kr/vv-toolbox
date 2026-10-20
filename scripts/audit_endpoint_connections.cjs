// Read-only audit of the running atlas; no selection or geometry changes.
const fs = require('node:fs');
const vm = require('node:vm');
const crypto = require('node:crypto');
async function main() {
  const base = process.env.VV_AUDIT_URL || 'http://127.0.0.1:8093';
  const read = async path => { const r=await fetch(base+path); if(!r.ok)throw Error(`${path}: ${r.status}`); return r.json(); };
  const offline=process.argv[3];
  const state = offline?{}:await read('/api/state');
  const data = offline?JSON.parse(fs.readFileSync(offline,'utf8')):await read('/api/atlas-centerlines');
  if ((!offline&&!data.available) || !Array.isArray(data.edges)) throw Error('Centerlines not ready');
  const source=fs.readFileSync('src/vv_toolbox/web_ui.py','utf8');
  const helper='function endpointNeighborhood('+source.split('function endpointNeighborhood(')[1].split('function drawEndpointConnections(')[0];
  const fn=vm.runInNewContext(helper+';endpointNeighborhood');
  const edges=new Map(data.edges.map(e=>[e.id,e]));
  const nodes=new Map(data.nodes.map(n=>[n.id,n]));
  const dist=(a,b)=>Math.hypot(...a.map((v,i)=>v-b[i]));
  const errors=[];
  for(const e of data.edges) {
    if(!nodes.has(e.start)||!nodes.has(e.end))errors.push(['missing_node',e.id]);
    if(e.points.length!==e.radii.length)errors.push(['radius_count',e.id]);
  }
  for(const l of data.links) {
    if(!nodes.has(l.start)||!edges.has(l.target_edge))errors.push(['missing_link_anchor',l.id]);
    else if(nodes.get(l.start).part_id!==l.part_a||edges.get(l.target_edge).part_id!==l.part_b)errors.push(['owner_mismatch',l.id]);
  }
  const perPart=data.parts.map(p=>{const r=fn(data,p.id);return {id:p.id,groups:r.groups.length,empty:r.groups.filter(g=>!g.neighbors.length).length,unassigned:r.unassigned};});
  const selected=process.argv[2]||state.atlas_selection||'FJ1718';
  const neighborhood=fn(data,selected);
  const rows=[];
  for(const group of neighborhood.groups)for(const [neighbor,l]of group.neighbors) {
    const target=edges.get(l.target_edge),p=l.target_point||nodes.get(l.end)?.point;
    let i=0;for(let k=1;k<target.points.length;k++)if(dist(target.points[k],p)<dist(target.points[i],p))i=k;
    const arc=[0];for(let k=1;k<target.points.length;k++)arc.push(arc[k-1]+dist(target.points[k-1],target.points[k]));
    rows.push({group:group.id,neighbor,link:l.id,source:l.part_a,target:l.part_b,distance:l.distance,surface_gap_proxy:l.surface_gap_proxy,target_path_fraction:arc[i]/arc.at(-1),target_distance_to_nearest_end:Math.min(arc[i],arc.at(-1)-arc[i]),reference:data.reference_topology?.candidate_assessments?.find(a=>a.link_id===l.id)?.status});
  }
  const report={timestamp:new Date().toISOString(),selected,modifications:state.atlas_modifications,algorithm:data.algorithm,smoothing:data.smoothing,graph_sha256:crypto.createHash('sha256').update(JSON.stringify(data)).digest('hex'),counts:{parts:data.parts.length,edges:data.edges.length,links:data.links.length,invalid:errors.length,parts_with_unassigned:perPart.filter(p=>p.unassigned).length,parts_without_anchors:perPart.filter(p=>!p.groups).length,empty_anchor_groups:perPart.reduce((n,p)=>n+p.empty,0)},errors,selected_candidates:rows,parts_with_unassigned:perPart.filter(p=>p.unassigned)};
  console.log(JSON.stringify(report,null,2));
}
main().catch(e=>{console.error(e);process.exitCode=1;});
