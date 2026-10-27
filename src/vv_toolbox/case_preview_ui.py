"""Dependency-free orthographic centerline viewer; display coordinates only."""

JS = r'''
class VVCasePreview {
 constructor(canvas,onSelect){
  this.canvas=canvas;this.ctx=canvas.getContext('2d');this.onSelect=onSelect;
  this.edges=[];this.selected='';this.center=[0,0,0];this.extent=1;
  this.yaw=0;this.pitch=0;this.zoom=1;this.segments=[];
  this.showSurface=true;this.showCenterlines=true;this.surface=null;this.surfaceError='';
  new ResizeObserver(()=>this.draw()).observe(canvas);
  canvas.addEventListener('pointerdown',e=>{
   canvas.setPointerCapture(e.pointerId);this.drag={x:e.clientX,y:e.clientY,moved:0};
  });
  canvas.addEventListener('pointermove',e=>{
   if(!this.drag)return;
   const dx=e.clientX-this.drag.x,dy=e.clientY-this.drag.y;
   this.drag.moved+=Math.hypot(dx,dy);this.drag.x=e.clientX;this.drag.y=e.clientY;
   this.yaw+=dx*.008;this.pitch+=dy*.008;this.draw();
  });
  canvas.addEventListener('pointerup',e=>{
   if(!this.drag)return;
   if(this.drag.moved<4){const r=canvas.getBoundingClientRect();
    const id=this.pick(e.clientX-r.left,e.clientY-r.top);if(id!==null)this.onSelect(id);}
   this.drag=null;
  });
  canvas.addEventListener('pointercancel',()=>{this.drag=null});
  canvas.addEventListener('wheel',e=>{
   e.preventDefault();this.zoom=Math.min(20,Math.max(.1,this.zoom*Math.exp(-e.deltaY*.001)));this.draw();
  },{passive:false});
  canvas.addEventListener('keydown',e=>{
   if(['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(e.key)){
    e.preventDefault();this.yaw+=(e.key==='ArrowRight'?.1:e.key==='ArrowLeft'?-.1:0);
    this.pitch+=(e.key==='ArrowDown'?.1:e.key==='ArrowUp'?-.1:0);this.draw();
   }
  });
 }
 setCase(value){
  this.surface?.dispose();this.surface=null;this.surfaceError='';
  const parts=value.surface_parts||[];
  this.surfaceTriangles=parts.reduce((n,p)=>n+p.faces.length,0);
  if(this.surfaceTriangles){try{this.surface=new VVRegisteredSurface(parts);}catch(e){this.surfaceError=String(e.message);}}
  this.edges=value.edges.filter(e=>e.centerline_mm&&e.centerline_mm.length>1);
  const lo=[Infinity,Infinity,Infinity],hi=[-Infinity,-Infinity,-Infinity];
  for(const edge of this.edges)for(const p of edge.centerline_mm)
   for(let i=0;i<3;i++){lo[i]=Math.min(lo[i],p[i]);hi[i]=Math.max(hi[i],p[i]);}
  for(const part of parts)for(const p of part.vertices_mm)
   for(let i=0;i<3;i++){lo[i]=Math.min(lo[i],p[i]);hi[i]=Math.max(hi[i],p[i]);}
  this.center=Number.isFinite(lo[0])?lo.map((v,i)=>(v+hi[i])/2):[0,0,0];
  this.extent=Number.isFinite(lo[0])?Math.max(1,Math.hypot(...lo.map((v,i)=>hi[i]-v))):1;
  this.homeCenter=[...this.center];this.homeExtent=this.extent;
  this.frame=`${value.frame.axes} · ${value.frame.units} · ${this.edges.length}/${value.edges.length} edges with centerlines`;
  this.fit();
 }
 fit(){this.center=[...(this.homeCenter||[0,0,0])];this.extent=this.homeExtent||1;
  this.yaw=0;this.pitch=-Math.PI/2;this.zoom=1;this.draw();}
 focus(){
  const edge=this.edges.find(e=>e.id===this.selected);if(!edge)return;
  const lo=[Infinity,Infinity,Infinity],hi=[-Infinity,-Infinity,-Infinity];
  for(const p of edge.centerline_mm)for(let i=0;i<3;i++){lo[i]=Math.min(lo[i],p[i]);hi[i]=Math.max(hi[i],p[i]);}
  this.center=lo.map((v,i)=>(v+hi[i])/2);this.extent=Math.max(1,Math.hypot(...lo.map((v,i)=>hi[i]-v)));
  this.zoom=1;this.draw();
 }
 select(id){this.selected=id;this.draw();}
 project(point){
  const [x,y,z]=point.map((v,i)=>v-this.center[i]);
  const a=x*Math.cos(this.yaw)+z*Math.sin(this.yaw);
  const b=-x*Math.sin(this.yaw)+z*Math.cos(this.yaw);
  const c=y*Math.cos(this.pitch)-b*Math.sin(this.pitch);
  const scale=.8*Math.min(this.width,this.height)/this.extent*this.zoom;
  return [this.width/2+a*scale,this.height/2-c*scale];
 }
 draw(){
  const r=this.canvas.getBoundingClientRect();this.width=r.width;this.height=r.height;
  if(!r.width||!r.height)return;
  const dpr=window.devicePixelRatio||1;this.canvas.width=Math.round(r.width*dpr);
  this.canvas.height=Math.round(r.height*dpr);const ctx=this.ctx;
  ctx.setTransform(dpr,0,0,dpr,0,0);ctx.fillStyle='#0b1217';ctx.fillRect(0,0,r.width,r.height);
  this.segments=[];
  if(this.showSurface&&this.surface){try{this.surface.draw(this);}catch(e){this.surfaceError=String(e.message);}}
  for(const edge of (this.showCenterlines?[...this.edges.filter(e=>e.id!==this.selected),...this.edges.filter(e=>e.id===this.selected)]:[])){
   ctx.strokeStyle=edge.id===this.selected?'#6ce3df':'#db5965';ctx.lineWidth=edge.id===this.selected?4:1.5;
   ctx.beginPath();let previous=null;
   for(const point of edge.centerline_mm){
    const p=this.project(point);if(previous){ctx.lineTo(...p);this.segments.push({id:edge.id,a:previous,b:p});}
    else ctx.moveTo(...p);previous=p;
   }ctx.stroke();
  }
  ctx.fillStyle='#bcced9';ctx.font='13px system-ui';
  ctx.fillText(this.frame||'Load a case to preview centerlines',12,22);
  if(this.surfaceError)ctx.fillText('Surface unavailable: '+this.surfaceError,12,42);
 }
 pick(x,y){
  let chosen=null,best=8;
  for(const s of this.segments){
   const dx=s.b[0]-s.a[0],dy=s.b[1]-s.a[1],length=dx*dx+dy*dy;
   const t=length?Math.max(0,Math.min(1,((x-s.a[0])*dx+(y-s.a[1])*dy)/length)):0;
   const distance=Math.hypot(x-s.a[0]-t*dx,y-s.a[1]-t*dy);
   if(distance<=best){best=distance;chosen=s.id;}
  }return chosen;
 }
}
window.VVCasePreview=VVCasePreview;
'''

from .case_surface_preview_ui import JS as SURFACE_JS
JS = SURFACE_JS + JS
