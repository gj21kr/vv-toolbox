"""Self-contained browser shell; no remote assets."""
HTML = r'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>VV Toolbox</title>
<style>
[hidden]{display:none!important}
*{box-sizing:border-box}body{margin:0;background:#10191f;color:#e3eeef;font:13px system-ui}header{height:66px;padding:12px 20px;border-bottom:1px solid #31414a;display:flex;align-items:center;gap:20px}h1{font-size:21px;margin:0}small{color:#9fb6bd}.badge{font-size:10px;letter-spacing:1px;color:#74ded2;border:1px solid #36655f;border-radius:20px;padding:5px 9px}main{display:grid;grid-template-columns:440px 1fr;height:calc(100vh - 66px)}aside{overflow:auto;border-right:1px solid #31414a;padding:15px}h2{font-size:15px;margin:8px 0}p{color:#a8bdc3;line-height:1.5}label{display:block;margin:9px 0 4px;color:#bdcdd1}select,button,input{font:inherit}select,button{background:#20323b;border:1px solid #425960;color:#ecf6f6;border-radius:6px;padding:8px;width:100%}button{cursor:pointer}button:hover{border-color:#5bcec5}button.primary{background:#23665f}button:disabled{opacity:.45;cursor:wait}input[type=range]{width:100%;accent-color:#59c9bd}input[type=checkbox]{accent-color:#59c9bd}fieldset{border:0;padding:0;margin:0}details{border-top:1px solid #30454d;margin-top:12px;padding-top:12px}summary{cursor:pointer;font-weight:600}.row{display:flex;gap:8px}.row>*{flex:1;min-width:0}.graphbox{height:350px;overflow:auto;border:1px solid #30454d;border-radius:8px;margin-top:10px;background:#14222a}svg{display:block;width:100%;min-width:390px}.edge{stroke:#477e85;stroke-width:2;fill:none}.hit{stroke:transparent;stroke-width:16;fill:none;cursor:pointer}.edge.selected{stroke:#ffb278;stroke-width:4}.edgeLabel{fill:#d5e7ea;font-size:10px;cursor:pointer;paint-order:stroke;stroke:#14222a;stroke-width:4px}.node{fill:#89d0c9;cursor:pointer}.nodeLabel{fill:#8da4af;font-size:8px;pointer-events:none}.selectedName{color:#ffc190;font-weight:600;overflow-wrap:anywhere}#stage{position:relative;min-width:0}iframe{width:100%;height:100%;border:0}#veil{position:absolute;inset:0;background:#0e1d25d9;display:grid;place-items:center;z-index:4;font-size:20px;text-align:center}#veil[hidden]{display:none}#status{margin-left:auto;font-size:12px;color:#9fd7cf}output{float:right;color:#fff}a{color:#71d9cf}.tip{font-size:11px}#error{color:#ffab99;white-space:pre-wrap}@media(max-width:850px){main{grid-template-columns:350px 1fr}aside{padding:10px}}@media(max-width:650px){main{display:flex;flex-direction:column;height:auto}aside{height:55vh}#stage{height:65vh}header{gap:8px;padding:8px}.badge{display:none}.graphbox{height:270px}}
.graphbox{overflow-x:hidden}svg{min-width:0}.edgeLabel{font-size:10px;pointer-events:none}.hit{pointer-events:stroke}.edgeButton{fill:transparent;pointer-events:all;cursor:pointer}.edgeButton:focus{outline:none;stroke:#ffc190;stroke-width:1;fill:#ffc19018}.laneTitle{fill:#8fc9c5;font-size:11px;font-weight:600}.leader{stroke:#45606a;stroke-width:1;stroke-dasharray:2 3;pointer-events:none}
.edge{stroke:var(--vessel-color,#e64c53)}.node{fill:var(--vessel-color,#e64c53)}
.notice{padding:10px;border:1px solid #7a6340;background:#332b20;color:#eed3a8;border-radius:6px;font-size:11px;line-height:1.5}.provenance{font-size:11px;line-height:1.6;overflow-wrap:anywhere}.provenance dt{color:#9fb6bd;margin-top:7px}.provenance dd{margin:0}.classBadge{display:block;margin:6px 0;color:#9fe0cd}.classBadge.mismatch{color:#ffb281}[hidden]{display:none!important}
body{font-size:14px}main{grid-template-columns:420px 1fr}aside{padding:14px;background:#101b22}.atlasCard{padding:14px;background:#16252e;border:1px solid #30454e;border-radius:10px;margin-bottom:12px}.atlasCard h2{font-size:16px;margin:0 0 10px}.tip,.provenance{font-size:12px}.notice{font-size:12px}.atlasCard p{margin:8px 0}.atlasCard label{font-size:13px}.atlasList{max-height:190px;overflow:auto;margin-top:10px;border-top:1px solid #30454e}.atlasList ul{margin:6px 0;padding-left:0;list-style:none}.atlasList button{font-size:13px;padding:8px 10px;line-height:1.4}.atlasList strong{font-size:12px;color:#9db8bf}.atlasCard .graphbox{height:auto;max-height:430px;margin-top:8px}.atlasCard input[type=range]{margin:8px 0 14px}.atlasCard details{font-size:12px}.atlasCard .row button{font-size:12px}.relationshipNode:focus rect{stroke:#fff;stroke-width:3}#atlasRelationSummary{font-size:12px;color:#a9c4ce}#atlasModificationPanel>.notice{border:0;background:none;padding:0;color:#a8bdc3}#legacyWorkspace{display:none!important}@media(max-width:850px){main{grid-template-columns:380px 1fr}}@media(max-width:650px){main{display:flex}aside{height:55vh}}
</style>
<style>
#atlasBrowse{display:grid;grid-template-columns:1fr 1.3fr;column-gap:10px}
#atlasBrowse label[for=atlasRegion]{grid-column:1;grid-row:1}
#atlasRegion{grid-column:1;grid-row:2}
#atlasBrowse label[for=atlasSearch]{grid-column:2;grid-row:1}
#atlasSearch{grid-column:2;grid-row:2;background:#20323b;color:#ecf6f6;border:1px solid #425960;border-radius:6px;min-width:0}
#atlasBrowse p{grid-column:1/-1}
#atlasCenterlinePanel .graphbox{height:auto!important;overflow:hidden;max-height:none}
#atlasModificationPanel .row button{font-size:13px;padding:10px}
</style>
<header><div><h1>VV Toolbox · Atlas</h1><small id="scopeSubtitle">Femoral → cerebral</small></div><span id="sourceBadge" class="badge" hidden>ATLAS</span><span id="status">Connecting…</span></header>
<main><aside><nav aria-label="Workspace mode" class="row"><button id="openEditor" aria-pressed="true">Graph &amp; vessel modification</button><button id="openAtlas" aria-pressed="false">Atlas reference</button></nav><p id="workspaceNote" class="tip"></p><h2 id="graphHeading">Branch graph</h2><p id="graphDescription" class="tip">Select a layer and vessel to edit its shape or connections.</p>
<label for="source">Anatomy source</label><select id="source"><option value="schematic">Authored schematic · editable</option><option id="referenceOption" value="reference" disabled>Standalone reference arch · unavailable</option><option id="atlasOption" value="atlas" disabled>BodyParts3D · shared-coordinate atlas</option></select><p id="sourceReason" class="tip"></p>
<details id="atlasInspector" hidden><summary>Atlas provenance</summary><p class="tip">Structures retain their shared atlas coordinates. One anatomical atlas is not a population model or a verified vascular lumen.</p><dl id="atlasFacts" class="provenance"></dl></details>
<details id="referenceInspector"><summary>Reference provenance & measurements</summary><p id="referenceDescription" class="tip">No reference has been registered.</p><dl id="referenceFacts" class="provenance"></dl><div id="referenceMetrics" class="provenance"></div></details>
<label id="layerLabel" for="layer">Vessel layer</label><select id="layer"><option value="arterial">Arteries</option><option value="systemic_venous">Systemic veins</option><option value="hepatic_portal">Hepatic portal veins</option></select>
<div class="row"><label><input id="show_arterial" type="checkbox" checked>Arteries</label><label><input id="show_systemic_venous" type="checkbox" checked>Systemic veins</label><label><input id="show_hepatic_portal" type="checkbox" checked>Portal veins</label></div>
<label id="atlasContextLabel" hidden><input id="atlasContext" type="checkbox" checked>Heart / organ context</label>
<div id="neckRepairsPanel" hidden><label><input id="neckRepairs" type="checkbox" checked>Estimated missing vessels</label><p id="neckRepairsNote" class="notice">Missing neck connections and cerebral veins are estimated additions; not validated anatomy.</p><p class="tip">All arteries are red and veins are blue, including estimated additions. Estimated vessels retain their labels. Uncheck to inspect the original atlas alone.</p><details><summary>Reconstruction limits</summary><p id="neckRepairsMethod" class="tip"></p><p id="neckRepairsLimits" class="tip"></p><p id="neckRepairsUnresolved" class="tip"></p><ul id="repairGapDetails" class="provenance"></ul><p class="tip">Named estimated venous segments (authored topology, not recovered source vessels):</p><ul id="repairSegments" class="provenance"></ul></details></div>
<section id="clearancePanel"><p id="clearanceStatus" class="tip" role="status">Inter-circuit clearance: awaiting screening.</p><p class="tip">Centerline/radius estimate · not surface or anatomical validation.</p><details id="clearanceDetails"><summary>Clearance screening details</summary><p class="tip">Centerline/radius screening only. This is not an exact surface-intersection test or anatomical validation. Negative clearance indicates a potential overlap.</p><p id="clearanceMethod" class="tip"></p><ul id="clearanceConflicts" class="provenance"></ul><p id="clearanceLimits" class="tip"></p></details></section>
<p class="tip" id="layerNote">Red arteries · blue systemic veins · light blue portal veins. Portal and systemic veins remain separate across the unmodeled liver exchange.</p>
<select id="region" aria-label="Graph region"><option>All regions</option><option selected>Cerebral</option><option>Aortic arch</option><option>Abdominal</option><option>Femoral</option></select>
<p id="cerebralNotice" class="notice">A1–A3, M1–M3 and P1–P3 are estimated schematic subdivisions. Landmark-based annotation has not been validated.</p>
<div id="atlasBrowse" hidden><label for="atlasRegion">Atlas region</label><select id="atlasRegion"><option>Whole body</option><option>Head &amp; neck</option><option>Thorax</option><option>Abdomen</option><option>Pelvis &amp; femoral</option></select><label for="atlasSearch">Find a structure</label><input id="atlasSearch" type="search" placeholder="Vessel name or atlas ID" style="width:100%;padding:8px"><p class="tip">Approximate spatial filter using source bounds. Select a structure to highlight and focus it in 3D.</p><p id="atlasCount" class="tip"></p><p id="atlasSelection" class="selectedName" role="status"></p></div>
<section id="atlasCenterlinePanel" hidden><label><input id="atlasCenterlinesVisible" type="checkbox">Atlas centerlines</label><p id="atlasCenterlineStatus" class="tip" role="status">Centerline extraction not available.</p><p class="tip">Solid: within-part centerlines derived from meshes (or explicitly estimated vessels). Dashed: unverified proximity candidates between parts. These are not confirmed anatomical connections.</p><a id="atlasCenterlineDownload" href="/api/atlas-centerlines" download="atlas-centerlines.json" hidden>Download centerline graph JSON</a><div class="graphbox" style="height:290px"><svg id="atlasCenterlineGraph" role="img" aria-label="Atlas centerline neighborhood"></svg></div></section>
<section id="atlasModificationPanel" hidden><h2>Atlas vessel modification</h2><p id="atlasModificationName" class="selectedName">Select an atlas vessel</p><fieldset id="atlasModificationControls" disabled><label for="atlasRadius">Radius multiplier <output id="atlasRadiusOut">1.00</output></label><input id="atlasRadius" type="range" min="0.5" max="2" step="0.05" value="1"><label for="atlasTortuosity">Tortuosity adjustment <output id="atlasTortuosityOut">0.00</output></label><input id="atlasTortuosity" type="range" min="-1" max="1" step="0.05" value="0"><label for="atlasTorsion">Torsion adjustment (degrees) <output id="atlasTorsionOut">0°</output></label><input id="atlasTorsion" type="range" min="-180" max="180" step="5" value="0"><div class="row"><button id="applyAtlasModification" class="primary">Apply atlas modification</button><button id="resetAtlasModification">Restore selected original</button></div></fieldset><p id="atlasModificationStatus" class="tip" role="status"></p><p class="notice">Edits create a local derived shape; restore returns this vessel to its original geometry. Endpoint and junction preservation is approximate. Collisions and anatomical validity are not validated.</p></section>
<div class="graphbox"><svg id="graph" role="img" aria-label="Interactive vessel connectivity graph"></svg><ul id="atlasParts" class="provenance" hidden></ul></div>
<label id="vesselLabel" for="vessel">Selected vessel</label><select id="vessel"></select>
<fieldset id="controls"><h2 class="selectedName" id="selectedName">Choose a vessel</h2>
<div id="shapeControls">
<label>Radius multiplier <output id="radiusOut">1.00</output></label><input id="radius" aria-label="Selected vessel radius" type="range" min="0.5" max="2" step=".05" value="1">
<label>Tortuosity <output id="tortOut">0.30</output></label><input id="tort" aria-label="Selected vessel tortuosity" type="range" min="0" max="1" step=".05" value=".3">
<div class="row"><button id="applyVessel" class="primary">Apply vessel shape</button><button id="resetVessel">Reset vessel</button></div>
</div><p id="referenceReadOnly" class="notice" hidden>Standalone reference geometry is read-only. It is not joined to the authored whole-body network.</p>
<details id="variation" open><summary>Arterial branch variations</summary>
<label>Arch connections</label><select id="variant"><option value="standard">Standard arch</option><option value="common_origin">Shared brachiocephalic / left carotid origin</option><option value="left_carotid_from_brachiocephalic">Left carotid from brachiocephalic</option><option value="left_vertebral_from_arch">Left vertebral from arch</option></select>
<label>Arch shape preset</label><select id="archType"><option value=".5">Type I illustration</option><option value="1.5">Type II illustration</option><option value="2.5">Type III illustration</option><option value="custom">Custom degree</option></select>
<label>Requested arch depth <output id="archOut">0.50</output></label><input id="arch" aria-label="Requested arch depth ratio" type="range" min=".25" max="3.5" step=".05" value=".5">
<p class="tip">Continuous synthetic construction ratio; presets illustrate types and do not classify clinical anatomy. <span id="measured"></span></p>
<span id="archClass" class="classBadge" role="status"></span>
<div class="row"><label><input type="checkbox" id="acom" checked>ACom</label><label><input type="checkbox" id="left_pcom" checked>Left PCom</label><label><input type="checkbox" id="right_pcom" checked>Right PCom</label></div>
<button id="applyVariation" class="primary">Apply branch variation</button></details>
<details id="venousVariation" hidden open><summary>Venous variations</summary><label for="imv">Inferior mesenteric vein drainage</label><select id="imv"><option value="splenic">Splenic vein</option><option value="superior_mesenteric">Superior mesenteric vein</option><option value="confluence">Portal confluence</option></select><label for="dominance">Transverse sinus dominance</label><select id="dominance"><option value="balanced">Balanced</option><option value="left">Left dominant</option><option value="right">Right dominant</option></select><p class="tip">IMV changes portal connections. Dominance adjusts the synthetic cerebral sinus caliber.</p><button id="applyVenous" class="primary">Apply venous variation</button></details>
<details><summary>View & arterial route</summary><div id="routeControls"><label>Femoral access</label><select id="access"><option value="right_femoral">Right femoral</option><option value="left_femoral">Left femoral</option></select><label>Cerebral destination</label><select id="target"></select></div><label>Focus</label><select id="focus"><option>Whole network</option><option>Aortic arch</option><option>Cerebral</option><option>Femoral bifurcation</option><option>Abdominal</option></select><label>Geometry</label><select id="mode"><option>Surface</option><option>Centerlines</option></select><button id="applyView">Update view</button></details>
<details><summary>Workspace</summary><p class="tip">All browser tabs share this model. Graph and surface update together after a rebuild.</p><button id="resetAll">Reset anatomy</button><p><a href="/api/export" download="vv-synthetic-graph.json">Download graph JSON</a></p></details>
<details><summary>About this anatomy</summary><p class="tip">Authored illustrative arteries, systemic veins and hepatic portal veins. The liver exchange between portal and systemic compartments is not a connecting vessel. Not patient anatomy, validated flow, catheter contact or clinical planning. Coral lines show the arterial undirected shortest route. Coordinates use mm.</p></details></fieldset><p id="error" role="alert"></p>
</aside><section id="stage"><iframe title="Interactive 3D vessel model" src="http://127.0.0.1:__VISER_PORT__"></iframe><details id="sceneLegend" open hidden style="position:absolute;left:12px;bottom:12px;z-index:3;max-width:360px;width:calc(100% - 24px);max-height:40%;overflow:auto;background:#10191fee;border:1px solid #607985;border-radius:8px;padding:12px;margin:0"><summary>Model information</summary><div id="sceneLegendText"></div></details><div id="veil">Building anatomy…</div></section></main>
<script>
const $=id=>document.getElementById(id); let state=null, selected='left_aca_a1',generation=-1,pending=false,referenceRendered='',clearanceRendered='';
// Keep legacy controls detached from the visible Atlas workspace for API compatibility.
const sidebar=document.querySelector('aside'),legacy=document.createElement('div');legacy.id='legacyWorkspace';legacy.hidden=true;while(sidebar.firstChild)legacy.append(sidebar.firstChild);sidebar.append(legacy);
const atlasWorkspace=document.createElement('div');atlasWorkspace.id='atlasWorkspace';sidebar.append(atlasWorkspace);
function atlasCard(title){const card=document.createElement('section');card.className='atlasCard';if(title){const heading=document.createElement('h2');heading.textContent=title;card.append(heading)}atlasWorkspace.append(card);return card}
const availability=atlasCard('Atlas workspace');availability.id='atlasAvailability';availability.textContent='Loading Atlas…';
const browseCard=atlasCard('1 · Select a vessel');browseCard.append($('atlasBrowse'));const vesselList=document.createElement('div');vesselList.className='atlasList';vesselList.append($('atlasParts'));const listDetails=document.createElement('details'),listTitle=document.createElement('summary');listTitle.textContent='Browse matching vessels';listDetails.open=true;listDetails.append(listTitle,vesselList);browseCard.append(listDetails);$('atlasBrowse').querySelector('.tip').hidden=true;
const relationCard=atlasCard('2 · Vessel relationships');relationCard.append($('atlasCenterlinePanel'));const relationSummary=document.createElement('p');relationSummary.id='atlasRelationSummary';$('atlasCenterlinePanel').prepend(relationSummary);
const relationMode=document.createElement('select');relationMode.id='atlasRelationMode';relationMode.setAttribute('aria-label','Relationship evidence');relationMode.append(new Option('Literature reference · junctions','reference'),new Option('Spatial candidates · unverified','proximity'));relationMode.onchange=()=>drawAtlasCenterlines();relationSummary.before(relationMode);
const relationEvidence=document.createElement('div');relationEvidence.id='atlasRelationEvidence';relationSummary.after(relationEvidence);
relationMode.insertBefore(new Option('Selected vessel · both ends','ends'),relationMode.firstChild);relationMode.value='ends';
const connectionOverview=document.createElement('div');connectionOverview.id='atlasConnectionOverview';relationEvidence.after(connectionOverview);
const extractionDetails=document.createElement('details'),extractionTitle=document.createElement('summary');extractionTitle.textContent='Centerline extraction details';extractionDetails.append(extractionTitle,$('atlasCenterlineStatus'),$('atlasCenterlineDownload'));for(const p of [...$('atlasCenterlinePanel').querySelectorAll(':scope > p.tip')])extractionDetails.append(p);$('atlasCenterlinePanel').append(extractionDetails);
const modificationCard=atlasCard('');modificationCard.append($('atlasModificationPanel'));$('atlasModificationPanel').querySelector('h2').textContent='3 · Modify selected vessel';$('applyAtlasModification').textContent='Apply modification';$('resetAtlasModification').textContent='Restore original';
const editSessionPanel=document.createElement('div');editSessionPanel.style.cssText='border-top:1px solid #425960;margin-top:16px;padding-top:12px';
editSessionPanel.innerHTML='<h3>Save vessel edits</h3><p class="tip">Save all vessel adjustments locally. Reload replaces current adjustments and restores their 3D shapes and centerlines. Original Atlas files are preserved.</p><div class="row"><button id="atlasEditsSave" disabled>Save vessel edits</button><button id="atlasEditsReload" disabled>Reload saved edits</button></div><p id="atlasEditsStatus" role="status">Loading saved-edit status…</p><p id="atlasEditsMessage" role="status"></p>';
$('atlasModificationPanel').append(editSessionPanel);
let editSessionState=null,editSessionPending=false,editSessionGeneration='';
function showEditSessionStatus(){
 const count=Object.keys(state?.atlas_modifications||{}).length;
 $('atlasEditsStatus').textContent=editSessionState?`${count} modified vessel(s) · ${editSessionState.error||(!editSessionState.file_exists?'no local save':editSessionState.dirty?'changes since local save':'matches local save')}. Shape validity and collisions remain unverified.`:'Saved-edit status unavailable.';
 const disabled=editSessionPending||pending||!isAtlas()||!state?.atlas_centerlines?.available||!editSessionState?.available;
 $('atlasEditsSave').disabled=disabled||!editSessionState;
 $('atlasEditsReload').disabled=disabled||!editSessionState?.file_exists;
}
async function refreshEditSessionStatus(){try{
 const response=await fetch('/api/atlas-edit-session',{cache:'no-store'}),data=await response.json();
 if(!response.ok)throw Error(data.error);editSessionState=data;showEditSessionStatus();
 }catch(error){editSessionState=null;showEditSessionStatus();$('atlasEditsMessage').textContent=error.message}}
async function editSessionAction(action){
 if(editSessionPending||pending||!state)return;
 editSessionPending=true;busy(true);showEditSessionStatus();$('atlasEditsMessage').textContent=action==='reload'?'Restoring saved vessel shapes…':'Saving vessel adjustments…';
 try{const response=await fetch('/api/atlas-edit-session',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action,expected_generation:state.generation})}),data=await response.json();
 if(!response.ok)throw Error(data.error||'Could not update saved edits');editSessionState=data;
 $('atlasEditsMessage').textContent=action==='save'?'Vessel adjustments saved locally.':'Saved adjustments restored in 3D and centerlines.';
 }catch(error){$('atlasEditsMessage').textContent=error.message}
 finally{editSessionPending=false;busy(false);await poll();await refreshEditSessionStatus()}
}
$('atlasEditsSave').onclick=()=>editSessionAction('save');$('atlasEditsReload').onclick=()=>editSessionAction('reload');
const modificationLabel=document.createElement('label');modificationLabel.htmlFor='atlasModificationVessel';modificationLabel.textContent='Vessel selection';
const modificationSelect=document.createElement('select');modificationSelect.id='atlasModificationVessel';modificationSelect.title='Select the vessel to modify';
const modificationSearch=document.createElement('input');modificationSearch.id='atlasModificationSearch';modificationSearch.type='search';modificationSearch.placeholder='Name, ID or abbreviation · e.g. left ACom';modificationSearch.setAttribute('aria-label','Search vessels to modify');modificationSearch.style.cssText='width:100%;padding:10px;margin:0 0 8px;background:#20323b;color:#ecf6f6;border:1px solid #425960;border-radius:6px';
const modificationMatches=document.createElement('p');modificationMatches.className='tip';modificationMatches.setAttribute('role','status');
const segmentFilters=document.createElement('div');segmentFilters.className='row';
const segmentSide=document.createElement('select');segmentSide.setAttribute('aria-label','Cerebral side');segmentSide.append(new Option('Both sides',''),new Option('Left','left'),new Option('Right','right'));
const segmentChoice=document.createElement('select');segmentChoice.setAttribute('aria-label','Cerebral segment');segmentChoice.append(new Option('All vessel segments',''));
for(const family of ['M','A','P'])for(const number of [1,2,3]){const id=family+number;segmentChoice.append(new Option(id+(['M1','M2','P1'].includes(id)?' · source named':' · boundary needed'),id))}
segmentFilters.append(segmentSide,segmentChoice);segmentFilters.style.marginBottom='8px';
const segmentNotice=document.createElement('p');segmentNotice.className='tip';segmentNotice.setAttribute('role','status');
$('atlasModificationName').before(modificationLabel,segmentFilters,segmentNotice,modificationSearch,modificationSelect,modificationMatches);
segmentSide.onchange=segmentChoice.onchange=()=>{modificationSearch.value='';syncAtlasModification()};
modificationSearch.oninput=()=>syncAtlasModification();
modificationSelect.onchange=()=>{if(modificationSelect.value)post('/api/atlas-selection',{part_id:modificationSelect.value})};
let modificationOptionsKey='';
function sourceSegment(vessel){
 const name=(vessel.name||'').toLowerCase();
 if(name.includes('sphenoid part of')&&name.includes('middle cerebral'))return 'M1';
 if(name.includes('insular part of')&&name.includes('middle cerebral'))return 'M2';
 if(name.includes('precommunicating part of')&&name.includes('posterior cerebral'))return 'P1';
 return '';
}
function segmentCandidate(vessel,segment){
 const name=(vessel.name||'').toLowerCase();
 if(['M1','M2','P1'].includes(segment))return sourceSegment(vessel)===segment;
 if(segment==='M3')return name.includes('middle cerebral')&&!sourceSegment(vessel);
 if(segment.startsWith('A'))return name.includes('anterior cerebral artery')||name.includes('pericallosal artery');
 if(segment.startsWith('P'))return name.includes('postcommunicating part of')&&name.includes('posterior cerebral');
 return true;
}
function matchesVesselSearch(vessel,query){
 const normalize=text=>String(text).toLowerCase().replace(/[^a-z0-9]+/g,' ').trim();
 const name=normalize(vessel.name||''),aliases=[];
 for(const [phrase,alias]of [['anterior communicating','acom acomm'],['posterior communicating','pcom pcomm'],['internal carotid','ica'],['external carotid','eca'],['common carotid','cca'],['middle cerebral','mca'],['anterior cerebral','aca'],['posterior cerebral','pca']])if(name.includes(phrase))aliases.push(alias);
 const tokens=normalize(query).split(' ').filter(Boolean),haystack=normalize(`${name} ${vessel.id} ${aliases.join(' ')} ${sourceSegment(vessel)}`);
 const unpairedAcom=name.includes('anterior communicating')&&!/\b(left|right)\b/.test(name)&&(tokens.some(t=>['acom','acomm'].includes(t))||tokens.includes('communicating'));
 return tokens.every(token=>unpairedAcom&&['left','right'].includes(token)||haystack.includes(token));
}
const optionsCard=atlasCard(''),displayDetails=document.createElement('details'),displayTitle=document.createElement('summary');displayTitle.textContent='Display options';displayDetails.append(displayTitle);optionsCard.append(displayDetails);displayDetails.append($('show_arterial').closest('.row'),$('atlasCenterlinesVisible').closest('label'),$('atlasContextLabel'),$('neckRepairsPanel'));
const viewDetails=$('applyView').closest('details');viewDetails.querySelector('summary').textContent='Camera focus';displayDetails.append(viewDetails);$('mode').previousElementSibling.hidden=true;$('mode').hidden=true;
const advancedCard=atlasCard(''),advanced=document.createElement('details'),advancedTitle=document.createElement('summary');advancedTitle.textContent='Source & reconstruction details';advanced.append(advancedTitle,$('atlasInspector'));advancedCard.append(advanced);const repairsDetails=$('neckRepairsPanel').querySelector('details');advanced.append(repairsDetails);for(const p of [...$('neckRepairsPanel').querySelectorAll(':scope > p')])advanced.append(p);advanced.append($('referenceReadOnly'));atlasWorkspace.append($('error'));
const layerIds=['arterial','systemic_venous','hepatic_portal'];
const vesselDisplay=document.createElement('div');vesselDisplay.className='atlasCard';vesselDisplay.innerHTML='<h2>Vessel display</h2><div class="row" role="group" aria-label="Vessel display"><button data-mode="arteries">Arteries</button><button data-mode="veins">Veins</button><button data-mode="both">Both</button></div>';
atlasWorkspace.prepend(vesselDisplay);
const candidateCard=atlasCard('합성 후보 검토');candidateCard.id='candidateCard';
candidateCard.innerHTML='<p>원본 Atlas와 분리된 합성 후보와 검사 상태를 확인합니다.</p><div class="row"><button id="showCandidate">합성 후보 보기</button><button id="candidateReturn" hidden>Atlas로 돌아가기</button></div><p id="candidateScope" role="status"></p><p id="candidateChecks"></p><details id="candidateDetails" hidden><summary>후보 버전과 표시 범위</summary><p id="candidateRevision"></p><p id="candidateEdges"></p></details>';
atlasWorkspace.prepend(candidateCard);
const candidateSelect=document.createElement('select');candidateSelect.id='candidateSelect';candidateSelect.setAttribute('aria-label','합성 후보 선택');candidateSelect.append(new Option('우측 외장골·고환동맥','right-iliac-source-profile'),new Option('우측 MCA 동맥류 · 검토 필요','right-mca-saccular'),new Option('우측 MCA 접합부 개선 · 검토 필요','right-mca-junction-review'),new Option('우측 MCA 표면 보정 · 검토 필요','right-mca-retained-fairing'));$('showCandidate').before(candidateSelect);
candidateSelect.style.cssText='width:100%;margin-bottom:10px';$('showCandidate').parentElement.before(candidateSelect);
const candidateView=document.createElement('button');candidateView.id='candidateView';candidateView.textContent='중심선 보기';$('candidateReturn').after(candidateView);
candidateSelect.append(new Option('뇌혈관 8개 · 원본 비교','cerebral-protected-reference'),new Option('뇌혈관 8개 · 끝단 보존 보정 후보','cerebral-protected-fit'));
candidateSelect.append(new Option('좌측 경동맥 · 내강 결합 후보','left-carotid-solid-union'),new Option('우측 경동맥 · 내강 결합 후보','right-carotid-solid-union'));
candidateSelect.append(new Option('대퇴–전방순환 통합 · 검토 후보','femoral-anterior-solid-union'));
candidateSelect.append(new Option('대퇴–전방순환 · 목 메시 개선 후보','resampled-access-protected'));
candidateSelect.append(new Option('대퇴 굴곡 0.25 mm · 검사 후보','access-femoral-bend-inspection'));
const candidateSource=document.createElement('select');candidateSource.id='candidateSource';candidateSource.setAttribute('aria-label','결합 모델의 원본 혈관 선택');candidateSource.hidden=true;
const candidateSelectionInfo=document.createElement('p');candidateSelectionInfo.id='candidateSelectionInfo';
candidateCard.append(candidateSource,candidateSelectionInfo);
const candidateRoutes=document.createElement('details');candidateRoutes.id='candidateRoutes';candidateRoutes.hidden=true;
const candidateRoutesTitle=document.createElement('summary');candidateRoutesTitle.textContent='대퇴–경동맥 접근 경로 검사';
const candidateRoutesTable=document.createElement('div');candidateRoutesTable.style.cssText='display:grid;grid-template-columns:1fr 1fr 1.5fr 1fr;gap:6px;margin-top:10px;font-size:12px';
candidateRoutes.append(candidateRoutesTitle,candidateRoutesTable);candidateCard.append(candidateRoutes);
candidateSource.onchange=()=>post('/api/candidate-selection',{source_name:candidateSource.value||null});
const candidateRadius=document.createElement('div');candidateRadius.id='candidateRadius';candidateRadius.hidden=true;
candidateRadius.innerHTML='<h3>선택 혈관 반경</h3><label>반경 배율 <input id="candidateRadiusScale" type="number" value="0.9" min="0.01" step="0.05"></label><label>접합 전이 거리 (mm) <input id="candidateRadiusTransition" type="number" value="5" min="0.01" step="1"></label><label>최대 이동 허용값 (mm) <input id="candidateRadiusBound" type="number" value="0.5" min="0.01" step="0.1"></label><div class="row"><button id="candidateRadiusPreview">반경 미리보기</button><button id="candidateRadiusApply">후보 적용</button><button id="candidateRadiusDiscard">미리보기 취소</button><button id="candidateRadiusUndo">적용 되돌리기</button></div><p id="candidateRadiusStatus" role="status"></p><p>원본을 보존하는 실험적 합성 편집입니다. 접합 경계는 고정합니다. 주변 혈관 충돌과 중심선 포함은 편집 후 재검사가 필요하며, 변경은 이 세션에만 보관됩니다.</p>';
candidateCard.append(candidateRadius);
const candidateExport=document.createElement('div');candidateExport.id='candidateExport';candidateExport.hidden=true;
candidateExport.innerHTML='<button id="candidateCaseSave">현재 형상·그래프 저장 (검사용)</button><p>검사 실패·미확인 상태도 함께 저장합니다. 승인된 생성 데이터가 아닙니다.</p>';
candidateCard.append(candidateExport);
$('candidateCaseSave').onclick=async()=>{
 try{
  const r=await fetch('/api/candidate-case-snapshot',{headers:{'X-Expected-Generation':String(state.generation)}});
  if(!r.ok)throw Error((await r.json()).error);
  const text=await r.text(),url=URL.createObjectURL(new Blob([text],{type:'application/json'}));
  const a=document.createElement('a');a.href=url;a.download='access-inspection.case.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
 }catch(e){$('error').textContent=e.message}
};
candidateRadius.querySelector('p:not([id])').textContent='원본을 보존하는 실험적 합성 편집입니다. 접합 경계는 고정합니다. 주변 충돌과 중심선 포함은 재검사가 필요합니다. 편집 파일에는 원본 식별 정보와 편집 순서를 기록하며, 불러올 때 같은 원본에서 재계산합니다.';
candidateRadius.insertAdjacentHTML('beforeend','<div class="row"><button id="candidateRadiusSave">편집 파일 저장</button><button id="candidateRadiusLoad">편집 파일 불러오기</button></div><input id="candidateRadiusFile" type="file" accept=".json,application/json" hidden>');
for(const row of candidateRadius.querySelectorAll('.row'))row.style.cssText='display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:10px';
for(const input of candidateRadius.querySelectorAll('input[type=number]'))input.style.cssText='width:100%;background:#20323b;color:#ecf6f6;border:1px solid #425960;border-radius:6px;padding:8px;margin:4px 0 10px';
let radiusPending=false;
$('candidateRadiusSave').onclick=async()=>{
 try{
  const r=await fetch('/api/candidate-radius-session');if(!r.ok)throw Error((await r.json()).error);
  const text=await r.text(),url=URL.createObjectURL(new Blob([text],{type:'application/json'}));
  const a=document.createElement('a');a.href=url;a.download=state.candidate.id+'-radius.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
 }catch(e){$('error').textContent=e.message}
};
$('candidateRadiusLoad').onclick=()=>$('candidateRadiusFile').click();
$('candidateRadiusFile').onchange=async()=>{
 const file=$('candidateRadiusFile').files[0];if(!file)return;
 try{
  if(file.size>1024*1024)throw Error('편집 파일은 1 MiB 이하여야 합니다.');
  await radiusRequest('/api/candidate-radius-restore',{session_text:await file.text()});
 }catch(e){$('error').textContent=e.message}
 finally{$('candidateRadiusFile').value=''}
};
async function radiusRequest(path,data){
 radiusPending=true;$('error').textContent='';updateCandidateControls();
 try{
  const r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json','X-Expected-Generation':String(state.generation)},body:JSON.stringify(data)});
  const body=await r.json();if(!r.ok)throw Error(body.error||'반경 편집 실패');
 }catch(e){$('error').textContent=e.message}
 finally{radiusPending=false;await poll();updateCandidateControls()}
}
$('candidateRadiusPreview').onclick=()=>radiusRequest('/api/candidate-radius-preview',{
 source_name:candidateSource.value,scale:Number($('candidateRadiusScale').value),
 transition_mm:Number($('candidateRadiusTransition').value),max_displacement_mm:Number($('candidateRadiusBound').value)});
for(const [id,action] of [['candidateRadiusApply','apply'],['candidateRadiusDiscard','discard'],['candidateRadiusUndo','undo']])
 $(id).onclick=()=>radiusRequest('/api/candidate-radius-action',{action,token:action==='undo'?null:state.candidate_radius?.preview_token});
const protectedCompare=document.createElement('button');protectedCompare.id='protectedCompare';protectedCompare.hidden=true;
candidateView.after(protectedCompare);
protectedCompare.onclick=()=>post('/api/source',{source:'candidate',candidate_id:state.candidate.protected_comparison.reference?'cerebral-protected-fit':'cerebral-protected-reference'});
candidateView.onclick=()=>post('/api/view',{access:state.access,target:state.target,mode:state.mode==='Surface'?'Centerlines':'Surface',focus:'Whole network'});
let displayedCandidateId=null;
$('showCandidate').onclick=()=>post('/api/source',{source:'candidate',candidate_id:candidateSelect.value});
$('candidateReturn').onclick=()=>post('/api/source',{source:'atlas'});
function updateCandidateControls(){
 const active=state?.source==='candidate',candidate=state?.candidate;
 if(active&&candidate?.id!==displayedCandidateId){candidateSelect.value=candidate.id;displayedCandidateId=candidate.id;}
 candidateView.hidden=!active||candidate?.centerlines_available===false;candidateView.disabled=pending;candidateView.textContent=state?.mode==='Surface'?'중심선 보기':'표면 보기';
 protectedCompare.hidden=!active||!candidate?.protected_comparison;protectedCompare.disabled=pending;
 protectedCompare.textContent=candidate?.protected_comparison?.reference?'보정 후보와 비교':'같은 혈관의 원본 보기';
 $('showCandidate').disabled=pending;candidateSelect.disabled=pending;$('candidateReturn').hidden=!active;$('candidateReturn').disabled=pending;
 $('candidateDetails').hidden=!active;
 $('candidateScope').textContent=active?(candidate?.radius_path_sources?.length?'반경 미리보기 가능 · ':'읽기 전용 · ')+(candidate?.scope||'원본 Atlas와 분리된 합성 후보'):'Atlas의 선택과 수정 내용을 유지한 채 전환합니다.';
 $('candidateChecks').textContent=active?`두 표면 간 분리: ${candidate?.pair_surface_separation||'UNKNOWN'} · 간격 하한 ${Number.isFinite(candidate?.pair_surface_gap_lower_bound_mm)?candidate.pair_surface_gap_lower_bound_mm.toFixed(3)+' mm':'미확인'}. 전체 Atlas 충돌·자기 교차: 미검사. 해부학적 수용: 미확인.`:'';
 if(active&&candidate?.context_inspection){const audit=candidate.context_inspection;$('candidateChecks').textContent=`주변 프로파일 검사: ${audit.status} · 분리 ${audit.separated_count}/${audit.context_edge_count}. 검토 대상: ${audit.review_edges.map(r=>r.edge_id+' ('+r.status+')').join(', ')}. 원본 표면 충돌·임상 검증: 미실행.`;}
 if(active&&candidate?.junction_inspection){const j=candidate.junction_inspection;$('candidateChecks').textContent+=` 큰 접힘 검사: ${j.crease_screen}. 후보 자기교차: ${j.self_contact}. 매끄러움 수렴: ${j.smoothness}. ${j.note}`;}
 if(active&&candidate?.protected_comparison){const p=candidate.protected_comparison;$('candidateChecks').textContent=`${p.reference?'원본':'보정 후보'} ${p.parts}개 표면 · 후보 자기 접촉 검출 0 · 동시 대체 ${p.affected_pairs}조합 검사에서 접촉 삼각형 쌍 추가·소실 0. 중심선·반경 일치, 체적 포함 및 해부학적 수용은 미확인입니다.`;}
 $('candidateRevision').textContent=candidate?.revision||'';$('candidateRevision').style.overflowWrap='anywhere';$('candidateEdges').textContent=(candidate?.edge_ids||[]).join(' · ');
 if(active&&candidate?.carotid_union){const c=candidate.carotid_union;$('candidateChecks').textContent=`단일 내강 · 자기 접촉 검출 0 · 중심선 ${c.path_segments}개 구간 포함 · ${c.lineage_faces}개 면 출처 확인 · 새 접촉 혈관 0. 접합 매끄러움과 해부학적 연결은 미확인입니다.`;}
 if(active&&candidate?.access_union){const a=candidate.access_union;$('candidateChecks').textContent=`${a.source_count}개 원본 부분 · 단일 폐곡면 · 자기 접촉 검출 0 · ${a.lineage_faces}개 면 출처 확인. 중심선 검사: ${a.centerline_status} (${a.checked_paths}개 경로 기록). 주변 검사: ${a.context_status} (${a.context_completed ?? a.context_neighbors}/${a.context_neighbors}개, 접촉 ${a.contacts.length}개, 미확정 ${a.unknown.length}개). 네 접근 경로 그래프·해부 구간·접합 매끄러움은 미확인입니다. 검사 상태는 후보를 불러온 시점 기준입니다.`;}
 candidateRoutes.hidden=!active||!candidate?.access_graph;candidateRoutesTable.replaceChildren();
 if(active&&candidate?.access_graph){const g=candidate.access_graph;$('candidateChecks').textContent+=` 합성 그래프 ${g.nodes}개 접점 · ${g.edges}개 구간. 경로 검사: ${g.status}. 진한 빨강: 원본 경로 · 연한 빨강: 추정 목 연결·합성 접합.`;
  for(const value of ['대퇴','경동맥','도달점','판정',...g.routes.flatMap(r=>[r.femoral_side==='L'?'좌측':'우측',r.carotid_side==='L'?'좌측':'우측',r.target.startsWith('FJ1654')?'ACA 원본':'MCA 근위부',r.status])]){const cell=document.createElement('span');cell.textContent=value;candidateRoutesTable.append(cell);}
 }
 candidateSource.hidden=!active||!candidate?.selectable_sources;
 candidateSource.disabled=pending||(active&&candidate?.access_graph&&state.mode!=='Surface');
 if(!candidateSource.hidden){
  candidateSource.replaceChildren(new Option('전체 결합 표면',''),...candidate.selectable_sources.map(s=>new Option(s.label,s.id)));
  candidateSource.value=candidate.selected_source||'';
 }
 const selection=active?candidate?.source_selection:null;
 candidateSelectionInfo.textContent=selection?`선택된 부분 표면 ${selection.faces}개 면 · 접합 공유 정점 ${selection.shared_vertices}개. 부분 보기이며 형상은 변경하지 않습니다.`:'';
 if(active&&candidate?.access_graph&&state.mode!=='Surface')candidateSelectionInfo.textContent='전체 중심선 그래프를 표시합니다. 원본 부분 선택은 표면 보기에서 사용할 수 있습니다.';
 const radiusBusy=radiusPending||state?.candidate_radius_busy;
 const radiusState=state?.candidate_radius,preview=radiusState?.preview_token;
 const radiusParameters=radiusBusy?state?.candidate_radius_request:preview?candidate?.radius_edit:null;
 for(const [id,key] of [['candidateRadiusScale','scale'],['candidateRadiusTransition','transition_mm'],['candidateRadiusBound','max_displacement_mm']]){
  $(id).disabled=!!(radiusBusy||preview);
  const value=radiusParameters?.[key]??(key==='max_displacement_mm'?radiusParameters?.displacement_bound_mm:undefined);
  if(Number.isFinite(value))$(id).value=String(value);
 }
 candidateRadius.hidden=!active||!candidate?.radius_path_sources?.length;
 if(active&&candidate?.shape_edit){const a=candidate.access_union,e=candidate.shape_edit;
  $('candidateChecks').textContent=`굴곡 변위 ${e.bend_mm} mm · 회전 ${e.twist_deg}° · 공유 경계와 다른 혈관 고정. 중심선 ${a.checked_paths}개 경로 ${a.centerline_status}. 주변 검사 ${a.context_status} (${a.context_completed}/${a.context_neighbors}개, 접촉 ${a.contacts.length}개, 미확정 ${a.unknown.length}개). 읽기 전용 검사 후보이며 반경 보존·접합 매끄러움·해부학적 수용은 미확인입니다. 상태는 후보를 불러온 시점 기준입니다.`;
 }
 candidateExport.hidden=!active||!candidate?.access_graph;
 $('candidateCaseSave').disabled=pending||radiusBusy||!candidate?.access_graph;
 $('candidateRadiusPreview').disabled=pending||radiusBusy||!!preview||!candidate?.radius_path_sources?.includes(candidate?.selected_source);
 $('candidateRadiusApply').disabled=pending||radiusBusy||!preview||candidate?.radius_edit?.neighbor_contact!=='PASS'||(!!candidate?.access_union&&candidate?.radius_edit?.centerline_containment?.status!=='PASS');
 $('candidateRadiusDiscard').disabled=pending||radiusBusy||!preview;
 $('candidateRadiusUndo').disabled=pending||radiusBusy||!!preview||!radiusState?.undo_available;
 $('candidateRadiusSave').disabled=pending||radiusBusy||!!preview||!radiusState;
 $('candidateRadiusLoad').disabled=pending||radiusBusy||!!preview||!!radiusState?.undo_available;
 $('candidateRadiusStatus').textContent=radiusBusy?'반경 후보 계산 중 · 현재 모델 유지':preview?'미리보기 표시 중 · 아직 적용하지 않음':radiusState?.undo_available?'반경 변경 적용됨 · 세션 내 복원 가능':'혈관 부분을 선택한 뒤 반경 후보를 계산하세요.';
 if(radiusBusy&&state.candidate_radius_progress?.total){const p=state.candidate_radius_progress;const labels={geometry:'형상 계산과 자기 접촉 검사',centerlines:'중심선 검사',context:'주변 혈관 검사'};$('candidateRadiusStatus').textContent=`${labels[p.phase]||'계산'} · ${p.completed}/${p.total} · 현재 모델 유지`;}
 if(!radiusBusy&&!preview&&candidate?.radius_path_unavailable?.[candidate?.selected_source])$('candidateRadiusStatus').textContent='이 혈관은 편집 중심선을 하나로 확정할 수 없습니다. 분지 경로 지정이 필요합니다.';
 if(active&&(radiusBusy||preview||radiusState?.undo_available)){
  $('showCandidate').disabled=true;candidateSelect.disabled=true;$('candidateReturn').disabled=true;
 }
 if(radiusBusy||preview)candidateSource.disabled=true;
 if(active&&candidate?.radius_edit){
  $('candidateScope').textContent='반경 변형 합성 후보 · 원본 Atlas 보존';
  const context=candidate.radius_edit.neighbor_context;
  $('candidateChecks').textContent=`반경 배율 ${candidate.radius_edit.scale} · 자기 접촉 검사 ${candidate.radius_edit.self_contact.status}. 주변 혈관 검사: ${candidate.radius_edit.neighbor_contact}. 중심선 검사: ${candidate.radius_edit.centerline_containment?.status||"NOT RUN"}. 접합 매끄러움·해부학적 연결은 미확인입니다.`;
  if(context)$('candidateChecks').textContent+=` ${context.neighbors}개 주변 혈관 · 새 접촉/확대: ${context.new_or_extended_contacts.join(', ')||'없음'} · 미확정: ${context.unknown.join(', ')||'없음'} · 남아 있는 접촉: ${context.remaining_contacts.join(', ')||'없음'}.`;
  if(context?.unknown?.length)$('candidateChecks').textContent+=' 미확정 사유: '+Object.entries(context.unknown_reasons||{}).map(([id,reasons])=>id+' — '+reasons.join('; ')).join(' · ');
  if(preview&&candidate.radius_edit.neighbor_contact!=='PASS')$('candidateRadiusStatus').textContent='미리보기 표시 중 · 주변 혈관 검사 미통과로 적용할 수 없습니다.';
 }
 vesselDisplay.hidden=active;annotationCard.hidden=active;caseCard.hidden=active;
 if(active){availability.hidden=true;$('stage').querySelector('iframe').hidden=false;
 const original=candidate?.protected_comparison?.reference===true;
 $('scopeSubtitle').textContent=(candidate?.title||'선택된 후보')+(original?' · 원본 표면':' · 합성 후보');
 $('sourceBadge').textContent=original?'읽기 전용 원본':'읽기 전용 후보';$('graph').style.display='none';}
}
for(const button of vesselDisplay.querySelectorAll('button'))button.onclick=()=>post('/api/visibility',{arterial:button.dataset.mode!=='veins',systemic_venous:button.dataset.mode!=='arteries',hepatic_portal:button.dataset.mode!=='arteries'});
const isReference=()=>state?.source==='reference';
const isAtlas=()=>state?.source==='atlas';
const isReadOnly=()=>isReference()||isAtlas()||state?.source==='candidate';
let atlasCenterlineData=null,atlasCenterlineFetching=false,atlasCenterlineLastSelection=null,atlasCenterlineGeneration=-1;
let atlasModificationKey='',atlasModificationGeneration=-1,atlasModificationPart=null;
const currentGraph=()=>state?.layers?.[$('layer').value]||{nodes:state?.nodes||{},edges:state?.edges||[]};
const currentParams=()=> $('layer').value==='arterial'?state.parameters:state.parameters.venous;
const pretty=s=>s.replace(/_/g,' ').replace(/\b(aca|mca|pca|acom|pcom|sma|ima|a[123]|m[123]|p[123])\b/gi,x=>x.toUpperCase()).replace(/\b\w/g,x=>x.toUpperCase());
for(const s of ['left','right'])for(const a of ['mca','aca','pca'])$('target').add(new Option(pretty(s+'_'+a),s+'_'+a));
function values(){ $('radiusOut').textContent=(+$('radius').value).toFixed(2);$('tortOut').textContent=(+$('tort').value).toFixed(2);$('archOut').textContent=(+$('arch').value).toFixed(2)}
['radius','tort','arch'].forEach(id=>$(id).oninput=()=>{values();if(id==='arch')$('archType').value='custom'});
$('archType').onchange=()=>{if($('archType').value!=='custom')$('arch').value=$('archType').value;values()};
function select(id){selected=id;$('vessel').value=id;$('selectedName').textContent=pretty(id);if(!isReadOnly()){const base=currentParams();const p=base.vessel_parameters[id]||base;$('radius').value=p.radius_scale;$('tort').value=p.tortuosity;values()}draw()}
function group(e){const s=e.id;if($('layer').value!=='arterial'){if(/sinus|cerebral|galen|rosenthal|sagittal|transverse|sigmoid|straight|jugular/.test(s))return 'Cerebral';if(/femoral|iliac/.test(s))return 'Femoral';if(/hepatic|splenic|gastric|mesenteric|renal|portal|inferior_vena|ivc|gonadal|adrenal/.test(s))return 'Abdominal';const nodes=currentGraph().nodes;return ((nodes[e.start]?.[2]||0)+(nodes[e.end]?.[2]||0))/2>800?'Cerebral':'Thoracic'}if(/aca|mca|pca|acom|pcom|basilar/.test(s))return 'Cerebral';if(/celiac|splenic|hepatic|gastric|mesenteric|renal|abdominal/.test(s))return 'Abdominal';if(/femoral|iliac/.test(s))return 'Femoral';return 'Aortic arch'}
function refreshLayer(resetRegion=false){
 const arterial=$('layer').value==='arterial';$('variation').hidden=!arterial||isReadOnly();$('venousVariation').hidden=arterial||isReadOnly();
 if(isAtlas()){draw();return}
 if(resetRegion){const regions=isReference()?['All regions']:arterial?['All regions','Cerebral','Aortic arch','Abdominal','Femoral']:['All regions','Cerebral','Thoracic','Abdominal','Femoral'];$('region').replaceChildren(...regions.map(r=>new Option(r,r)));$('region').value=isReference()?'All regions':arterial?'Cerebral':$('layer').value==='hepatic_portal'?'Abdominal':'All regions'}
 const graph=currentGraph();$('vessel').replaceChildren(...graph.edges.map(e=>new Option(pretty(e.id),e.id)));
 if(!graph.edges.some(e=>e.id===selected))selected=(graph.edges.find(e=>$('region').value==='All regions'||group(e)===$('region').value)||graph.edges[0])?.id||'';
 if(selected)select(selected);else{$('selectedName').textContent='No vessels in this layer';draw()}
}
$('layer').onchange=()=>{selected='';refreshLayer(true)};
function sourceControls(){
 const reference=isReference(),atlas=isAtlas(),info=state.reference||{},atlasInfo=state.atlas||{};
 availability.hidden=atlas&&atlasInfo.available;availability.textContent=atlasInfo.available?'Atlas workspace is not active. Reload to load the Atlas.':'Atlas unavailable: '+(atlasInfo.error||'Local source data has not been loaded.');for(const card of [browseCard,relationCard,modificationCard,optionsCard,advancedCard])card.hidden=!atlas||!atlasInfo.available;
 $('stage').querySelector('iframe').hidden=!atlas||!atlasInfo.available;
 $('scopeSubtitle').textContent='Atlas vessel workspace';$('sourceBadge').textContent='ATLAS';
 $('atlasModificationPanel').hidden=!atlas;
 $('openEditor').setAttribute('aria-pressed',String(!isReadOnly()));$('openEditor').classList.toggle('primary',!isReadOnly());
 $('openAtlas').setAttribute('aria-pressed',String(atlas));$('openAtlas').classList.toggle('primary',atlas);$('openAtlas').disabled=pending||!atlasInfo.available;
 $('workspaceNote').textContent=atlas?'Select an atlas vessel to adjust its radius, tortuosity and torsion. Changes are local derived geometry; original atlas parts remain recoverable.':reference?'Reference view. Open Graph & vessel modification to edit the authored model. Your previous edits are preserved separately.':'Edit the branch graph, vessel shape and anatomical variations below. Atlas reference remains available for comparison.';
 $('atlasOption').disabled=!atlasInfo.available;$('atlasOption').title=atlasInfo.available?'Original shared-coordinate atlas parts':atlasInfo.error||'Atlas data is not available';$('atlasInspector').hidden=!atlas;$('referenceInspector').hidden=atlas;
 $('layer').hidden=atlas;$('layerLabel').hidden=atlas;
 $('atlasBrowse').hidden=!atlas;
 $('atlasContextLabel').hidden=!atlas;$('atlasContext').checked=state.context_visible??true;$('atlasContext').disabled=pending;
 const repairs=state.neck_repairs||{};$('neckRepairsPanel').hidden=!atlas||!repairs.available;
 $('neckRepairs').checked=state.neck_repairs_visible??true;$('neckRepairs').disabled=pending||!repairs.available;
 $('neckRepairsMethod').textContent=repairs.method||'Estimated missing-vessel reconstruction';
 const separation=(repairs.parts||[]).find(p=>p.separation)?.separation;
 if(separation){const margin=separation.after?.minimum_clearance_mm;$('neckRepairsMethod').textContent+=` · Estimated vessel spacing: ${Number.isFinite(margin)?margin.toFixed(2):'unknown'} source units minimum (capsule proxy; original atlas surfaces are not certified clear).`}
 $('neckRepairsLimits').textContent=Array.isArray(repairs.limitations)?repairs.limitations.join(' '):String(repairs.limitations||'Estimated geometry; anatomical continuity is not validated.');
 const unresolved=Array.isArray(repairs.unresolved)?repairs.unresolved:[];
 const filled=unresolved.filter(entry=>String(entry.display_resolution||'').startsWith('FILLED_BY_ESTIMATED_NETWORK'));
 const unfilled=unresolved.length-filled.length;
 $('neckRepairsUnresolved').textContent=unresolved.length?`${unresolved.length} original-source gap report${unresolved.length===1?'':'s'}: ${filled.length} represented by an estimated network; ${unfilled} without an estimated display fill. Missing source anatomy remains missing. Whole-network continuity is not validated.`:'No source gaps reported by this repair step; whole-network anatomical continuity remains unvalidated.';
 $('repairGapDetails').replaceChildren();for(const entry of unresolved){const li=document.createElement('li');const estimated=String(entry.display_resolution||'').startsWith('FILLED_BY_ESTIMATED_NETWORK');li.textContent=`${pretty([entry.side,entry.kind].filter(Boolean).join(' '))}: ${estimated?'source absent; estimated display fill available':'no estimated display fill reported'}`;$('repairGapDetails').append(li)}
 $('repairSegments').replaceChildren();for(const part of repairs.parts||[]){for(const segment of part.graph?.segments||[]){const li=document.createElement('li');li.textContent=`${pretty(segment.id||segment.name||'Estimated segment')} · ESTIMATED`;$('repairSegments').append(li)}}
 for(const id of ['region','vessel','vesselLabel','selectedName'])$(id).hidden=atlas;
 $('graph').style.display=atlas?'none':'block';$('atlasParts').hidden=!atlas;
 $('scopeSubtitle').textContent=reference?'Standalone aortic reference':'Femoral → cerebral';
 $('sourceBadge').textContent=reference?(info.kind==='image-derived-reference'?'IMAGE-DERIVED REFERENCE':'REFERENCE GEOMETRY'):'SYNTHETIC ANATOMY';
 $('graphHeading').textContent=reference?'Source modeling paths':'Branch graph';
 $('graphDescription').textContent=reference?'Source modeling paths; junction connections are not verified. No artificial connecting vessels are added.':'Select a layer and vessel to edit its shape or connections.';
 $('source').value=state.source||'schematic';$('referenceOption').disabled=!info.available;
 $('referenceOption').textContent=info.available?'Standalone reference arch · read-only':'Standalone reference arch · unavailable';
 $('sourceReason').textContent=reference?'Reference arch only. Authored whole-body controls are preserved separately.':info.available?'Editable schematic. Switch source to inspect the separate reference arch.':info.error||'No reference geometry is available.';
 $('layer').disabled=reference||pending;if(reference)$('layer').value='arterial';
 $('shapeControls').hidden=isReadOnly();$('routeControls').hidden=isReadOnly();$('referenceReadOnly').hidden=!isReadOnly();$('resetAll').hidden=isReadOnly();
 $('referenceReadOnly').textContent=atlas?'Original atlas geometry is retained. Selected-vessel modifications update the derived display and centerline graph; restore removes the selected override. Estimated missing vessels retain their provenance.':'Standalone reference geometry is read-only. It is not joined to the authored whole-body network.';
 for(const id of ['radius','tort','applyVessel','resetVessel','access','target'])$(id).disabled=isReadOnly();
 for(const id of ['systemic_venous','hepatic_portal'])$('show_'+id).disabled=reference||pending;
 const allowedFocus=atlas?['Whole network','Aortic arch','Cerebral','Femoral bifurcation','Abdominal']:['Whole network','Aortic arch'];
 for(const option of $('focus').options){if(option.value==='Cerebral'){option.value='Cerebral';option.textContent=atlas?'Head & neck':'Cerebral'}option.disabled=isReadOnly()&&!allowedFocus.includes(option.value)}
 if(isReadOnly()&&!allowedFocus.includes($('focus').value))$('focus').value='Aortic arch';
 $('mode').disabled=atlas;if(atlas)$('mode').value='Surface';
 if(atlas){
  $('scopeSubtitle').textContent='Shared anatomical coordinates';$('sourceBadge').textContent='ATLAS REFERENCE';$('graphHeading').textContent='Atlas structures';
  $('graphDescription').textContent='Source atlas parts in their original shared coordinates. This is a structure list, not an inferred vessel-connectivity graph.';
  $('sourceReason').textContent=atlasInfo.available?'BodyParts3D source atlas with separately marked estimated missing vessels. Organ context and estimated additions can be hidden independently.':atlasInfo.error||'Atlas data is unavailable.';
  $('layerNote').textContent='Red arteries · blue veins. Heart context is a separate translucent structure. Visibility changes do not move atlas parts.';
  $('atlasFacts').replaceChildren();for(const[label,value]of [['Title',atlasInfo.title],['License',atlasInfo.license],['Coordinates',atlasInfo.coordinates],['Units',atlasInfo.units]]){if(value==null)continue;const dt=document.createElement('dt'),dd=document.createElement('dd');dt.textContent=label;dd.textContent=String(value);$('atlasFacts').append(dt,dd)}
  if(typeof atlasInfo.source_url==='string'&&/^https?:\/\//.test(atlasInfo.source_url)){const a=document.createElement('a');a.href=atlasInfo.source_url;a.target='_blank';a.rel='noopener noreferrer';a.textContent='Original atlas source';$('atlasFacts').append(a)}
  return;
 }
 $('layerNote').textContent='Red arteries · blue systemic veins · light blue portal veins. Portal and systemic veins remain separate across the unmodeled liver exchange.';
 const fingerprint=JSON.stringify(info);if(fingerprint===referenceRendered)return;referenceRendered=fingerprint;
 $('referenceDescription').textContent=info.available?(String(info.kind||'').toLowerCase().includes('synthetic')||String(info.title||'').includes('SynthAorta')?'Synthetic reference shape; not an individual patient or a validated normal population model.':'External reference geometry; anatomical and clinical validity are not implied.'):'Reference unavailable. '+(info.error||'');
 $('referenceFacts').replaceChildren();
 for(const[label,value]of [['Title',info.title],['Kind',info.kind],['Case status',info.case_status],['License',info.license],['Display units',info.units],['Source units (inferred)',info.source_units],['Unit evidence',info.unit_evidence],['Coordinates',info.coordinates],['Topology',info.topology],['SHA-256',info.sha256]]){if(value==null)continue;const dt=document.createElement('dt'),dd=document.createElement('dd');dt.textContent=label;dd.textContent=String(value);$('referenceFacts').append(dt,dd)}
 if(typeof info.source_url==='string'&&/^https?:\/\//.test(info.source_url)){const a=document.createElement('a');a.href=info.source_url;a.target='_blank';a.rel='noopener noreferrer';a.textContent='Original reference source';$('referenceFacts').append(a)}
 $('referenceMetrics').replaceChildren();
 const metrics=info.metrics||{},format=n=>Number.isFinite(n)?n.toFixed(2):'UNKNOWN';
 const heading=document.createElement('h2');heading.textContent='Source path measurements';$('referenceMetrics').append(heading);
 for(const[name,path]of Object.entries(metrics.paths||{})){
  const row=document.createElement('p'),title=document.createElement('strong');title.textContent=pretty(name);row.append(title,document.createElement('br'));
  row.append(document.createTextNode(`Length ${format(path.length_mm)} mm · contour radius ${format(path.radius_min_mm)}–${format(path.radius_max_mm)} mm`));
  const curvature=path.centerline?.curvature?.p95??path.centerline?.curvature_per_mm?.p95??path.centerline?.curvature_mm_inv?.p95;
  if(Number.isFinite(curvature)){row.append(document.createElement('br'),document.createTextNode(`Curvature P95 ${curvature.toPrecision(3)} mm⁻¹`))}
  $('referenceMetrics').append(row);
 }
 const radiusNote=document.createElement('p');radiusNote.textContent=info.radius_note||'Radius is derived from source contour area; it does not establish an exact lumen cross-section.';$('referenceMetrics').append(radiusNote);
 for(const[key,label]of [['arch_type','Arch type'],['branch_angles','Branch angles']]){const value=info[key]??metrics[key];if(value==null)continue;const row=document.createElement('p');row.textContent=label+': '+(typeof value==='object'?(value.status||'UNKNOWN')+(value.reason?' — '+value.reason:''):String(value));$('referenceMetrics').append(row)}
 const mesh=document.createElement('details'),summary=document.createElement('summary'),counts=document.createElement('p');summary.textContent='Mesh & sampling';counts.textContent=`${metrics.vertices??'UNKNOWN'} vertices · ${metrics.triangles??'UNKNOWN'} triangles · ${metrics.contour_count??'UNKNOWN'} source contours`;mesh.append(summary,counts);$('referenceMetrics').append(mesh);
}
function archMeasurement(){
 const m=state?.arch_measurement||{};
 if(Number.isFinite(m.measured_centerline_ratio))$('measured').textContent=`Current measured centerline surrogate: ${m.measured_centerline_ratio.toFixed(2)}.`;
 const label=v=>String(v??'Not available').replace(/_/g,' ');
 $('archClass').textContent=m.measured_type?`Measured surrogate: ${label(m.measured_type)} · requested preset: ${label(m.requested_type)}${m.matches_requested_type===false?' · MISMATCH: shape and requested preset differ':''}`:'';
 $('archClass').classList.toggle('mismatch',m.matches_requested_type===false);
}
function clearanceScreening(){
 $('clearancePanel').hidden=isReadOnly();if(isReadOnly())return;
 const c=state.clearance||{},key=JSON.stringify([state.generation,c]);if(key===clearanceRendered)return;clearanceRendered=key;
 const conflicts=Array.isArray(c.potential_collisions)?c.potential_collisions:[];
 $('clearanceStatus').textContent=c.status==='CLEAR'?`Generation ${state.generation} · Clearance: no potential inter-circuit conflicts detected.`:c.status==='OVERLAP'?`Generation ${state.generation} · Clearance: ${conflicts.length} potential inter-circuit conflict${conflicts.length===1?'':'s'} detected.`:`Generation ${state.generation} · Inter-circuit clearance: not evaluated.`;
 $('clearanceStatus').style.color=c.status==='OVERLAP'?'#ffb281':'#a8bdc3';
 $('clearanceMethod').textContent=c.method?String(c.method):'Centerline/radius screening';
 $('clearanceLimits').textContent=Array.isArray(c.limitations)?c.limitations.join(' '):String(c.limitations||'No detected potential conflicts does not establish clinical or anatomical validity.');
 $('clearanceConflicts').replaceChildren();for(const item of conflicts){const li=document.createElement('li');const clearance=Number.isFinite(item.clearance_mm)?item.clearance_mm.toFixed(2)+' mm':'unknown';li.textContent=`${pretty(item.vessel_a||'Unknown vessel')} (${pretty(item.layer_a||'unknown layer')}) ↔ ${pretty(item.vessel_b||'Unknown vessel')} (${pretty(item.layer_b||'unknown layer')}): ${clearance} signed clearance`;$('clearanceConflicts').append(li)}
}
$('source').onchange=()=>post('/api/source',{source:$('source').value});
$('openEditor').onclick=()=>{if(isReadOnly())post('/api/source',{source:'schematic'})};
$('openAtlas').onclick=()=>{if(!isAtlas())post('/api/source',{source:'atlas'})};
$('atlasContext').onchange=()=>post('/api/atlas-context',{visible:$('atlasContext').checked});
$('neckRepairs').onchange=()=>post('/api/neck-repairs',{visible:$('neckRepairs').checked});
$('atlasRegion').onchange=()=>{listDetails.open=true;draw()};$('atlasSearch').oninput=()=>{listDetails.open=true;draw()};
function syncAtlasSelection(){
 const all=[...(state?.atlas?.parts||[]),...(state?.neck_repairs?.parts||[])];const part=all.find(p=>p.id===state?.atlas_selection);
 if(part&&listDetails.dataset.selection!==part.id){listDetails.open=false;listDetails.dataset.selection=part.id}
 $('atlasSelection').textContent=part?`Selected: ${part.name||part.id} (${part.id})`:'No structure selected';
 for(const button of $('atlasParts').querySelectorAll('button[data-part-id]')){const selected=button.dataset.partId===state?.atlas_selection;button.setAttribute('aria-pressed',String(selected));button.style.borderColor=selected?'#ffd38a':'';button.disabled=pending}
 if(atlasCenterlineData&&atlasCenterlineLastSelection!==state?.atlas_selection)drawAtlasCenterlines();
 syncAtlasModification();
}
function atlasModificationValues(){
 $('atlasRadiusOut').textContent=(+$('atlasRadius').value).toFixed(2);$('atlasTortuosityOut').textContent=(+$('atlasTortuosity').value).toFixed(2);$('atlasTorsionOut').textContent=$('atlasTorsion').value+'°';
}
function syncAtlasModification(){
 $('atlasModificationPanel').hidden=!isAtlas();if(!isAtlas())return;
 const vessels=[...(state.atlas?.parts||[]),...(state.neck_repairs?.parts||[])].filter(p=>layerIds.includes(p.layer));
 const segment=segmentChoice.value||(modificationSearch.value.match(/\b[MAP][123]\b/i)?.[0]||'').toUpperCase(),side=segmentSide.value,needsBoundary=segment&&!['M1','M2','P1'].includes(segment);
 const query=needsBoundary?modificationSearch.value.replace(/\b[MAP][123]\b/ig,''):modificationSearch.value;
 const filtered=vessels.filter(p=>(!side||new RegExp('\\b'+side+'\\b','i').test(p.name||''))&&(!segment||segmentCandidate(p,segment))&&matchesVesselSearch(p,query));
 segmentNotice.textContent=needsBoundary?`${side?side+' ':''}${segment}: no verified segment boundary in this Atlas. Listed vessels are unsegmented candidates, NOT identified ${segment} segments. Editing changes the whole selected atlas part.`:segment?`${segment}: mapped from the source anatomical name. This is a name-based label, not independent anatomical validation.`:'M1/M2/P1 have source-name mappings. Other segments require anatomical boundary annotation.';
 const optionsKey=filtered.map(p=>p.id).join('|')+';'+modificationSearch.value+';'+segment;
 if(optionsKey!==modificationOptionsKey){
  modificationOptionsKey=optionsKey;modificationSelect.replaceChildren(new Option('Select a vessel…',''));
  for(const [layer,title]of [['arterial','Arteries'],['systemic_venous','Systemic veins'],['hepatic_portal','Portal veins']]){
   const group=document.createElement('optgroup');group.label=title;
   for(const vessel of filtered.filter(p=>p.layer===layer).sort((a,b)=>(a.name||a.id).localeCompare(b.name||b.id)))group.append(new Option(`${sourceSegment(vessel)?sourceSegment(vessel)+' · ':needsBoundary?'Unsegmented · ':''}${vessel.name||vessel.id} · ${vessel.id}`,vessel.id));
   if(group.children.length)modificationSelect.append(group);
  }
 }
 const id=state.atlas_selection,part=vessels.find(p=>p.id===id);
 modificationSelect.value=filtered.some(p=>p.id===id)?id:'';modificationSelect.disabled=pending||!filtered.length;
 modificationMatches.textContent=filtered.length?`${filtered.length} matching vessels`:'No matching vessels. Try a name, atlas ID, or abbreviation.';
 if(/\b(left|right)\b/i.test(modificationSearch.value)&&filtered.some(p=>/anterior communicating/i.test(p.name||'')&&!/\b(left|right)\b/i.test(p.name||'')))modificationMatches.textContent+=' · Atlas ACom is listed without left/right labels.';
 const ready=state.atlas_centerlines?.available&&atlasCenterlineGeneration===state.generation;
 const editable=ready&&(atlasCenterlineData?.edges||[]).some(edge=>edge.part_id===id);
 const key=JSON.stringify([id,state.generation]);
 if(key!==atlasModificationKey){atlasModificationKey=key;atlasModificationGeneration=state.generation;atlasModificationPart=id;const p=state.atlas_modifications?.[id]||{};$('atlasRadius').value=p.radius_scale??1;$('atlasTortuosity').value=p.tortuosity??0;$('atlasTorsion').value=p.torsion_deg??0;atlasModificationValues()}
 $('atlasModificationName').textContent=part?`${sourceSegment(part)?sourceSegment(part)+' · ':''}${part.name||id} · ${id}`:'Select an atlas vessel';
 $('atlasModificationControls').disabled=pending||!editable||!!state.atlas_edit_recovery_error;
 $('atlasModificationStatus').textContent=!part?'Select a vessel from the atlas list or graph.':!ready?'Waiting for the current centerline graph.':!editable?'This structure has no extracted centerline and cannot be modified.':state.atlas_modifications?.[id]?'Local modification applied to this vessel.':'Original geometry · adjustments are relative to this baseline.';
 const inspection=state.atlas_edit_checks?.[id];
 if(inspection)$('atlasModificationStatus').textContent+=` Basic edit checks: ${inspection.basic_invariants}. Source degenerate triangles: ${inspection.source_degenerate_triangles}; new: ${inspection.newly_degenerate_face_ids.length}. Maximum movement: ${inspection.maximum_vertex_displacement_mm.toFixed(3)} mm. Self-intersection: ${inspection.self_intersection}; surrounding collision: ${inspection.surrounding_collision}; junction smoothness: ${inspection.junction_smoothness}. Anatomical validity: ${inspection.anatomical_validity}.`;
 if(state.atlas_edit_recovery_error)$('atlasModificationStatus').textContent=state.atlas_edit_recovery_error;
}
for(const id of ['atlasRadius','atlasTortuosity','atlasTorsion'])$(id).oninput=atlasModificationValues;
$('applyAtlasModification').onclick=()=>post('/api/atlas-modification',{part_id:atlasModificationPart,radius_scale:+$('atlasRadius').value,tortuosity:+$('atlasTortuosity').value,torsion_deg:+$('atlasTorsion').value},atlasModificationGeneration);
$('resetAtlasModification').onclick=()=>post('/api/atlas-modification',{part_id:atlasModificationPart,radius_scale:1,tortuosity:0,torsion_deg:0},atlasModificationGeneration);
function endpointNeighborhood(data,partId){
 const edges=(data.edges||[]).filter(e=>e.part_id===partId),adj=new Map(),prepared=[];
 const dist=(a,b)=>Math.hypot(...a.map((v,i)=>v-b[i]));
 for(const e of edges){const arc=[0];for(let i=1;i<e.points.length;i++)arc.push(arc[i-1]+dist(e.points[i-1],e.points[i]));const length=arc.at(-1);prepared.push({e,arc,length});for(const [a,b]of [[e.start,e.end],[e.end,e.start]]){if(!adj.has(a))adj.set(a,[]);adj.get(a).push([b,length])}}
 const anchors=[...adj].filter(([,a])=>a.length===1||a.length>2).map(([id,a])=>({id,kind:a.length===1?'end':'junction',neighbors:new Map()}));
 // Distances along this vessel, not world-axis position or blood-flow direction.
 const shortest=start=>{const d=new Map([[start,0]]),todo=new Set(adj.keys());while(todo.size){let best=null;for(const n of todo)if(d.has(n)&&(best===null||d.get(n)<d.get(best)))best=n;if(best===null)break;todo.delete(best);for(const[n,w]of adj.get(best)){const v=d.get(best)+w;if(v<(d.get(n)??Infinity))d.set(n,v)}}return d};
 for(const a of anchors)a.distances=shortest(a.id);
 const nodes=new Map((data.nodes||[]).map(n=>[n.id,n]));let unassigned=0;
 for(const l of data.links||[]){if(![l.part_a,l.part_b].includes(partId))continue;const outgoing=l.part_a===partId,id=outgoing?l.part_b:l.part_a;let scores;
  if(outgoing){scores=anchors.map(a=>a.distances.get(l.start)??Infinity)}
  else{const p=l.target_point||nodes.get(l.end)?.point,entry=prepared.find(v=>v.e.id===l.target_edge);if(!p||!entry){unassigned++;continue}let nearest=0;for(let i=1;i<entry.e.points.length;i++)if(dist(entry.e.points[i],p)<dist(entry.e.points[nearest],p))nearest=i;const t=entry.arc[nearest];scores=anchors.map(a=>Math.min((a.distances.get(entry.e.start)??Infinity)+t,(a.distances.get(entry.e.end)??Infinity)+entry.length-t))}
  const nearest=Math.min(...scores);if(!Number.isFinite(nearest)){unassigned++;continue}const group=anchors[scores.indexOf(nearest)],previous=group.neighbors.get(id);if(!previous||l.distance<previous.distance)group.neighbors.set(id,l);
 }
 return {groups:anchors.map(({distances,...a})=>({...a,neighbors:[...a.neighbors].sort((a,b)=>(a[1].distance??Infinity)-(b[1].distance??Infinity))})),unassigned};
}
function drawEndpointConnections(data,selectedPart,parts){
 const root=$('atlasConnectionOverview'),result=endpointNeighborhood(data,selectedPart);root.replaceChildren();
 $('atlasCenterlineGraph').style.height='0px';$('atlasRelationEvidence').replaceChildren();
 $('atlasRelationSummary').textContent='Connections on both sides of the selected vessel. Grouped by distance along its centerline to an end or internal junction. End numbers are not blood-flow directions. All dashed connections remain candidates.';
 const selected=()=>{const el=document.createElement('div');el.className='notice';el.style.cssText='text-align:center;margin:12px 0;border-color:#ffd38a';el.textContent='SELECTED · '+(parts.get(selectedPart)?.name||selectedPart)+' · '+selectedPart;root.append(el)};
 const assessment=new Map((data.reference_topology?.candidate_assessments||[]).map(a=>[a.link_id,a]));
 if(!result.groups.length){selected();const p=document.createElement('p');p.textContent='No identifiable centerline ends: extraction may be missing or cyclic. This does not establish an anatomical terminal.';root.append(p);return}
 result.groups.forEach((group,index)=>{
  if(index===1)selected();
  const box=document.createElement('section'),title=document.createElement('p'),list=document.createElement('div');box.style.cssText='border:1px dashed #b8a16e;border-radius:8px;padding:9px;margin:8px 0';title.style.cssText='margin:0 0 8px;color:#b8dcd5;font-weight:600';title.textContent=(group.kind==='end'?'End region ':'Internal junction region ')+(index+1)+' · '+group.neighbors.length+' candidates';box.append(title,list);list.style.cssText='display:grid;grid-template-columns:1fr 1fr;gap:6px';
  if(!group.neighbors.length){const p=document.createElement('p');p.textContent='No connection identified here. Anatomical termination is NOT confirmed.';box.append(p)}
  for(const[id,link]of group.neighbors){const button=document.createElement('button'),name=document.createElement('span'),status=document.createElement('small');button.style.cssText='text-align:left;white-space:normal;line-height:1.4';name.textContent=parts.get(id)?.name||id;status.style.cssText='display:block;margin-top:5px';const a=assessment.get(link.id);status.textContent=id+' · '+(a?.status==='review_required'?'REVIEW REQUIRED':a?.status==='reference_junction_candidate'?'Reference counterpart; position unverified':'Spatial candidate');button.append(name,status);button.onclick=()=>post('/api/atlas-selection',{part_id:id});list.append(button)}
  root.append(box);
 });
 if(result.groups.length===1)selected();
 if(result.unassigned){const p=document.createElement('p');p.textContent=result.unassigned+' links could not be assigned to an end/junction. Inspect Spatial candidates.';root.append(p)}
}
function drawReferenceJunctions(data,selectedPart,parts){
 const svg=$('atlasCenterlineGraph'),evidence=$('atlasRelationEvidence');evidence.replaceChildren();
 const topology=data.reference_topology,junctions=(topology?.junctions||[]).filter(j=>j.members.some(m=>m.part_ids.includes(selectedPart)||(m.related_part_ids||[]).includes(selectedPart)));
 $('atlasRelationSummary').textContent=junctions.length?`${junctions.length} literature reference junctions. Source concepts or names matched; positions and variants remain unverified. Unresolved trunks are listed under Needs review, not drawn as vessels.`:'No curated anatomical relation for this vessel yet. Use Spatial candidates to inspect unverified neighbors.';
 const make=(tag,attrs,parent=svg)=>{const el=document.createElementNS('http://www.w3.org/2000/svg',tag);for(const[k,v]of Object.entries(attrs))el.setAttribute(k,v);parent.append(el);return el};
 let offset=0;
 for(const j of junctions){
  const rows=j.members.filter(m=>m.part_ids.length).map(m=>({id:m.part_ids.length===1?m.part_ids[0]:null,name:m.part_ids.length===1?(parts.get(m.part_ids[0])?.name||m.part_ids[0]):m.expected_names[0],role:m.role,status:m.mapping_status,count:m.part_ids.length}));
  for(const member of j.members){
   if(member.part_ids.length===1)continue;
   const details=document.createElement('details'),summary=document.createElement('summary'),note=document.createElement('p');
   summary.textContent=member.part_ids.length?`${member.expected_names[0]} · ${member.part_ids.length} elements (${member.mapping_status==='multiple_elements_same_concept'?'same concept':'ambiguous'})`:`Needs review · ${member.expected_names[0]}`;
   note.textContent=member.part_ids.length?'A concept may comprise several mesh elements. These are not separate confirmed branches.':member.unresolved_reason||'No corresponding atlas element identified. No vessel or junction has been generated.';
   if(member.mapping_basis)note.textContent+=` Source: ${member.mapping_basis.tree.toUpperCase()} / ${member.mapping_basis.concept_id}.`;
   details.append(summary,note);
   for(const id of [...member.part_ids,...(member.related_part_ids||[])]){const button=document.createElement('button');button.textContent=(parts.get(id)?.name||id)+' · '+id;button.style.cssText='text-align:left;margin:3px 0;font-size:12px';button.onclick=()=>post('/api/atlas-selection',{part_id:id});details.append(button)}
   evidence.append(details);
  }
  const title=make('text',{x:12,y:offset+20,fill:'#a7e5d8','font-size':12});title.textContent=j.label;
  const diamond=make('path',{d:`M 190 ${offset+34} l 12 12 l -12 12 l -12 -12 Z`,fill:'#71cdbb'});make('title',{},diamond).textContent=j.kind+' · reference only · position unannotated';
  for(const[rowIndex,row]of rows.entries()){
   const x=rowIndex%2?200:10,y=offset+106+Math.floor(rowIndex/2)*106;
   make('path',{d:`M 190 ${offset+58} L ${x+85} ${y-30}`,stroke:'#71cdbb','stroke-width':1,fill:'none'});
   const group=make('g',row.id?{role:'button',tabindex:0,'aria-label':'Focus vessel '+row.name,class:'relationshipNode',style:'cursor:pointer'}:{});
   make('rect',{x,y:y-30,width:170,height:86,rx:7,fill:row.id===selectedPart?'#29404c':'#1c303b',stroke:row.status==='missing'?'#ffb278':row.id===selectedPart?'#ffd38a':'#71cdbb'},group);
   make('title',{},group).textContent=row.name+' · '+row.role+' · '+row.status;
   const lines=[],words=row.name.split(' ');let line='';for(const word of words){if((line+' '+word).trim().length>22&&line){lines.push(line);line=word}else line+=(line?' ':'')+word}if(line)lines.push(line);
   lines.slice(0,2).forEach((text,i)=>{const label=make('text',{x:x+8,y:y-12+i*15,fill:'#eef7fa','font-size':11},group);label.textContent=i===1&&lines.length>2?text.slice(0,20)+'…':text});
   const role=make('text',{x:x+8,y:y+23,fill:'#a7e5d8','font-size':10},group);role.textContent=row.role.replaceAll('_',' ');
   const status=make('text',{x:x+8,y:y+42,fill:row.status==='ambiguous'?'#ffb278':'#a8bdc3','font-size':10},group);status.textContent=row.count>1?`${row.count} elements · ${row.status==='multiple_elements_same_concept'?'one concept':'ambiguous'}`:row.id;
   if(row.id){group.onclick=()=>post('/api/atlas-selection',{part_id:row.id});group.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();group.onclick()}}}
  }
  offset+=92+Math.ceil(rows.length/2)*106;
  const details=document.createElement('details'),summary=document.createElement('summary'),note=document.createElement('p'),source=document.createElement('a');summary.textContent=j.label+' · evidence';note.textContent=j.note||'Reference pattern only; atlas junction position requires annotation.';source.href=j.source_url;source.target='_blank';source.rel='noopener noreferrer';source.textContent='Anatomical source';details.append(summary,note,source);evidence.append(details);
 }
 const reviews=(topology?.candidate_assessments||[]).filter(a=>a.status==='review_required'&&[a.part_a,a.part_b].includes(selectedPart));
 if(reviews.length){const warning=document.createElement('p');warning.className='notice';warning.textContent=`${new Set(reviews.map(r=>[r.part_a,r.part_b].sort().join(':'))).size} spatial pair(s) require review: not standard direct branches. Inspect Spatial candidates.`;evidence.append(warning)}
 svg.setAttribute('viewBox',`0 0 380 ${Math.max(1,offset)}`);svg.style.height=offset+'px';svg.parentElement.style.overflow='auto';svg.parentElement.style.maxHeight='460px';
}
function drawAtlasCenterlines(){
 const data=atlasCenterlineData;if(!data)return;atlasCenterlineLastSelection=state?.atlas_selection;
 const svg=$('atlasCenterlineGraph');svg.replaceChildren();svg.setAttribute('aria-label','Atlas vessel relationship graph');
 const selectedPart=state?.atlas_selection,parts=new Map([...(state.atlas?.parts||[]),...(state.neck_repairs?.parts||[])].map(p=>[p.id,p]));
 if($('atlasConnectionOverview')){$('atlasConnectionOverview').replaceChildren();$('atlasConnectionOverview').hidden=$('atlasRelationMode').value!=='ends'}
 if(!selectedPart){svg.style.height='0px';$('atlasRelationSummary').textContent='Select a vessel above to view neighboring vessel candidates.';return}
 if($('atlasRelationMode').value==='ends'){drawEndpointConnections(data,selectedPart,parts);return}
 if($('atlasRelationMode').value==='reference'){drawReferenceJunctions(data,selectedPart,parts);return}
 $('atlasRelationEvidence').replaceChildren();
 const links=(data.links||[]).filter(l=>l.part_a===selectedPart||l.part_b===selectedPart),neighbors=new Map();
 for(const link of links){const id=link.part_a===selectedPart?link.part_b:link.part_a;if(id===selectedPart)continue;const previous=neighbors.get(id);if(!previous||link.distance<previous.distance)neighbors.set(id,link)}
 const shown=[...neighbors].sort((a,b)=>(a[1].distance??Infinity)-(b[1].distance??Infinity)||a[0].localeCompare(b[0]));
 const points=(data.edges||[]).filter(e=>e.part_id===selectedPart).flatMap(e=>e.points||[]),nodeBy=new Map((data.nodes||[]).map(n=>[n.id,n]));
 const bounds=[0,1,2].map(axis=>points.length?points.reduce((b,p)=>[Math.min(b[0],p[axis]),Math.max(b[1],p[axis])],[Infinity,-Infinity]):[0,0]);
 const axis=[0,1,2].sort((a,b)=>(bounds[b][1]-bounds[b][0])-(bounds[a][1]-bounds[a][0]))[0],mid=(bounds[axis][0]+bounds[axis][1])/2;
 const sides=[[],[]];for(const entry of shown){const link=entry[1],attachment=nodeBy.get(link.part_a===selectedPart?link.start:link.end)?.point; sides[attachment&&attachment[axis]<mid?0:1].push(entry)}
 const ownEdges=(data.edges||[]).filter(e=>e.part_id===selectedPart).length;
 $('atlasRelationSummary').textContent=`${neighbors.size} neighboring candidates · all shown. Spatial positions only, NOT parent/child branches. Dashed links are unverified.`;
 const reviews=(data.reference_topology?.candidate_assessments||[]).filter(a=>a.status==='review_required'&&[a.part_a,a.part_b].includes(selectedPart));if(reviews.length){const p=document.createElement('p');p.className='notice';p.textContent='Review required: '+[...new Set(reviews.map(r=>r.reason))].join(' ');$('atlasRelationEvidence').append(p)}
 const centerY=Math.ceil(sides[0].length/2)*100+48,height=centerY+Math.ceil(sides[1].length/2)*100+48;
 const position=(side,i)=>[i%2?202:8,side?centerY+100+Math.floor(i/2)*100:48+Math.floor(i/2)*100];
 svg.setAttribute('viewBox',`0 0 380 ${height}`);svg.style.height=height+'px';svg.parentElement.style.overflow='auto';svg.parentElement.style.maxHeight='460px';
 const make=(tag,attrs,parent=svg)=>{const el=document.createElementNS('http://www.w3.org/2000/svg',tag);for(const[k,v]of Object.entries(attrs))el.setAttribute(k,v);parent.append(el);return el};
 for(const[side,entries]of sides.entries())for(let i=0;i<entries.length;i++){const[x,y]=position(side,i),start=centerY+(side?32:-32),end=y+(side?-32:32);make('path',{d:`M 190 ${start} C 190 ${(start+end)/2}, ${x+85} ${(start+end)/2}, ${x+85} ${end}`,fill:'none',stroke:'#b8a16e','stroke-width':1.5,'stroke-dasharray':'5 4'})}
 const node=(id,x,y,w,chosen)=>{const part=parts.get(id),name=part?.name||id,color=part?.layer==='arterial'?'#f1767c':'#75baff';const g=make('g',{class:'relationshipNode',role:'button',tabindex:0,'aria-label':'Focus vessel '+name,style:'cursor:pointer'});make('rect',{x,y:y-32,width:w,height:64,rx:8,fill:chosen?'#29404c':'#1c303b',stroke:chosen?'#ffd38a':color,'stroke-width':chosen?2:1},g);const title=make('title',{},g);title.textContent=name+' · '+id;const words=name.split(' '),lines=[''];for(const word of words){const last=lines.length-1;if((lines[last]+' '+word).trim().length>20&&lines[last])lines.push(word);else lines[last]+=(lines[last]?' ':'')+word}const label=make('text',{x:x+9,y:y-15,fill:'#eef7fa','font-size':12,'pointer-events':'none'},g);for(const[lineIndex,line]of lines.slice(0,2).entries()){const span=make('tspan',{x:x+9,dy:lineIndex?15:0},label);span.textContent=lineIndex===1&&lines.length>2?line.slice(0,18)+'…':line}const code=make('text',{x:x+9,y:y+22,fill:color,'font-size':10,'pointer-events':'none'},g);code.textContent=(chosen?'Selected · ':'')+id;g.onclick=()=>post('/api/atlas-selection',{part_id:id});g.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();g.onclick()}}};
 node(selectedPart,105,centerY,170,true);sides.forEach((entries,side)=>entries.forEach(([id],i)=>{const[x,y]=position(side,i);node(id,x,y,170,false)}));
}
async function updateAtlasCenterlines(){
 const info=state?.atlas_centerlines||{};$('atlasCenterlinePanel').hidden=!isAtlas();if(!isAtlas())return;
 $('atlasCenterlinesVisible').checked=state.atlas_centerlines_visible??false;$('atlasCenterlinesVisible').disabled=pending||!info.available;
 $('atlasCenterlineStatus').textContent=info.busy?`Extracting atlas centerlines… ${info.completed??0}/${info.total??'?'} parts. The atlas remains available.`:info.error?'Centerline extraction: '+info.error:info.available?'Centerline graph available. Neighbor links are unverified proximity candidates.':'No atlas centerlines available yet.';
 if(info.available&&info.summary){const summary=Object.entries(info.summary).filter(([,v])=>typeof v==='number').map(([k,v])=>pretty(k)+': '+v).join(' · ');if(summary)$('atlasCenterlineStatus').textContent+=' '+summary}
 $('atlasCenterlineDownload').hidden=!info.available;
 if(info.available&&atlasCenterlineGeneration!==state.generation&&!atlasCenterlineFetching){atlasCenterlineFetching=true;const requestedGeneration=state.generation;try{const r=await fetch('/api/atlas-centerlines',{cache:'no-store'});if(!r.ok)throw Error('Centerline graph could not be loaded');const data=await r.json();if(state.generation===requestedGeneration){atlasCenterlineData=data;atlasCenterlineGeneration=requestedGeneration;drawAtlasCenterlines();syncAtlasModification()}}catch(error){$('atlasCenterlineStatus').textContent=error.message}finally{atlasCenterlineFetching=false}}
}
$('atlasCenterlinesVisible').onchange=()=>post('/api/atlas-centerlines-visibility',{visible:$('atlasCenterlinesVisible').checked});
function draw(){
 if(!state)return;
 if(isAtlas()){
  $('cerebralNotice').hidden=true;$('graph').replaceChildren();$('atlasParts').replaceChildren();
  const query=$('atlasSearch').value.trim().toLowerCase(),region=$('atlasRegion').value;let shown=0,total=0;
  const matches=part=>{if(query&&!`${part.name||''} ${part.id} ${part.layer||''}`.toLowerCase().includes(query))return false;if(region==='Whole body')return true;const b=part.bounds_source;if(!Array.isArray(b)||!Number.isFinite(b[0]?.[2])||!Number.isFinite(b[1]?.[2]))return false;const z=(b[0][2]+b[1][2])/2;const location=z>1400?'Head & neck':z>1150?'Thorax':z>900?'Abdomen':'Pelvis & femoral';return location===region};
  for(const [title,parts,estimated]of [['Source atlas structures',state.atlas?.parts||[],false],['Estimated missing vessels',state.neck_repairs?.parts||[],true]]){
   const vessels=parts.filter(part=>layerIds.includes(part.layer));total+=vessels.length;const filtered=vessels.filter(matches);shown+=filtered.length;if(!filtered.length)continue;
   const group=document.createElement('li'),heading=document.createElement('strong'),list=document.createElement('ul');heading.textContent=title;group.append(heading,list);group.style.marginBottom='14px';list.style.paddingLeft='8px';list.style.listStyle='none';
   for(const part of filtered){const li=document.createElement('li'),button=document.createElement('button');button.dataset.partId=part.id;button.textContent=`${part.name||part.id} · ${pretty(part.layer||'context')} (${part.id})${estimated?' · ESTIMATED':''}`;button.style.textAlign='left';button.onclick=()=>post('/api/atlas-selection',{part_id:part.id});li.style.marginBottom='8px';li.append(button);list.append(li)}$('atlasParts').append(group)
  }$('atlasCount').textContent=`${shown} / ${total} vessels`;syncAtlasSelection();return
 }
 const colors={arterial:'#e64c53',systemic_venous:'#5082eb',hepatic_portal:'#4db5f0'};
 $('graph').style.setProperty('--vessel-color',colors[$('layer').value]);
 const graph=currentGraph();const cerebral=!isReference()&&$('layer').value==='arterial'&&$('region').value==='Cerebral';$('cerebralNotice').hidden=!cerebral;
 const edges=graph.edges.filter(e=>$('region').value==='All regions'||group(e)===$('region').value);
 const svg=$('graph');svg.replaceChildren();const ids=[...new Set(edges.flatMap(e=>[e.start,e.end]))];const pos={};
 ids.sort((a,b)=>graph.nodes[b][2]-graph.nodes[a][2]||graph.nodes[a][0]-graph.nodes[b][0]);
 ids.forEach((id,i)=>{const x=graph.nodes[id][0];pos[id]=[x< -2?30:x>2?130:80,35+i*36]});
 if(cerebral){
  for(const side of ['left','right']){
   const lanes=side==='left'?{m:25,a:95,p:160}:{p:240,a:305,m:375};
   for(const [family,x]of Object.entries(lanes)){const artery={a:'aca',m:'mca',p:'pca'}[family];pos[`${side}_${artery}`]=[x,52];pos[`${side}_${family}2_end`]=[x,120];pos[`${side}_${family}1_end`]=[x,188]}
   pos[side+'_ica']=[side==='left'?65:335,304];
  }
  pos.basilar_tip=[200,356];pos.basilar_origin=[200,424];
 }
 const height=cerebral?455:Math.max(170,Math.max(ids.length,edges.length)*36+60);
 svg.setAttribute('viewBox',`0 0 400 ${height}`);svg.style.height=height+'px';
 const make=(tag,attrs)=>{const el=document.createElementNS('http://www.w3.org/2000/svg',tag);for(const[k,v]of Object.entries(attrs))el.setAttribute(k,v);svg.append(el);return el};
 if(cerebral){for(const[x,label]of [[92,'LEFT'],[300,'RIGHT']]){const t=make('text',{x,y:20,'text-anchor':'middle',class:'laneTitle'});t.textContent=label}}
 edges.forEach((e,i)=>{
  const a=pos[e.start],b=pos[e.end];let d=`M ${a} L ${b}`;let lx=(a[0]+b[0])/2+5,ly=(a[1]+b[1])/2;
  if(e.id==='acom'&&cerebral){d=`M ${a} C ${a[0]} 235, ${b[0]} 235, ${b}`;lx=185;ly=229}
  if(/pcom/.test(e.id)&&cerebral){const outer=e.id.startsWith('left')?118:282;d=`M ${a} Q ${outer} 292, ${b}`;lx=e.id.startsWith('left')?107:265;ly=272}
  make('path',{d,class:'edge'+(selected===e.id?' selected':'')});
  const hit=make('path',{d,class:'hit'});hit.onclick=()=>select(e.id);
  let label=pretty(e.id).replace('Splenic Artery','Splenic Artery (SA)');
  if(cerebral){const match=e.id.match(/_([amp][123])$/);if(match)label=match[1].toUpperCase();else label=e.id==='acom'?'ACom':e.id.includes('pcom')?'PCom':'Basilar'}
  else{ly=35+i*36;make('path',{d:`M ${lx} ${(a[1]+b[1])/2} L 161 ${ly-3}`,class:'leader'});lx=169}
  // Give each label an actual rectangular hit box: zero-width vertical SVG
  // paths are unreliable mouse/accessibility targets even with wide strokes.
  const button=make('rect',{x:lx-6,y:ly-16,width:cerebral?Math.max(34,label.length*7+10):224,height:29,rx:3,class:'edgeButton',tabindex:0,role:'button','aria-label':pretty(e.id)});
  button.onclick=()=>select(e.id);button.onkeydown=ev=>{if(ev.key==='Enter'||ev.key===' '){ev.preventDefault();select(e.id)}};
  const t=make('text',{x:lx,y:ly,class:'edgeLabel'});
  if(!cerebral&&label.length>32){const split=label.lastIndexOf(' ',32);const at=split>0?split:32;for(const [i,line]of [label.slice(0,at),label.slice(at).trim()].entries()){const span=document.createElementNS('http://www.w3.org/2000/svg','tspan');span.setAttribute('x',lx);span.setAttribute('dy',i?'11':'-4');span.textContent=line;t.append(span)}}else t.textContent=label;
  const title=document.createElementNS('http://www.w3.org/2000/svg','title');title.textContent=pretty(e.id);t.append(title);
 });
 ids.forEach(id=>{const[x,y]=pos[id];const c=make('circle',{cx:x,cy:y,r:4,class:'node'});const title=document.createElementNS('http://www.w3.org/2000/svg','title');title.textContent=pretty(id);c.append(title);c.onclick=()=>{const panel=$($('layer').value==='arterial'?'variation':'venousVariation');panel.open=true;panel.scrollIntoView({behavior:'smooth',block:'nearest'})}});
}
$('region').onchange=()=>{const edge=currentGraph().edges.find(e=>$('region').value==='All regions'||group(e)===$('region').value);if(edge)select(edge.id);else draw()};$('vessel').onchange=()=>select($('vessel').value);
function busy(on){$('controls').disabled=on;if(on)$('atlasModificationControls').disabled=true;$('openEditor').disabled=on;$('openAtlas').disabled=on||!state?.atlas?.available;for(const id of layerIds)$('show_'+id).disabled=on||(isReference()&&id!=='arterial');$('atlasContext').disabled=on;$('neckRepairs').disabled=on||!state?.neck_repairs?.available;$('source').disabled=on;$('layer').disabled=on||isReference();pending=on;$('veil').hidden=!on;if(on){$('veil').textContent='Updating anatomy…\nGraph and 3D update together';$('status').textContent='Updating…'}}
async function post(path,p,expectedGeneration){
 $('error').textContent='';busy(true);updateCandidateControls();syncAtlasModification();
 const headers={'Content-Type':'application/json'};
 if(path==='/api/anatomy')headers['X-Expected-Generation']=String(state.generation);
 if(path==='/api/atlas-modification')headers['X-Expected-Generation']=String(expectedGeneration);
 try{
  const r=await fetch(path,{method:'POST',headers,body:JSON.stringify(p)});const b=await r.json();
  if(r.status===409){
   await poll();
   $('error').textContent=b.code==='atlas_edit_recovery_required'?b.error:b.current_generation!==undefined?'This workspace changed in another tab. The latest model has been loaded. Review the controls and apply your edit again.':'The model is still updating. Wait for it to finish, then apply your edit again.';
   return;
  }
  if(!r.ok)throw Error(b.error);await poll();
 }catch(e){$('error').textContent=e.message;busy(false);updateCandidateControls();syncAtlasModification()}
}
const copy=()=>JSON.parse(JSON.stringify(state.parameters));
$('applyVessel').onclick=()=>{const p=copy();const base=$('layer').value==='arterial'?p:p.venous;base.vessel_parameters[selected]={radius_scale:+$('radius').value,tortuosity:+$('tort').value};post('/api/anatomy',p)};
$('resetVessel').onclick=()=>{const p=copy();const base=$('layer').value==='arterial'?p:p.venous;delete base.vessel_parameters[selected];post('/api/anatomy',p)};
$('applyVariation').onclick=()=>{const p=copy();p.arch_variant=$('variant').value;p.arch_height_ratio=+$('arch').value;p.absent_communicators=['acom','left_pcom','right_pcom'].filter(id=>!$(id).checked);post('/api/anatomy',p)};
$('applyVenous').onclick=()=>{const p=copy();p.venous.imv_drainage=$('imv').value;p.venous.transverse_dominance=$('dominance').value;post('/api/anatomy',p)};
for(const id of layerIds)$('show_'+id).onchange=()=>post('/api/visibility',Object.fromEntries(layerIds.map(key=>[key,$('show_'+key).checked])));
$('resetAll').onclick=()=>post('/api/anatomy',{radius_scale:1,tortuosity:.3,vessel_parameters:{},arch_height_ratio:.5,arch_variant:'standard',absent_communicators:[],venous:{radius_scale:1,tortuosity:.3,samples:64,vessel_parameters:{},imv_drainage:'splenic',transverse_dominance:'balanced'}});
$('applyView').onclick=()=>post('/api/view',Object.fromEntries(['access','target','mode','focus'].map(id=>[id,$(id).value])));
async function poll(){try{
 const r=await fetch('/api/state');const next=await r.json();if(next.busy){busy(true);return}if(next.error)$('error').textContent=next.error;
 const sourceChanged=(next.source||'schematic')!==(state?.source||'schematic');const changed=next.generation!==generation||sourceChanged;
 if(next.scene_description!==state?.scene_description){
  $('sceneLegendText').replaceChildren();$('sceneLegend').hidden=!next.scene_description;
  for(const paragraph of (next.scene_description||'').split(/\n\n/)){const p=document.createElement('p');p.textContent=paragraph.replace(/\*\*/g,'');$('sceneLegendText').append(p);}
 }
 state=next;generation=next.generation;
 for(const id of layerIds)$('show_'+id).checked=next.visibility?.[id]??true;
 $('boundaryContext').checked=next.annotation_context_visible??false;
 for(const button of vesselDisplay.querySelectorAll('button')){const v=next.visibility||{},mode=v.arterial&&v.systemic_venous&&v.hepatic_portal?'both':v.arterial&&!v.systemic_venous&&!v.hepatic_portal?'arteries':!v.arterial&&v.systemic_venous&&v.hepatic_portal?'veins':'';button.setAttribute('aria-pressed',String(button.dataset.mode===mode));button.classList.toggle('primary',button.dataset.mode===mode);button.disabled=pending;}
 if(changed){$('variant').value=state.parameters.arch_variant;$('arch').value=state.parameters.arch_height_ratio;$('archType').value=[.5,1.5,2.5].includes(state.parameters.arch_height_ratio)?String(state.parameters.arch_height_ratio).replace(/^0/,''):'custom';for(const id of ['acom','left_pcom','right_pcom'])$(id).checked=!state.parameters.absent_communicators.includes(id);$('imv').value=state.parameters.venous?.imv_drainage||'splenic';$('dominance').value=state.parameters.venous?.transverse_dominance||'balanced';if(isReference())$('layer').value='arterial';refreshLayer(sourceChanged||isReference())}
 busy(editSessionPending);sourceControls();updateCandidateControls();archMeasurement();clearanceScreening();if(isAtlas())syncAtlasSelection();updateAtlasCenterlines();showEditSessionStatus();const editSessionKey=JSON.stringify([state.source,generation,!!state.atlas_centerlines?.available]);if(editSessionGeneration!==editSessionKey){editSessionGeneration=editSessionKey;refreshEditSessionStatus()}const count=state.source==='candidate'?(state.candidate?.edge_ids||[]).length:isAtlas()?(state.atlas?.parts||[]).length:state.layers?Object.values(state.layers).reduce((n,g)=>n+g.edges.length,0):state.edges.length;$('status').textContent=`Generation ${generation} · ${count} ${isAtlas()?'atlas parts':'vessels'} · ${state.source||'schematic'}`;
}catch(e){$('error').textContent='Connection interrupted. Retrying…';$('status').textContent='Disconnected'}}
const annotationCard=atlasCard('4 · Cerebral boundary drafts');
annotationCard.innerHTML=`<p id="boundaryFrame">Source-bound coordinates. Drafts do not split vessels or certify anatomical boundaries.</p>
<label for="boundarySelect">Side · artery · transition</label><select id="boundarySelect"></select>
<p id="boundaryEvidence" role="status"></p>
<label for="boundaryReason">Unresolved reason</label><textarea id="boundaryReason" maxlength="4000" rows="3"></textarea>
<label for="boundaryNote">Review notes</label><textarea id="boundaryNote" maxlength="4000" rows="3"></textarea>
<label for="boundaryRefs">Evidence references · one per line</label><textarea id="boundaryRefs" rows="2"></textarea>
<label>Candidate XYZ · native source coordinates</label><div class="row"><input id="boundaryX" type="number" step="any" aria-label="Candidate source X"><input id="boundaryY" type="number" step="any" aria-label="Candidate source Y"><input id="boundaryZ" type="number" step="any" aria-label="Candidate source Z"></div>
<p class="tip">Leave all XYZ fields empty for no candidate. Coordinates remain an unreviewed draft; the authoritative boundary stays unresolved.</p>
<label><input id="boundaryContext" type="checkbox"> Show source corpus callosum and insula</label>
<p class="tip">ACom remains in the artery layer. <a href="https://dbarchive.biosciencedbc.jp/data/bodyparts3d/20130619/coordinate_system.png" target="_blank" rel="noopener noreferrer">Source coordinate definition</a>: mm; +X left, +Y posterior, +Z superior. Native origin, not a DICOM registration.</p>
<button id="boundaryFocus">Show saved candidate in 3D</button><div class="row"><button id="boundarySave" class="primary">Save draft</button><button id="boundaryReload">Reload saved drafts</button></div><p id="boundaryMessage" role="status">Load saved drafts to begin.</p>`;
for(const input of annotationCard.querySelectorAll('textarea,input[type=number]'))input.style.cssText='width:100%;background:#20323b;color:#ecf6f6;border:1px solid #425960;border-radius:6px;padding:8px';
let annotationData=null,annotationSaving=false;
function boundaryFrameRenderable(){const f=annotationData?.document.coordinate_frame;return f?.id==='bodyparts3d_native_LPS'&&f.units==='mm'&&f.frame_confirmed===true&&f.units_confirmed===true}
function showBoundary(){
 const b=annotationData?.document.boundaries.find(b=>b.boundary_id===$('boundarySelect').value);if(!b)return;
 const frame=annotationData.document.coordinate_frame;$('boundaryFrame').textContent=`${frame.id} · ${frame.units} · ${frame.frame_confirmed&&frame.units_confirmed?'source coordinate contract confirmed':'frame/units unconfirmed'}. Drafts do not certify anatomical boundaries.`;
 $('boundaryEvidence').textContent=b.evidence_status+' · '+b.landmark_type;
 $('boundaryReason').value=b.reason;$('boundaryNote').value=b.review_note;$('boundaryRefs').value=b.source_refs.join('\n');
 const xyz=annotationData.candidate_positions[b.boundary_id]||[];['X','Y','Z'].forEach((axis,i)=>$('boundary'+axis).value=xyz[i]??'');
 $('boundarySave').disabled=b.evidence_status!=='unresolved';
 $('boundaryFocus').disabled=!boundaryFrameRenderable()||!annotationData.candidate_positions[b.boundary_id];
}
async function loadBoundaryDrafts(){
 try{const cleared=await fetch('/api/annotation-clear',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});if(!cleared.ok)throw Error('Could not clear previous candidate display; retry reload');const response=await fetch('/api/atlas-annotations',{cache:'no-store'}),data=await response.json();if(!response.ok)throw Error(data.error);annotationData=data;
 const previous=$('boundarySelect').value;$('boundarySelect').replaceChildren(...data.document.boundaries.map(b=>new Option(`${b.side==='L'?'Left':'Right'} · ${b.artery} · ${b.transition.replace('_',' → ')}`,b.boundary_id)));
 if(data.document.boundaries.some(b=>b.boundary_id===previous))$('boundarySelect').value=previous;showBoundary();$('boundaryMessage').textContent='Loaded source-bound drafts. No reviewed boundary positions.';
 }catch(error){$('boundaryMessage').textContent=error.message;$('boundarySave').disabled=true}
}
$('boundarySelect').onchange=showBoundary;$('boundaryReload').onclick=loadBoundaryDrafts;
$('boundaryContext').onchange=()=>post('/api/annotation-context',{visible:$('boundaryContext').checked});
$('boundaryFocus').onclick=()=>post('/api/annotation-focus',{boundary_id:$('boundarySelect').value});
$('boundarySave').disabled=true;
$('boundarySave').onclick=async()=>{
 if(!annotationData||annotationSaving)return;annotationSaving=true;$('boundarySave').disabled=true;
 try{const raw=['X','Y','Z'].map(axis=>$('boundary'+axis).value.trim());if(raw.some(Boolean)&&!raw.every(Boolean))throw Error('Enter all three coordinates or leave all empty');
 const payload={revision:annotationData.revision,boundary_id:$('boundarySelect').value,reason:$('boundaryReason').value,review_note:$('boundaryNote').value,source_refs:$('boundaryRefs').value.split('\n').map(s=>s.trim()).filter(Boolean),candidate_position:raw.every(Boolean)?raw.map(Number):null};
 const response=await fetch('/api/atlas-annotations',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)}),data=await response.json();if(!response.ok)throw Error(data.error);
 annotationData=data;$('boundaryFocus').disabled=!boundaryFrameRenderable()||!data.candidate_positions[$('boundarySelect').value];$('boundaryMessage').textContent='Draft saved locally. Boundary remains unresolved.';
 }catch(error){$('boundaryMessage').textContent=error.message}finally{annotationSaving=false;$('boundarySave').disabled=false}
};
const caseCard=atlasCard('5 · Source case data');
caseCard.insertAdjacentHTML('beforeend','<p><a href="/case-labels" target="_blank" rel="noopener">Label a saved case →</a></p>');
caseCard.insertAdjacentHTML('beforeend',`<p>원본 경로만 준비하거나, 현재 동맥 표면과 편집 기록을 함께 담을 수 있습니다. 대응 경로가 없는 구조는 누락 목록에 기록됩니다. 사례를 불러와도 3D 장면은 바뀌지 않습니다.</p>
<p id="caseSummary" role="status">No case data loaded.</p>
<div class="row"><button id="casePrepare">Prepare source case</button><button id="caseReload">Reload saved data</button></div>
<button id="casePrepareCurrent">현재 동맥 표면·편집으로 사례 준비</button>
<div class="row"><button id="caseSave" disabled>Save case data</button><button id="caseDownload" disabled>Download case JSON</button></div>
<button id="caseRefresh">Refresh case status</button><p id="caseMessage" role="status"></p>`);
let caseState=null,casePending=false;
function showCaseStatus(data){caseState=data;const s=data.summary;
 $('caseSummary').textContent=s?`${s.case_id} · ${s.model_kind} · ${s.edges} paths · ${s.nodes} nodes · ${s.surface_parts||0} surfaces · ${s.unresolved_edges} unresolved paths. ${data.includes_atlas_edits?'Atlas 편집 포함. ':''}${data.includes_estimates?'추정 형상 포함 · 해부학적 연결 미검증. ':''}Data only; not rendered.`:'No case data loaded. The displayed Atlas is separate.';
 $('caseSave').disabled=!data.loaded;$('caseDownload').disabled=!data.loaded;
 $('caseReload').disabled=!data.file_exists;
}
async function refreshCaseStatus(){try{const r=await fetch('/api/case-workspace',{cache:'no-store'}),d=await r.json();if(!r.ok)throw Error(d.error);showCaseStatus(d)}catch(e){$('caseMessage').textContent=e.message}}
async function caseAction(action){if(casePending||!caseState)return;casePending=true;for(const b of caseCard.querySelectorAll('button'))b.disabled=true;
 try{const r=await fetch('/api/case-workspace',{method:'POST',headers:{'Content-Type':'application/json','X-Expected-Generation':String(state.generation)},body:JSON.stringify({action,version:caseState.version})}),d=await r.json();if(!r.ok)throw Error(d.error);showCaseStatus(d);
 $('caseMessage').textContent=action==='save'?'준비된 사례 데이터를 저장했습니다.':action==='reload'?'Saved case data loaded. The 3D Atlas scene has not changed.':action==='prepare_current'?'현재 동맥 표면과 편집 기록을 사례에 담았습니다. 연결·구간 경계의 해부학적 확인은 별도입니다.':'Original arterial case prepared. Anatomical connections and segment boundaries remain unconfirmed.';
 }catch(e){$('caseMessage').textContent=e.message}finally{casePending=false;for(const b of caseCard.querySelectorAll('button'))b.disabled=false;if(caseState)showCaseStatus(caseState)}}
$('casePrepare').onclick=()=>caseAction('prepare');$('caseReload').onclick=()=>caseAction('reload');$('caseSave').onclick=()=>caseAction('save');$('caseRefresh').onclick=refreshCaseStatus;
$('casePrepareCurrent').onclick=()=>caseAction('prepare_current');
$('caseDownload').onclick=async()=>{try{const r=await fetch('/api/case-download',{cache:'no-store'});if(!r.ok)throw Error((await r.json()).error);const url=URL.createObjectURL(await r.blob()),a=document.createElement('a');a.href=url;a.download='vv-source-case.snapshot.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}catch(e){$('caseMessage').textContent=e.message}};
refreshCaseStatus();loadBoundaryDrafts();poll();setInterval(poll,1200);
</script></html>'''

from .interval_preview_ui import SCRIPT as INTERVAL_PREVIEW_SCRIPT
HTML = HTML.replace('</script>', INTERVAL_PREVIEW_SCRIPT + '</script>')
