"""Stateless saved-case editing; never reads or writes server-side case files."""
from copy import deepcopy
import json
import math
import hashlib

from .anatomical_labels import REGISTRY, assign_access_labels, resolve_labels
from .case_io import case_digest, _encode, _unique_object


def process_request(request):
    if not isinstance(request,dict):
        raise ValueError('Expected action, snapshot and assignments')
    action=request.get('action')
    expected={'action','snapshot','parameters' if action in ('smooth','containment','shape') else 'assignments'}
    if set(request)!=expected:
        raise ValueError('Unexpected workbench request fields')
    if action not in ('inspect','apply','smooth','containment','shape','context'):
        raise ValueError('Unknown label action')
    snapshot=request['snapshot']
    if isinstance(snapshot,str):
        snapshot=json.loads(snapshot,object_pairs_hook=_unique_object)
    if (not isinstance(snapshot,dict) or set(snapshot)!={'schema','revision','case'}
            or snapshot['schema']!='vv-toolbox.case-snapshot/1'):
        raise ValueError('Case snapshot required')
    case=snapshot['case']
    revision=case_digest(case)
    if snapshot['revision']!=revision:
        raise ValueError('Snapshot revision mismatch')
    if action=='containment':
        from .workbench_containment import inspect_edge
        parameters=request['parameters']
        if not isinstance(parameters,dict) or set(parameters)!={'edge_id'}:
            raise ValueError('Select one edge for source-surface comparison')
        return dict(inspection=inspect_edge(case,parameters['edge_id']))
    if action=='apply':
        case=assign_access_labels(case,request['assignments'],expected_revision=revision)
        revision=case_digest(case)
    elif action=='smooth':
        case=_smooth_copy(case,request['parameters'])
        revision=case_digest(case)
    elif action=='shape':
        from .registered_shape_edit import deform_registered_source
        parameters=request['parameters']
        if not isinstance(parameters,dict) or set(parameters)!={
                'edge_id','bend_mm','bend_direction','twist_deg','collar_mm','transition_mm','max_displacement_mm'}:
            raise ValueError('Explicit registered shape parameters required')
        case=deform_registered_source(case,**parameters)
        revision=case_digest(case)
    elif action=='context':
        from pathlib import Path
        from .registered_context_evidence import attach_registered_context
        if request['assignments']!=[]:
            raise ValueError('Context lookup must not contain assignments')
        case=attach_registered_context(case,Path(__file__).resolve().parents[2])
        revision=case_digest(case)
    elif request['assignments']!=[]:
        raise ValueError('Inspect must not contain assignments')
    ids=[e['id'] for e in case['edges']]
    labels,_=resolve_labels(case,ids)
    envelope=dict(schema='vv-toolbox.case-snapshot/1',revision=revision,case=deepcopy(case))
    from .registered_shape_edit import source_edit_options
    return dict(snapshot=envelope,snapshot_json=_encode(envelope).decode('utf-8'),
        shape_edit_options=source_edit_options(case),
        edges=[dict(id=e['id'],anatomy=deepcopy(e['anatomy']),label_id=labels[e['id']])
               for e in case['edges']],
        labels=deepcopy(REGISTRY['labels'][12:]),anatomical_acceptance='UNKNOWN')


def _smooth_copy(case, parameters):
    """Expose bounded single-edge smoothing, keeping source data independent."""
    from .centerline_regularization import smooth_synthetic_centerlines
    if not isinstance(parameters,dict) or set(parameters)!={'edge_id','sigma_mm','max_displacement_mm'}:
        raise ValueError('Select an edge, smoothing width and displacement bound')
    sigma=parameters['sigma_mm'];bound=parameters['max_displacement_mm']
    if (type(sigma) not in (int,float) or not math.isfinite(sigma) or not .05<=sigma<=5
            or type(bound) not in (int,float) or not math.isfinite(bound) or not 0<bound<=10):
        raise ValueError('Workbench limits: width 0.05–5 mm; displacement >0 and <=10 mm')
    edge=next((e for e in case['edges'] if e['id']==parameters['edge_id']),None)
    if edge is None or edge['centerline_mm'] is None:
        raise ValueError('Known edge with centerline required')
    spacing=sigma/4
    length=sum(math.dist(a,b) for a,b in zip(edge['centerline_mm'],edge['centerline_mm'][1:]))
    if math.ceil(length/spacing)+1>50000:
        raise ValueError('Interactive resampling budget exceeded; increase smoothing width')
    parent=case_digest(case)
    derived=deepcopy(case)
    if derived['model_kind']=='source':
        derived.update(model_kind='synthetic',generation=dict(seed=0,
            generator_version='workbench-source-copy/1',config=dict(parent_case_revision=parent)))
    derived.setdefault('history',[]).append(dict(operation='workbench-centerline-copy/1',
        parent_case_revision=parent,scope='separate synthetic centerline edit'))
    operation_id=hashlib.sha256(_encode(dict(parent_revision=parent,parameters=parameters))).hexdigest()[:20]
    return smooth_synthetic_centerlines(derived,[parameters['edge_id']],sigma_mm=sigma,
        sample_spacing_mm=spacing,max_displacement_mm=bound,
        case_id=f'workbench-smoothed:{operation_id}')


HTML = r'''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>VV Toolbox · Saved case labels</title>
<style>
body{font:16px/1.6 system-ui;background:#10191f;color:#e8eff3;margin:0}
main{max-width:900px;margin:32px auto;padding:24px}h1{font-size:28px}
a{color:#73d7ce}label{display:block;margin:20px 0 6px;font-weight:600}
input,select,textarea,button{box-sizing:border-box;font:inherit;padding:10px;border-radius:6px;
border:1px solid #607985;background:#1c2b34;color:#fff;max-width:100%}
input:not([type=file]):not([type=checkbox]),select,textarea{width:100%}button{cursor:pointer;margin:16px 12px 0 0}
button:disabled{opacity:.45;cursor:default}.muted{color:#b6c8d1}
#status,#containmentResult{padding:12px;background:#20313a;white-space:pre-wrap;overflow-wrap:anywhere}
canvas{display:block;width:100%;height:340px;touch-action:none;border:1px solid #607985;border-radius:6px;box-sizing:border-box}
#relationships{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,300px),1fr));gap:16px}
.relationship{border:1px solid #607985;border-radius:6px;padding:12px;min-width:0;overflow-wrap:anywhere}
.relationship button{display:block;width:100%;text-align:left;white-space:normal;overflow-wrap:anywhere}
</style><main><a href="/">← VV Toolbox</a><h1>Saved case labels</h1>
<p>Load a case snapshot, select an edge, and declare its whole-edge access-vessel label.
Download creates a separate file. The Atlas scene and files on the server are unchanged.</p>
<p class="muted">Labels are operator declarations. They do not confirm anatomical boundaries.
An atlas fragment is not necessarily a complete vessel.</p>
<p id="savedInspection" role="status">저장된 검사 기록: 사례를 불러오세요.</p>
<details id="contactReview" hidden><summary>주변 혈관 접촉 검사 상세</summary>
<p id="contactSummary"></p>
<p class="muted">추가·제거 수는 삼각형 접촉 쌍의 변화입니다. 실제 관통 부피나 새로 접촉한 혈관 수가 아닙니다. 정상 분지 여부는 별도 확인이 필요합니다.</p>
<div style="overflow:auto;max-height:360px"><table style="width:100%;text-align:left"><thead><tr><th>상대 혈관 ID</th><th>변경 전</th><th>변경 후</th><th>추가 쌍</th><th>제거 쌍</th></tr></thead><tbody id="contactRows"></tbody></table></div>
</details>
<label for="file">1 · Case snapshot (.json, up to 16 MB)</label><input id="file" type="file" accept=".json,application/json">
<label for="search">2 · Find an edge</label><input id="search" type="search" placeholder="Name, side, or edge ID" disabled>
<label for="edge">Matching edges</label><select id="edge" size="7" disabled></select>
<p id="selection" class="muted">No case loaded.</p>
<label for="preview">Saved surface and centerlines</label>
<label><input id="showSurface" type="checkbox" checked> 등록 표면</label>
<label><input id="showCenterlines" type="checkbox" checked> 중심선 (표면 위에 표시)</label>
<p id="surfaceStatus" role="status"></p>
<canvas id="preview" tabindex="0" aria-label="Rotatable centerline preview; drag or use arrow keys to rotate, scroll to zoom, click a line to select"></canvas>
<button id="fit">Reset view</button><button id="focus">Focus selected edge</button>
<p class="muted">Drag or use arrow keys to rotate · Scroll to zoom · Click a line to select.
Registered triangles are shown without reconstruction. Centerlines overlay the surface and may be behind it in 3D.
Overlapping projections can be ambiguous—rotate and check the selected ID.</p>
<h2>Recorded connections at both ends</h2>
<p class="muted">These are shared nodes in the saved graph, not inferred contacts.
First/last follow centerline point order and do not indicate blood-flow direction.</p>
<div id="relationships"></div>
<details><summary>Modify selected centerline</summary>
<p>Creates a separate synthetic case. Endpoints, endpoint chords and radii stay fixed.
This does not check vessel-surface collisions or anatomical validity.</p>
<label for="sigma">Smoothing width (mm, 0.05–5)</label><input id="sigma" type="number" min="0.05" max="5" step="0.05" value="0.5">
<label for="bound">Maximum allowed displacement (mm, up to 10)</label><input id="bound" type="number" min="0.001" max="10" step="0.1" value="0.3">
<button id="smooth" disabled>Smooth in synthetic copy</button>
<p class="muted">These are numerical controls, not clinical ranges. Requires an open path with at least five points and no existing lesion on it.</p></details>
<details id="shapePanel"><summary>혈관 벽·중심선 굴곡 / 회전</summary>
<p>별도 검사 후보를 만듭니다. 굴곡은 변위이며 tortuosity 목표값이 아닙니다. 회전은 양 끝을 잇는 축 기준이며 미분 torsion이 아닙니다.</p>
<p id="shapeEligibility"></p>
<label>굴곡 변위 (mm)<input id="shapeBend" type="number" step="0.05" value="0.25"></label>
<label>굴곡 방향 (LPS)<select id="shapeDirection"><option value="1,0,0">X · Left</option><option value="0,1,0">Y · Posterior</option><option value="0,0,1">Z · Superior</option></select></label>
<label>축 주위 회전 (°)<input id="shapeTwist" type="number" step="1" value="0"></label>
<label>접합 고정 거리 (mm)<input id="shapeCollar" type="number" min="0" step="0.1" value="1"></label>
<label>전이 거리 (mm)<input id="shapeTransition" type="number" min="0.01" step="1" value="10"></label>
<label>최대 이동 허용값 (mm)<input id="shapeBound" type="number" min="0.01" step="0.1" value="1"></label>
<button id="shape" disabled>벽·중심선 변경 후보 만들기</button>
<button id="shapeContext" disabled>이 사례에 대응하는 주변 검사 불러오기</button>
<button id="shapeContextRun" disabled>새 주변 검사 실행 / 이어 보기</button>
<p id="contextProgress" role="status">새 검사는 시간이 걸립니다. 창을 닫아도 서버 작업은 계속됩니다. 같은 사례를 다시 열어 이어 볼 수 있습니다.</p>
<p>수치 입력은 실험 조건입니다. 주변 혈관과의 접촉 및 반경 일치는 별도 검사이며, 생성 승인으로 처리하지 않습니다. 검사에 수 분이 걸릴 수 있습니다.</p></details>
<h2>Check selected centerline</h2>
<p class="muted">Compare the entire centerline with its declared original Atlas surface.
This does not check vessel walls, radii, other vessels or anatomical correctness.</p>
<button id="containment" disabled>Check against original surface</button>
<p id="containmentResult" role="status">NOT RUN · Select an edge to check.</p>
<label for="label">3 · Whole-edge label</label><select id="label" disabled></select>
<label for="refs">Evidence covering the entire selected edge (one reference per line)</label>
<textarea id="refs" rows="3" disabled placeholder="Source annotation or extent review reference"></textarea>
<button id="apply" disabled>Apply label to copy</button><button id="download" disabled>Download current case</button>
<div><button id="undo" disabled>Undo change</button><button id="redo" disabled>Redo change</button></div>
<p id="historyStatus" class="muted">Up to 20 changes can be undone in this tab.</p>
<p id="status" role="status" aria-live="polite">Choose a saved case to begin.</p>
<script src="/case-preview.js"></script><script>
const $=id=>document.getElementById(id);
let data=null,busy=false,edited=false,undoStack=[],redoStack=[],savedRevision=null;
const preview=new VVCasePreview($('preview'),id=>{
 if(busy||!data)return;
 if(![...$('edge').options].some(o=>o.value===id)){$('search').value='';filter();}
 $('edge').value=id;$('refs').value='';selection();
});
$('fit').onclick=()=>preview.fit();
$('focus').onclick=()=>preview.focus();
$('showSurface').onchange=()=>{preview.showSurface=$('showSurface').checked;preview.draw();};
$('showCenterlines').onchange=()=>{preview.showCenterlines=$('showCenterlines').checked;preview.draw();};
function controls(){for(const id of ['file','search','edge','label','refs','apply','download'])
 $(id).disabled=busy||(id!=='file'&&!data)||(id==='apply'&&(!$('edge').value||!$('label').value));
 const saved=data?.snapshot.case.inspection?.access_candidate;
 const shape=data?.snapshot.case.inspection?.registered_shape_edit;
 const contact=shape?.context;
 $('contactReview').hidden=!Array.isArray(contact?.rows);
 $('contactRows').replaceChildren();
 if(Array.isArray(contact?.rows)){
  $('contactSummary').textContent=`저장된 검사 ${contact.completed??contact.rows.length}/${contact.neighbor_count??contact.rows.length}개 · ${contact.status} · 잔존 접촉 ${contact.remaining_contacts?.length??'미확인'}개 · 미확인 ${contact.unknown?.length??'미확인'}개. 접촉 또는 미확인 항목을 모두 표시합니다.`;
  const rows=contact.rows.filter(r=>r.before?.status!=='SEPARATED'||r.after?.status!=='SEPARATED'||r.added_contact_pairs?.length||r.removed_contact_pairs?.length);
  rows.sort((a,b)=>(b.added_contact_pairs?.length||0)-(a.added_contact_pairs?.length||0)||String(a.neighbor_id).localeCompare(String(b.neighbor_id)));
  for(const row of rows){const tr=document.createElement('tr');
   for(const value of [row.neighbor_id,row.before?.status??'UNKNOWN',row.after?.status??'UNKNOWN',row.added_contact_pairs?.length??0,row.removed_contact_pairs?.length??0]){
    const td=document.createElement('td');td.textContent=String(value);td.style.padding='8px';tr.append(td);}
   $('contactRows').append(tr);
  }
 }
 $('shapeContext').disabled=busy||!shape||!!shape.context_binding;
 $('shapeContextRun').disabled=busy||!shape;
 $('savedInspection').textContent=!data?'저장된 검사 기록: 사례를 불러오세요.':
  `등록 표면 ${data.snapshot.case.surface_parts?.length||0}개 보존. `+
  (shape?`벽 변경 후보 · 주변 검사: ${shape.neighboring_vessels} · 생성 미승인. 부모 검사 기록은 이력으로 보존됩니다.`:saved?`저장 당시 주변 검사: ${saved.context?.status??saved.summary?.access_union?.context_status??'UNKNOWN'}. `+
   `생성 승인: ${saved.accepted_for_generation===false?'미승인':saved.accepted_for_generation===true?'파일에 승인 기록 있음':'미확인'}. `+
   '이 기록은 현재 변경 사항의 재검사 결과가 아닙니다.':'접근 후보 검사 기록 없음 · 수용 여부 미확인.');
 $('surfaceStatus').textContent=preview.surfaceError?'표면 표시 불가: '+preview.surfaceError:
  preview.surfaceTriangles?`등록 삼각형 ${preview.surfaceTriangles.toLocaleString()}개 · 저장된 좌표 사용 · 형상 수용 검증과 별개`:'등록 표면 없음 · 중심선만 표시';
 $('undo').disabled=busy||!undoStack.length;$('redo').disabled=busy||!redoStack.length;
 $('historyStatus').textContent=`Undo: ${undoStack.length}/20 · Redo: ${redoStack.length}`+
 (data&&data.snapshot.revision!==savedRevision?' · Changes not downloaded':'');
 for(const button of $('relationships').querySelectorAll('button'))button.disabled=busy;
 const selected=data?.snapshot.case.edges.find(e=>e.id===$('edge').value);
 const part=data?.snapshot.case.surface_parts?.find(p=>p.edge_ids.includes(selected?.id));
 const shapeOption=data?.shape_edit_options?.[selected?.id];
 const shapeEligible=shapeOption?.eligible===true;
 $('shape').disabled=busy||!shapeEligible;
 $('shapeEligibility').textContent=shapeEligible?`함께 변경할 구간 ${shapeOption.affected_edge_ids.length}개: ${shapeOption.affected_edge_ids.join(', ')}. 연결점과 구간 라벨은 유지됩니다. 상세 형상 검사는 실행 시 수행합니다.`:(shapeOption?.reason||'혈관을 선택해 편집 가능 여부를 확인하세요.');
 for(const id of ['shapeBend','shapeDirection','shapeTwist','shapeCollar','shapeTransition','shapeBound'])$(id).disabled=busy||!shapeEligible;
 $('smooth').disabled=busy||!selected||!selected.centerline_mm||selected.centerline_mm.length<5||selected.start===selected.end;
 $('containment').disabled=busy||!selected||!selected.centerline_mm;
 $('sigma').disabled=busy;$('bound').disabled=busy;}
function relationships(){
 const container=$('relationships');container.replaceChildren();
 const source=data?.snapshot.case,edge=source?.edges.find(e=>e.id===$('edge').value);
 if(!edge)return;
 for(const [end,title] of [['start','First endpoint'],['end','Last endpoint']]){
  const nodeId=edge[end],node=source.nodes[nodeId];
  const neighbors=source.edges.filter(e=>e.id!==edge.id&&(e.start===nodeId||e.end===nodeId))
    .sort((a,b)=>a.id.localeCompare(b.id));
  const section=document.createElement('section');section.className='relationship';section.dataset.endpoint=end;
  const heading=document.createElement('h3');heading.textContent=`${title} · ${neighbors.length} neighbors`;section.append(heading);
  const info=document.createElement('p');
  info.textContent=`${nodeId} · ${node.kind} · evidence: ${node.evidence_status}`;section.append(info);
  if(!neighbors.length){const empty=document.createElement('p');
   empty.textContent=node.kind==='anatomical_terminal'?'Declared anatomical terminal.':'No other edge is recorded here; this does not establish an anatomical terminal.';
   section.append(empty);}
  for(const other of neighbors){const button=document.createElement('button');button.dataset.edgeId=other.id;
   button.textContent=`${other.id} · ${other.anatomy.side} · ${other.anatomy.artery} · evidence: ${other.evidence_status}`;
   button.onclick=()=>{if(busy)return;$('search').value='';filter();$('edge').value=other.id;$('refs').value='';selection();preview.focus();};
   section.append(button);}
  container.append(section);
 }
}
function selection(){const row=data?.edges.find(e=>e.id===$('edge').value);
 $('containmentResult').textContent='NOT RUN · Check this edge at the current case revision.';
 $('selection').textContent=row?`${row.id} · ${row.anatomy.side} · ${row.anatomy.artery} · current mask ID ${row.label_id}`:'No matching edges.';
 $('label').value=row&&data.labels.some(l=>l.id===row.label_id)?String(row.label_id):'';
 preview.select(row?.id||'');
 relationships();
 controls();}
function filter(){const selected=$('edge').value,words=$('search').value.toLowerCase().split(/\s+/).filter(Boolean);
 $('edge').replaceChildren();
 for(const row of data?.edges||[]){const text=`${row.id} · ${row.anatomy.side} · ${row.anatomy.artery} · ${row.anatomy.segment}`;
 if(words.every(w=>text.toLowerCase().includes(w))){const option=new Option(text,row.id);$('edge').add(option);}}
 if([...$('edge').options].some(o=>o.value===selected))$('edge').value=selected;
 else if($('edge').options.length)$('edge').selectedIndex=0;
 selection();}
async function request(action,snapshot,assignments){const r=await fetch('/api/case-labels',{method:'POST',
 headers:{'Content-Type':'application/json'},body:JSON.stringify(['smooth','containment','shape'].includes(action)?{action,snapshot,parameters:assignments}:{action,snapshot,assignments})});
 const value=await r.json();if(!r.ok)throw Error(value.error||'Request failed');return value;}
$('file').onchange=async()=>{const file=$('file').files[0];if(!file)return;
 busy=true;controls();
 try{if(file.size>16*1024*1024)throw Error('Snapshot exceeds 16 MB.');
 const text=await file.text();JSON.parse(text);
 const next=await request('inspect',text,[]);
 if(data&&data.snapshot.revision!==savedRevision&&!confirm(window.VVLanguage?.translate('Replace this case? Current changes have not been downloaded.')||'Replace this case? Current changes have not been downloaded.')){
 $('status').textContent='Current case and edit history kept.';return;}
 data=next;edited=false;undoStack=[];redoStack=[];savedRevision=data.snapshot.revision;
 preview.setCase(data.snapshot.case);
 $('label').replaceChildren(new Option('Choose a label…',''),...data.labels.map(l=>new Option(`${l.id} · ${l.side} · ${l.artery}`,l.id)));
 $('search').value='';$('refs').value='';filter();$('status').textContent=`Loaded ${data.edges.length} edges. Anatomical acceptance: UNKNOWN.`;
 }catch(e){$('status').textContent=e.message+(data?' Current case and edit history kept.':'')}finally{busy=false;controls();}};
$('search').oninput=filter;$('label').onchange=controls;$('edge').onchange=()=>{$('refs').value='';selection();};
$('apply').onclick=async()=>{if(busy||!data||!$('edge').value)return;
 const refs=$('refs').value.split('\n').map(x=>x.trim()).filter(Boolean);
 if(!refs.length){$('status').textContent='Enter at least one full-edge evidence reference.';return;}
 busy=true;controls();try{const next=await request('apply',data.snapshot_json,[{edge_id:$('edge').value,
 label_id:Number($('label').value),evidence_refs:refs}]);
 if(next.snapshot.revision!==data.snapshot.revision){undoStack.push(data);if(undoStack.length>20)undoStack.shift();redoStack=[];}
 data=next;edited=true;filter();
 $('status').textContent='Label applied to the copy. Download to keep it. Anatomical acceptance remains UNKNOWN.';
 }catch(e){$('status').textContent=e.message}finally{busy=false;controls();}};
$('smooth').onclick=async()=>{if(busy||!data)return;
 busy=true;controls();try{const next=await request('smooth',data.snapshot_json,{
 edge_id:$('edge').value,sigma_mm:Number($('sigma').value),max_displacement_mm:Number($('bound').value)});
 undoStack.push(data);if(undoStack.length>20)undoStack.shift();redoStack=[];data=next;edited=true;
 preview.setCase(data.snapshot.case);filter();preview.focus();
 const metric=data.snapshot.case.centerline_regularization.metrics[0];
 $('status').textContent=`Synthetic copy created. Maximum displacement ${metric.max_displacement_mm.toFixed(4)} mm. Surface collision checks: NOT RUN; anatomical acceptance: UNKNOWN.`;
 }catch(e){$('status').textContent=e.message+' Current case kept.';}finally{busy=false;controls();}};
$('containment').onclick=async()=>{if(busy||!data||!$('edge').value)return;
 const revision=data.snapshot.revision,edgeId=$('edge').value;
 busy=true;controls();$('containmentResult').textContent='Checking original surface…';
 try{const result=(await request('containment',data.snapshot_json,{edge_id:edgeId})).inspection;
 if(result.case_revision!==revision||result.edge_id!==edgeId)throw Error('Inspection identity mismatch');
 $('containmentResult').textContent=`${result.status} · ${edgeId} · ${result.reason}`+
 (result.containment?`\nIntervals: ${result.containment.segment_count} · Unresolved: ${result.containment.unresolved_segments.length} · Outside witnesses: ${result.containment.outside_witnesses.length}`:'')+
 '\nOriginal-surface comparison only. Surface self-intersection, radius accuracy and anatomy: NOT RUN.';
 }catch(e){$('containmentResult').textContent='UNKNOWN · '+e.message;}
 finally{busy=false;controls();}};
$('shape').onclick=async()=>{if(busy||!data)return;
 const parameters={edge_id:$('edge').value,bend_mm:Number($('shapeBend').value),
  bend_direction:$('shapeDirection').value.split(',').map(Number),twist_deg:Number($('shapeTwist').value),
  collar_mm:Number($('shapeCollar').value),transition_mm:Number($('shapeTransition').value),
  max_displacement_mm:Number($('shapeBound').value)};
 busy=true;controls();$('status').textContent='벽·중심선 변경과 연결 경로 검사 중… 현재 사례는 결과가 확인될 때까지 유지됩니다.';
 try{const next=await request('shape',data.snapshot_json,parameters);
  undoStack.push(data);if(undoStack.length>20)undoStack.shift();redoStack=[];data=next;edited=true;
  preview.setCase(data.snapshot.case);filter();preview.focus();
  const r=data.snapshot.case.inspection.registered_shape_edit;
  $('status').textContent=`벽·중심선 후보 생성. 최대 이동 ${r.audit.maximum_displacement_mm.toFixed(4)} mm · 연결 경로 ${r.checked_paths.length}개 내강 포함 PASS. 주변 검사 NOT RUN · 생성 미승인.`;
 }catch(e){$('status').textContent=e.message+' 현재 사례와 편집 이력을 유지했습니다.';}
 finally{busy=false;controls();}};
$('shapeContext').onclick=async()=>{if(busy||!data)return;
 busy=true;controls();$('status').textContent='사례와 연결된 기존 주변 검사 기록 대조 중…';
 try{const next=await request('context',data.snapshot_json,[]);
  undoStack.push(data);if(undoStack.length>20)undoStack.shift();redoStack=[];data=next;edited=true;filter();
  const r=data.snapshot.case.inspection.registered_shape_edit;
  $('status').textContent=`주변 검사 ${r.neighboring_vessels} · ${r.context.rows.length}개 이웃. 동일 형상에 연결된 기존 측정이며 새 검사 실행은 아닙니다. 생성 미승인.`;
 }catch(e){$('status').textContent=e.message+' 현재 사례를 유지했습니다. 미등록 형상은 별도 주변 검사가 필요합니다.';}
 finally{busy=false;controls();}};
$('shapeContextRun').onclick=async()=>{if(busy||!data)return;
 const revision=data.snapshot.revision,snapshot=data.snapshot_json,key='vv-context-job';
 busy=true;controls();
 const read=async(url,options)=>{const response=await fetch(url,options);const value=await response.json();
  if(!response.ok){if(response.status===404)sessionStorage.removeItem(key);throw Error(value.error||'검사 요청 실패');}return value;};
 try{
  let saved=null;try{saved=JSON.parse(sessionStorage.getItem(key));}catch(e){sessionStorage.removeItem(key);}
  let job;
  if(saved?.revision===revision)job=await read('/api/case-context-jobs/'+saved.id);
  else{job=await read('/api/case-context-jobs',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({snapshot})});
   sessionStorage.setItem(key,JSON.stringify({id:job.id,revision}));}
  while(true){
   if(job.case_revision!==revision){sessionStorage.removeItem(key);throw Error('검사 대상 사례가 달라졌습니다.');}
   if(data?.snapshot.revision!==revision)throw Error('검사 대상 사례가 달라졌습니다.');
   if(job.state==='COMPLETE')break;
   if(job.state!=='RUNNING'){sessionStorage.removeItem(key);throw Error(job.error||'검사가 중단되었습니다. 자동 재실행하지 않습니다.');}
   $('contextProgress').textContent=job.total===null?'주변 형상과 검사 입력 확인 중…':`주변 검사 ${job.completed}/${job.total}개 완료 · 실행 중`;
   await new Promise(resolve=>setTimeout(resolve,1500));
   job=await read('/api/case-context-jobs/'+job.id);
  }
  const response=await fetch('/api/case-context-jobs/'+job.id+'/result');
  if(!response.ok)throw Error('완료 결과를 불러오지 못했습니다. 다시 이어 보기를 누르세요.');
  const text=await response.text(),document=JSON.parse(text);
  if(document.case.inspection.registered_shape_edit.context.case_revision!==revision)throw Error('검사 결과의 사례가 일치하지 않습니다.');
  const next=await request('inspect',text,[]);
  if(data?.snapshot.revision!==revision)throw Error('사례가 변경되어 결과를 적용하지 않았습니다.');
  undoStack.push(data);if(undoStack.length>20)undoStack.shift();redoStack=[];data=next;edited=true;filter();
  sessionStorage.removeItem(key);
  const report=data.snapshot.case.inspection.registered_shape_edit.context;
  $('contextProgress').textContent=`검사 완료: ${report.status} · ${report.completed}/${report.neighbor_count}개. 결과를 사례에 포함했습니다. 생성 미승인.`;
 }catch(e){$('contextProgress').textContent=e.message+' 현재 사례는 유지됩니다. 같은 사례에서 이어 보기를 다시 누를 수 있습니다.';}
 finally{busy=false;controls();}};
function travel(from,to,name){if(busy||!from.length)return;to.push(data);data=from.pop();
 preview.setCase(data.snapshot.case);$('refs').value='';filter();preview.focus();
 $('status').textContent=`${name} restored the previous case revision. Download to keep this version.`;}
$('undo').onclick=()=>travel(undoStack,redoStack,'Undo');
$('redo').onclick=()=>travel(redoStack,undoStack,'Redo');
$('download').onclick=()=>{if(!data)return;const url=URL.createObjectURL(new Blob(
 [data.snapshot_json],{type:'application/json'}));const a=document.createElement('a');
 a.href=url;a.download='vv-edited-case.snapshot.json';a.click();savedRevision=data.snapshot.revision;controls();setTimeout(()=>URL.revokeObjectURL(url),1000);};
window.addEventListener('beforeunload',e=>{if(busy||(data&&data.snapshot.revision!==savedRevision)){e.preventDefault();e.returnValue='';}});
</script></main></html>'''
