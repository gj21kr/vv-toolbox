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
</aside><section id="stage"><iframe title="Interactive 3D vessel model" src="http://127.0.0.1:__VISER_PORT__"></iframe><div id="veil">Building anatomy…</div></section></main>
<script>
const $=id=>document.getElementById(id); let state=null, selected='left_aca_a1',generation=-1,pending=false,referenceRendered='',clearanceRendered='';
// Keep legacy controls detached from the visible Atlas workspace for API compatibility.
const sidebar=document.querySelector('aside'),legacy=document.createElement('div');legacy.id='legacyWorkspace';legacy.hidden=true;while(sidebar.firstChild)legacy.append(sidebar.firstChild);sidebar.append(legacy);
const atlasWorkspace=document.createElement('div');atlasWorkspace.id='atlasWorkspace';sidebar.append(atlasWorkspace);
function atlasCard(title){const card=document.createElement('section');card.className='atlasCard';if(title){const heading=document.createElement('h2');heading.textContent=title;card.append(heading)}atlasWorkspace.append(card);return card}
const availability=atlasCard('Atlas workspace');availability.id='atlasAvailability';availability.textContent='Loading Atlas…';
const browseCard=atlasCard('1 · Select a vessel');browseCard.append($('atlasBrowse'));const vesselList=document.createElement('div');vesselList.className='atlasList';vesselList.append($('atlasParts'));const listDetails=document.createElement('details'),listTitle=document.createElement('summary');listTitle.textContent='Browse matching vessels';listDetails.open=true;listDetails.append(listTitle,vesselList);browseCard.append(listDetails);$('atlasBrowse').querySelector('.tip').hidden=true;
const relationCard=atlasCard('2 · Vessel relationships');relationCard.append($('atlasCenterlinePanel'));const relationSummary=document.createElement('p');relationSummary.id='atlasRelationSummary';$('atlasCenterlinePanel').prepend(relationSummary);
const extractionDetails=document.createElement('details'),extractionTitle=document.createElement('summary');extractionTitle.textContent='Centerline extraction details';extractionDetails.append(extractionTitle,$('atlasCenterlineStatus'),$('atlasCenterlineDownload'));for(const p of [...$('atlasCenterlinePanel').querySelectorAll(':scope > p.tip')])extractionDetails.append(p);$('atlasCenterlinePanel').append(extractionDetails);
const modificationCard=atlasCard('');modificationCard.append($('atlasModificationPanel'));$('atlasModificationPanel').querySelector('h2').textContent='3 · Modify selected vessel';$('applyAtlasModification').textContent='Apply modification';$('resetAtlasModification').textContent='Restore original';
const modificationLabel=document.createElement('label');modificationLabel.htmlFor='atlasModificationVessel';modificationLabel.textContent='Vessel selection';
const modificationSelect=document.createElement('select');modificationSelect.id='atlasModificationVessel';modificationSelect.title='Select the vessel to modify';
$('atlasModificationName').before(modificationLabel,modificationSelect);
modificationSelect.onchange=()=>{if(modificationSelect.value)post('/api/atlas-selection',{part_id:modificationSelect.value})};
let modificationOptionsKey='';
const optionsCard=atlasCard(''),displayDetails=document.createElement('details'),displayTitle=document.createElement('summary');displayTitle.textContent='Display options';displayDetails.append(displayTitle);optionsCard.append(displayDetails);displayDetails.append($('show_arterial').closest('.row'),$('atlasCenterlinesVisible').closest('label'),$('atlasContextLabel'),$('neckRepairsPanel'));
const viewDetails=$('applyView').closest('details');viewDetails.querySelector('summary').textContent='Camera focus';displayDetails.append(viewDetails);$('mode').previousElementSibling.hidden=true;$('mode').hidden=true;
const advancedCard=atlasCard(''),advanced=document.createElement('details'),advancedTitle=document.createElement('summary');advancedTitle.textContent='Source & reconstruction details';advanced.append(advancedTitle,$('atlasInspector'));advancedCard.append(advanced);const repairsDetails=$('neckRepairsPanel').querySelector('details');advanced.append(repairsDetails);for(const p of [...$('neckRepairsPanel').querySelectorAll(':scope > p')])advanced.append(p);advanced.append($('referenceReadOnly'));atlasWorkspace.append($('error'));
const layerIds=['arterial','systemic_venous','hepatic_portal'];
const isReference=()=>state?.source==='reference';
const isAtlas=()=>state?.source==='atlas';
const isReadOnly=()=>isReference()||isAtlas();
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
 const optionsKey=vessels.map(p=>p.id).join('|');
 if(optionsKey!==modificationOptionsKey){
  modificationOptionsKey=optionsKey;modificationSelect.replaceChildren(new Option('Select a vessel…',''));
  for(const [layer,title]of [['arterial','Arteries'],['systemic_venous','Systemic veins'],['hepatic_portal','Portal veins']]){
   const group=document.createElement('optgroup');group.label=title;
   for(const vessel of vessels.filter(p=>p.layer===layer).sort((a,b)=>(a.name||a.id).localeCompare(b.name||b.id)))group.append(new Option(`${vessel.name||vessel.id} · ${vessel.id}`,vessel.id));
   modificationSelect.append(group);
  }
 }
 const id=state.atlas_selection,part=vessels.find(p=>p.id===id);
 modificationSelect.value=id||'';modificationSelect.disabled=pending||!vessels.length;
 const ready=state.atlas_centerlines?.available&&atlasCenterlineGeneration===state.generation;
 const editable=ready&&(atlasCenterlineData?.edges||[]).some(edge=>edge.part_id===id);
 const key=JSON.stringify([id,state.generation]);
 if(key!==atlasModificationKey){atlasModificationKey=key;atlasModificationGeneration=state.generation;atlasModificationPart=id;const p=state.atlas_modifications?.[id]||{};$('atlasRadius').value=p.radius_scale??1;$('atlasTortuosity').value=p.tortuosity??0;$('atlasTorsion').value=p.torsion_deg??0;atlasModificationValues()}
 $('atlasModificationName').textContent=part?`${part.name||id} · ${id}`:'Select an atlas vessel';
 $('atlasModificationControls').disabled=pending||!editable;
 $('atlasModificationStatus').textContent=!part?'Select a vessel from the atlas list or graph.':!ready?'Waiting for the current centerline graph.':!editable?'This structure has no extracted centerline and cannot be modified.':state.atlas_modifications?.[id]?'Local modification applied to this vessel.':'Original geometry · adjustments are relative to this baseline.';
}
for(const id of ['atlasRadius','atlasTortuosity','atlasTorsion'])$(id).oninput=atlasModificationValues;
$('applyAtlasModification').onclick=()=>post('/api/atlas-modification',{part_id:atlasModificationPart,radius_scale:+$('atlasRadius').value,tortuosity:+$('atlasTortuosity').value,torsion_deg:+$('atlasTorsion').value},atlasModificationGeneration);
$('resetAtlasModification').onclick=()=>post('/api/atlas-modification',{part_id:atlasModificationPart,radius_scale:1,tortuosity:0,torsion_deg:0},atlasModificationGeneration);
function drawAtlasCenterlines(){
 const data=atlasCenterlineData;if(!data)return;atlasCenterlineLastSelection=state?.atlas_selection;
 const svg=$('atlasCenterlineGraph');svg.replaceChildren();svg.setAttribute('aria-label','Atlas vessel relationship graph');
 const selectedPart=state?.atlas_selection,parts=new Map([...(state.atlas?.parts||[]),...(state.neck_repairs?.parts||[])].map(p=>[p.id,p]));
 if(!selectedPart){svg.style.height='0px';$('atlasRelationSummary').textContent='Select a vessel above to view neighboring vessel candidates.';return}
 const links=(data.links||[]).filter(l=>l.part_a===selectedPart||l.part_b===selectedPart),neighbors=new Map();
 for(const link of links){const id=link.part_a===selectedPart?link.part_b:link.part_a;if(id===selectedPart)continue;const previous=neighbors.get(id);if(!previous||link.distance<previous.distance)neighbors.set(id,link)}
 const shown=[...neighbors].sort((a,b)=>(a[1].distance??Infinity)-(b[1].distance??Infinity)||a[0].localeCompare(b[0])).slice(0,4);
 const ownEdges=(data.edges||[]).filter(e=>e.part_id===selectedPart).length;
 $('atlasRelationSummary').textContent=`${neighbors.size} neighboring candidate${neighbors.size===1?'':'s'}${neighbors.size>shown.length?` · nearest ${shown.length} shown`:''}. Dashed links are unverified connections.`;
 const height=Math.max(150,shown.length*68+12),centerY=height/2;svg.setAttribute('viewBox',`0 0 380 ${height}`);svg.style.height=height+'px';
 const make=(tag,attrs,parent=svg)=>{const el=document.createElementNS('http://www.w3.org/2000/svg',tag);for(const[k,v]of Object.entries(attrs))el.setAttribute(k,v);parent.append(el);return el};
 for(let i=0;i<shown.length;i++){const y=38+i*68;make('path',{d:`M 157 ${centerY} C 188 ${centerY}, 188 ${y}, 214 ${y}`,fill:'none',stroke:'#b8a16e','stroke-width':1.5,'stroke-dasharray':'5 4'})}
 const node=(id,x,y,w,chosen)=>{const part=parts.get(id),name=part?.name||id,color=part?.layer==='arterial'?'#f1767c':'#75baff';const g=make('g',{class:'relationshipNode',role:'button',tabindex:0,'aria-label':'Focus vessel '+name,style:'cursor:pointer'});make('rect',{x,y:y-32,width:w,height:64,rx:8,fill:chosen?'#29404c':'#1c303b',stroke:chosen?'#ffd38a':color,'stroke-width':chosen?2:1},g);const title=make('title',{},g);title.textContent=name+' · '+id;const words=name.split(' '),lines=[''];for(const word of words){const last=lines.length-1;if((lines[last]+' '+word).trim().length>20&&lines[last])lines.push(word);else lines[last]+=(lines[last]?' ':'')+word}const label=make('text',{x:x+9,y:y-15,fill:'#eef7fa','font-size':12,'pointer-events':'none'},g);for(const[lineIndex,line]of lines.slice(0,2).entries()){const span=make('tspan',{x:x+9,dy:lineIndex?15:0},label);span.textContent=lineIndex===1&&lines.length>2?line.slice(0,18)+'…':line}const code=make('text',{x:x+9,y:y+22,fill:color,'font-size':10,'pointer-events':'none'},g);code.textContent=(chosen?'Selected · ':'')+id;g.onclick=()=>post('/api/atlas-selection',{part_id:id});g.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();g.onclick()}}};
 node(selectedPart,7,centerY,150,true);shown.forEach(([id],i)=>node(id,214,38+i*68,159,false));
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
 $('error').textContent='';busy(true);syncAtlasModification();
 const headers={'Content-Type':'application/json'};
 if(path==='/api/anatomy')headers['X-Expected-Generation']=String(state.generation);
 if(path==='/api/atlas-modification')headers['X-Expected-Generation']=String(expectedGeneration);
 try{
  const r=await fetch(path,{method:'POST',headers,body:JSON.stringify(p)});const b=await r.json();
  if(r.status===409){
   await poll();
   $('error').textContent=b.current_generation!==undefined?'This workspace changed in another tab. The latest model has been loaded. Review the controls and apply your edit again.':'The model is still updating. Wait for it to finish, then apply your edit again.';
   return;
  }
  if(!r.ok)throw Error(b.error);await poll();
 }catch(e){$('error').textContent=e.message;busy(false);syncAtlasModification()}
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
 const sourceChanged=(next.source||'schematic')!==(state?.source||'schematic');const changed=next.generation!==generation||sourceChanged;state=next;generation=next.generation;
 for(const id of layerIds)$('show_'+id).checked=next.visibility?.[id]??true;
 if(changed){$('variant').value=state.parameters.arch_variant;$('arch').value=state.parameters.arch_height_ratio;$('archType').value=[.5,1.5,2.5].includes(state.parameters.arch_height_ratio)?String(state.parameters.arch_height_ratio).replace(/^0/,''):'custom';for(const id of ['acom','left_pcom','right_pcom'])$(id).checked=!state.parameters.absent_communicators.includes(id);$('imv').value=state.parameters.venous?.imv_drainage||'splenic';$('dominance').value=state.parameters.venous?.transverse_dominance||'balanced';if(isReference())$('layer').value='arterial';refreshLayer(sourceChanged||isReference())}
 busy(false);sourceControls();archMeasurement();clearanceScreening();if(isAtlas())syncAtlasSelection();updateAtlasCenterlines();const count=isAtlas()?(state.atlas?.parts||[]).length:state.layers?Object.values(state.layers).reduce((n,g)=>n+g.edges.length,0):state.edges.length;$('status').textContent=`Generation ${generation} · ${count} ${isAtlas()?'atlas parts':'vessels'} · ${state.source||'schematic'}`;
}catch(e){$('error').textContent='Connection interrupted. Retrying…';$('status').textContent='Disconnected'}}
poll();setInterval(poll,1200);
</script></html>'''
