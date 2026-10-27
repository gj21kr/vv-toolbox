const fs=require('node:fs');
const crypto=require('node:crypto');
const base='http://127.0.0.1:8093';
const optimized=process.argv.includes('--optimized');
const suffix=optimized?'-optimized':'';
(async()=>{
 const state=await (await fetch(base+'/api/state')).json();
 if(state.source!=='atlas'||state.busy||!state.atlas_centerlines.available)throw Error('Idle Atlas required');
 const graph=await (await fetch(base+'/api/atlas-centerlines')).json();
 const edges=graph.edges.filter(e=>e.part_id==='FJ1692');
 if(edges.length!==1)throw Error('Fixed single-edge target unavailable');
 const points=edges[0].points.slice(1,-1);
 let length=0;for(let i=1;i<points.length;i++)length+=Math.hypot(...points[i].map((v,k)=>v-points[i-1][k]));
 const body={part_id:'FJ1692',edge_id:edges[0].id,start_mm:length*.25,end_mm:length*.75,
  factor:.9,max_displacement_mm:.3,absolute_scale_tolerance:.02};
 const saved=()=>crypto.createHash('sha256').update(fs.readFileSync('reference-data/bodyparts3d/atlas-edits.snapshot.json')).digest('hex');
 const hash=saved(),start=Date.now();
 const response=await fetch(base+'/api/atlas-interval-preview',{method:'POST',
  headers:{'Content-Type':'application/json','X-Expected-Generation':String(state.generation)},
  body:JSON.stringify(body),signal:AbortSignal.timeout(600000)});
 const data=await response.json();
 const after=await (await fetch(base+'/api/state')).json();
 if(state.generation!==after.generation||JSON.stringify(state.atlas_modifications)!==JSON.stringify(after.atlas_modifications)||hash!==saved())
  throw Error('Original state changed');
 const result={scope:'Fixed actual Atlas interval request, no synthetic response',
  request:body,http_status:response.status,elapsed_ms:Date.now()-start,
  generation:state.generation,saved_atlas_sha256:hash,
  original_preserved:true,outcome:response.ok?'CANDIDATE':data};
 if(response.ok){fs.mkdirSync('exports/live-interval-preview'+suffix,{recursive:true});fs.writeFileSync('exports/live-interval-preview'+suffix+'/candidate.json',JSON.stringify(data));result.checks=data.checks}
 if(optimized&&response.ok){
  const prior=JSON.parse(fs.readFileSync('exports/live-interval-preview/candidate.json'));
  const earlier=JSON.parse(fs.readFileSync('docs/evidence/live-interval-preview.json'));
  result.comparison={same_request:JSON.stringify(body)===JSON.stringify(earlier.request),
   same_vertices:JSON.stringify(data.vertices)===JSON.stringify(prior.vertices),
   same_faces:JSON.stringify(data.faces)===JSON.stringify(prior.faces),
   same_section_checks:JSON.stringify(data.checks.section_targets)===JSON.stringify(prior.checks.section_targets),
   same_neighbor_rows:JSON.stringify(data.checks.neighbor_surface_contacts.rows)===JSON.stringify(prior.checks.neighbor_surface_contacts.rows),
   prior_elapsed_ms:earlier.elapsed_ms};
 }
 fs.writeFileSync('docs/evidence/live-interval-preview'+suffix+'.json',JSON.stringify(result,null,2)+'\n');
 console.log(JSON.stringify({http_status:result.http_status,outcome:result.outcome,
  elapsed_ms:result.elapsed_ms,original_preserved:result.original_preserved}));
})().catch(e=>{console.error(e);process.exitCode=1});
