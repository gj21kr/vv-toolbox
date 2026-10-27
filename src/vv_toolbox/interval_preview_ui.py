"""Read-only interval controls and orthographic candidate comparison."""
SCRIPT = r'''
(()=>{
 const panel=document.createElement('details');panel.id='intervalPreviewPanel';
 panel.innerHTML=`<summary>구간 크기 미리보기</summary>
 <p id="intervalAvailability" role="status"></p>
 <p class="tip">첫 내부 단면부터의 거리(mm)입니다. 후보를 검사한 뒤 현재 장면에 적용할 수 있습니다. 원본 파일은 유지됩니다.</p>
 <form id="intervalForm"><fieldset id="intervalFields">
 <label for="intervalStart">시작 거리 (mm)</label><input id="intervalStart" type="number" min="0" step="any" required>
 <label for="intervalEnd">끝 거리 (mm)</label><input id="intervalEnd" type="number" min="0" step="any" required>
 <label for="intervalFactor">중앙 크기 배율</label><input id="intervalFactor" type="number" min="0.000001" step="any" placeholder="예: 0.9" required>
 <label for="intervalMovement">최대 정점 이동 (mm)</label><input id="intervalMovement" type="number" min="0.000000000001" step="any" required>
 <label for="intervalTolerance">단면 배율 허용오차</label><input id="intervalTolerance" type="number" min="0" step="any" required>
 <p class="tip">배율과 검사 조건은 사용자가 지정합니다. 부위별 질환 프리셋이 아닙니다.</p>
 <button class="primary" type="submit">검사하고 미리보기</button></fieldset></form>
 <p id="intervalMessage" role="status"></p>
 <button id="intervalUndo" type="button">마지막 구간 편집 되돌리기</button>
 <button id="intervalSessionDownload" type="button">구간 편집 세션 다운로드</button>
 <label for="intervalSessionFile">구간 편집 세션 불러오기</label><input id="intervalSessionFile" type="file" accept=".json,application/json">
 <p class="tip">세션 파일은 여러 구간 편집을 순서대로 저장합니다. 현재 구간 편집을 모두 되돌린 후 같은 기준 혈관 파라미터에서 불러오세요. 전체 사례 생성은 아직 연결되지 않았습니다.</p>
 <label for="intervalFile">저장된 후보 다시 열기</label><input id="intervalFile" type="file" accept=".json,application/json">
 <div id="intervalResult" hidden><div class="row"><button id="intervalCompare" type="button">원본 보기</button><button id="intervalDownload" type="button">후보 다운로드</button><button id="intervalRevalidate" type="button">현재 장면 재검사</button><button id="intervalApply" type="button">재검사 후 장면에 적용</button></div>
 <canvas id="intervalCanvas" width="520" height="360" tabindex="0" aria-label="혈관 구간 후보 3D 미리보기. 드래그 또는 방향키로 회전"></canvas>
 <p class="tip">드래그 또는 방향키로 회전 · 주변 혈관은 이 작은 미리보기에 표시하지 않습니다. 전체 충돌·해부학적 승인은 별도입니다.</p></div>`;
 $('atlasModificationPanel').append(panel);
 for(const input of panel.querySelectorAll('input'))input.style.cssText='width:100%;box-sizing:border-box;padding:8px;background:#20323b;color:#ecf6f6;border:1px solid #607984;border-radius:6px';
 const canvas=$('intervalCanvas');canvas.style.cssText='width:100%;height:auto;background:#101820;touch-action:none;border:1px solid #425960;box-sizing:border-box';
 let key='',edge=null,working=false,result=null,snapshotText=null,reference=false,yaw=.2,pitch=.1,drag=null;
 function identity(){return `${state?.source}/${state?.generation}/${state?.atlas_selection}`}
 function clear(){result=null;snapshotText=null;$('intervalResult').hidden=true;$('intervalMessage').textContent=''}
 function update(){
   const current=identity();
   if(current!==key){key=current;clear();edge=null;
     const edges=(atlasCenterlineData?.edges||[]).filter(e=>e.part_id===state?.atlas_selection);
     if(atlasCenterlineGeneration===state?.generation&&edges.length===1&&edges[0].points.length>=5)edge=edges[0];
     if(edge){const pts=edge.points.slice(1,-1);let length=0;for(let i=1;i<pts.length;i++)length+=Math.hypot(...pts[i].map((v,k)=>v-pts[i-1][k]));
       $('intervalStart').value=(length*.25).toFixed(4);$('intervalEnd').value=(length*.75).toFixed(4);
       $('intervalAvailability').textContent=`${edge.id} · 내부 구간 ${length.toFixed(2)} mm`;
     }else $('intervalAvailability').textContent='단일 중심선 구간을 가진 혈관을 선택하세요. 다중 분기 편집은 아직 지원하지 않습니다.';
   }
   if(!edge&&atlasCenterlineGeneration===state?.generation&&atlasCenterlineData) {
     const edges=atlasCenterlineData.edges.filter(e=>e.part_id===state?.atlas_selection);
     if(edges.length===1&&edges[0].points.length>=5){key='';update();return}
   }
   $('intervalFields').disabled=working||pending||!edge||!isAtlas();
   $('intervalFile').disabled=working||pending||!isAtlas();
   $('intervalDownload').disabled=working||!result;
   $('intervalRevalidate').disabled=working||pending||!result||!isAtlas();
   $('intervalApply').disabled=working||pending||!result||!isAtlas();
   $('intervalUndo').disabled=working||pending||!state?.atlas_interval_undo_available||!isAtlas();
   $('intervalSessionDownload').disabled=working||pending||!Object.keys(state?.atlas_interval_edits||{}).length||!isAtlas();
   $('intervalSessionFile').disabled=working||pending||!!Object.keys(state?.atlas_interval_edits||{}).length||!isAtlas();
 }
 function draw(){
   if(!result)return;
   const vertices=reference?result.reference_vertices:result.vertices,faces=result.faces;
   const low=[Infinity,Infinity,Infinity],high=[-Infinity,-Infinity,-Infinity];
   for(const points of [result.reference_vertices,result.vertices])for(const p of points)for(let k=0;k<3;k++){low[k]=Math.min(low[k],p[k]);high[k]=Math.max(high[k],p[k])}
   const center=low.map((v,k)=>(v+high[k])/2),span=Math.hypot(...high.map((v,k)=>v-low[k]))||1;
   const projected=vertices.map(p=>{const [x,y,z]=p.map((v,k)=>v-center[k]);const a=x*Math.cos(yaw)+y*Math.sin(yaw),b=-x*Math.sin(yaw)+y*Math.cos(yaw);
     return [canvas.width/2+a*300/span,canvas.height/2-(z*Math.cos(pitch)-b*Math.sin(pitch))*300/span,b*Math.cos(pitch)+z*Math.sin(pitch)]});
   const ctx=canvas.getContext('2d');ctx.clearRect(0,0,canvas.width,canvas.height);
   const ordered=faces.map(f=>({f,depth:f.reduce((s,i)=>s+projected[i][2],0)/3})).sort((a,b)=>b.depth-a.depth);
   for(const {f,depth} of ordered){ctx.fillStyle=`hsl(${result.layer==='arterial'?355:215} 65% ${45+15*depth/span}%)`;ctx.beginPath();f.forEach((i,k)=>{const p=projected[i];k?ctx.lineTo(p[0],p[1]):ctx.moveTo(p[0],p[1])});ctx.closePath();ctx.fill()}
   ctx.fillStyle='#eaf4f7';ctx.font='16px sans-serif';ctx.fillText(reference?'원본':'구간 편집 후보',12,24);
 }
 $('intervalCompare').onclick=()=>{reference=!reference;$('intervalCompare').textContent=reference?'후보 보기':'원본 보기';draw()};
 async function snapshotRequest(body){
   const response=await fetch('/api/interval-snapshot',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
   const data=await response.json();if(!response.ok)throw Error(data.error||'파일 검사 실패');return data;
 }
 $('intervalDownload').onclick=async()=>{
   if(!result||working)return;
   const selectedResult=result,requestKey=identity();working=true;update();
   try{
     const text=snapshotText||(await snapshotRequest({action:'export',candidate:selectedResult})).snapshot_text;
     if(requestKey!==identity()||selectedResult!==result)throw Error('장면이 바뀌어 다운로드를 중단했습니다.');
     snapshotText=text;const url=URL.createObjectURL(new Blob([text],{type:'application/json'})),a=document.createElement('a');
     a.href=url;a.download='vv-interval-candidate.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
     $('intervalMessage').textContent='후보 파일 다운로드 · 원본 Atlas 저장본은 변경하지 않았습니다.';
   }catch(error){$('intervalMessage').textContent='다운로드 중단: '+error.message}
   finally{working=false;update()}
 };
 $('intervalFile').onchange=async()=>{
   const file=$('intervalFile').files[0];if(!file||working)return;
   const requestKey=identity();working=true;update();
   try{
     if(file.size>15*1024*1024)throw Error('후보 파일은 15 MB 이하여야 합니다.');
     const data=await snapshotRequest({action:'import',snapshot_text:await file.text()});
     if(requestKey!==identity())throw Error('선택 또는 장면이 바뀌어 파일 열기를 중단했습니다.');
     if(data.candidate.part_id!==state?.atlas_selection)throw Error(`먼저 ${data.candidate.part_id} 혈관을 선택하세요.`);
     result=data.candidate;snapshotText=data.snapshot_text;reference=false;
     $('intervalCompare').textContent='원본 보기';$('intervalResult').hidden=false;
     $('intervalMessage').textContent='저장 후보 열림 · 파일 무결성 확인 · 형상 재검증 및 현재 장면 적용 안 함';draw();
   }catch(error){$('intervalMessage').textContent='파일 열기 중단: '+error.message}
   finally{working=false;$('intervalFile').value='';update()}
 };
 $('intervalRevalidate').onclick=async()=>{
   if(!result||working||pending)return;
   const selectedResult=result,requestKey=identity(),generation=state.generation;
   working=true;update();$('intervalMessage').textContent='현재 장면에서 재생성·재검사 중…';
   try{
     const text=snapshotText||(await snapshotRequest({action:'export',candidate:selectedResult})).snapshot_text;
     const response=await fetch('/api/atlas-interval-revalidate',{method:'POST',
       headers:{'Content-Type':'application/json','X-Expected-Generation':String(generation)},
       body:JSON.stringify({snapshot_text:text})}),data=await response.json();
     if(!response.ok)throw Error(data.error||'재검사 실패');
     if(requestKey!==identity()||data.generation!==generation)throw Error('장면이 바뀌어 결과를 폐기했습니다.');
     result=data;snapshotText=null;reference=false;$('intervalCompare').textContent='원본 보기';
     $('intervalMessage').textContent='현재 장면 재생성·검사 완료 · 저장 형상 일치 · 전체 해부학적 승인 및 적용 아님';draw();
   }catch(error){$('intervalMessage').textContent='재검사 중단: '+error.message}
   finally{working=false;update()}
 };
 async function sessionRequest(body,generation){
   const response=await fetch('/api/atlas-interval-session',{method:'POST',headers:{
     'Content-Type':'application/json','X-Expected-Generation':String(generation)},body:JSON.stringify(body)});
   const data=await response.json();if(!response.ok)throw Error(data.error||'세션 처리 실패');return data;
 }
 $('intervalSessionDownload').onclick=async()=>{
   if(working||pending)return;
   const generation=state.generation;working=true;update();
   try{
     const data=await sessionRequest({action:'export'},generation);
     const url=URL.createObjectURL(new Blob([data.session_text],{type:'application/json'})),a=document.createElement('a');
     a.href=url;a.download='vv-interval-session.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
     $('intervalMessage').textContent='구간 편집 세션 다운로드 완료 · 원본 파일 유지';
   }catch(error){$('intervalMessage').textContent='세션 저장 중단: '+error.message}
   finally{working=false;update()}
 };
 $('intervalSessionFile').onchange=async()=>{
   const file=$('intervalSessionFile').files[0];if(!file||working||pending)return;
   const generation=state.generation;working=true;update();
   $('intervalMessage').textContent='세션의 모든 편집을 재생성·검사 중…';
   try{
     if(file.size>15*1024*1024)throw Error('세션 파일은 15 MB 이하여야 합니다.');
     const data=await sessionRequest({action:'restore',session_text:await file.text()},generation);
     await poll();update();
     $('intervalMessage').textContent=`구간 편집 ${data.operations}개 복원 완료 · 원본 파일 유지`;
   }catch(error){$('intervalMessage').textContent='세션 복원 중단: '+error.message}
   finally{working=false;$('intervalSessionFile').value='';update()}
 };
 async function editInterval(action){
   if(working||pending)return;
   const generation=state.generation,selectedResult=result;
   working=true;update();$('intervalMessage').textContent=action==='apply'?'재검사 후 장면 적용 중…':'구간 편집 되돌리는 중…';
   try{
     const body=action==='apply'?{snapshot_text:snapshotText||(await snapshotRequest({action:'export',candidate:selectedResult})).snapshot_text}:{};
     const response=await fetch('/api/atlas-interval-'+action,{method:'POST',headers:{
       'Content-Type':'application/json','X-Expected-Generation':String(generation)},body:JSON.stringify(body)});
     const data=await response.json();if(!response.ok)throw Error(data.error||'구간 편집 실패');
     await poll();update();
     $('intervalMessage').textContent=action==='apply'?'현재 장면 적용 완료 · 원본 파일 유지 · 세션 내 편집':'마지막 구간 편집을 되돌렸습니다.';
   }catch(error){$('intervalMessage').textContent='구간 편집 중단: '+error.message}
   finally{working=false;update()}
 }
 $('intervalApply').onclick=()=>editInterval('apply');
 $('intervalUndo').onclick=()=>editInterval('undo');
 canvas.onpointerdown=e=>{drag=[e.clientX,e.clientY];canvas.setPointerCapture(e.pointerId)};
 canvas.onpointermove=e=>{if(!drag)return;yaw+=(e.clientX-drag[0])*.01;pitch+=(e.clientY-drag[1])*.01;drag=[e.clientX,e.clientY];draw()};
 canvas.onpointerup=()=>drag=null;canvas.onpointercancel=()=>drag=null;
 canvas.onkeydown=e=>{if(!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(e.key))return;e.preventDefault();yaw+=(e.key==='ArrowRight'?.1:e.key==='ArrowLeft'?-.1:0);pitch+=(e.key==='ArrowDown'?.1:e.key==='ArrowUp'?-.1:0);draw()};
 $('intervalForm').onsubmit=async event=>{
   event.preventDefault();if(working||pending||!edge)return;
   const start=+$('intervalStart').value,end=+$('intervalEnd').value;
   if(end<=start){$('intervalMessage').textContent='끝 거리는 시작 거리보다 커야 합니다.';return}
   const requestKey=identity(),generation=state.generation,partId=state.atlas_selection;
   const body={part_id:partId,edge_id:edge.id,start_mm:start,end_mm:end,factor:+$('intervalFactor').value,
     max_displacement_mm:+$('intervalMovement').value,absolute_scale_tolerance:+$('intervalTolerance').value};
   clear();working=true;update();$('intervalMessage').textContent='후보 생성과 주변 혈관 검사 중…';
   try{
     const response=await fetch('/api/atlas-interval-preview',{method:'POST',headers:{'Content-Type':'application/json','X-Expected-Generation':String(generation)},body:JSON.stringify(body)}),data=await response.json();
     if(requestKey!==identity())throw Error('선택 또는 장면이 바뀌어 결과를 폐기했습니다.');
     if(!response.ok)throw Error(data.error||'후보 검사 실패');
     if(data.generation!==generation||data.part_id!==partId||data.applied!==false)throw Error('후보와 현재 장면이 일치하지 않습니다.');
     result=data;reference=false;$('intervalCompare').textContent='원본 보기';$('intervalResult').hidden=false;
     $('intervalMessage').textContent='후보 생성 완료 · 원본 유지 · 전체 충돌 승인 아님';draw();
   }catch(error){$('intervalMessage').textContent='미리보기 중단: '+error.message}
   finally{working=false;update()}
 };
 setInterval(update,700);update();
})();
'''
