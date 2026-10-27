"""Local WebGL rendering of registered triangles; no surface reconstruction."""

JS = r'''
class VVRegisteredSurface {
 constructor(parts){
  this.canvas=document.createElement('canvas');
  const gl=this.gl=this.canvas.getContext('webgl',{alpha:true,antialias:true,preserveDrawingBuffer:true});
  if(!gl)throw Error('WebGL unavailable');
  const shader=(kind,source)=>{const s=gl.createShader(kind);gl.shaderSource(s,source);gl.compileShader(s);
   if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw Error(gl.getShaderInfoLog(s));return s;};
  const v=shader(gl.VERTEX_SHADER,`
   attribute vec3 position; attribute vec3 normal;
   uniform vec3 center; uniform vec2 angles; uniform vec3 scale;
   varying float light;
   vec3 rotate(vec3 p){float cy=cos(angles.x),sy=sin(angles.x),cp=cos(angles.y),sp=sin(angles.y);
    float a=p.x*cy+p.z*sy,b=-p.x*sy+p.z*cy;
    return vec3(a,p.y*cp-b*sp,p.y*sp+b*cp);}
   void main(){vec3 p=rotate(position-center);gl_Position=vec4(p*scale,1.0);
    light=.3+.7*abs(dot(normalize(rotate(normal)),normalize(vec3(.3,.5,1.))));}`);
  const f=shader(gl.FRAGMENT_SHADER,`precision mediump float; varying float light;
   void main(){gl_FragColor=vec4(vec3(.86,.20,.27)*light,1.0);}`);
  const program=this.program=gl.createProgram();gl.attachShader(program,v);gl.attachShader(program,f);gl.linkProgram(program);
  gl.deleteShader(v);gl.deleteShader(f);
  if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw Error(gl.getProgramInfoLog(program));
  const count=parts.reduce((n,p)=>n+p.faces.length,0),data=new Float32Array(count*18);
  let k=0;
  for(const part of parts)for(const face of part.faces){
   const [a,b,c]=face.map(i=>part.vertices_mm[i]);
   const u=b.map((x,i)=>x-a[i]),w=c.map((x,i)=>x-a[i]);
   const n=[u[1]*w[2]-u[2]*w[1],u[2]*w[0]-u[0]*w[2],u[0]*w[1]-u[1]*w[0]];
   const length=Math.hypot(...n)||1;
   for(const p of [a,b,c]){data.set(p,k);data.set(n.map(x=>x/length),k+3);k+=6;}
  }
  this.count=count*3;this.buffer=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,this.buffer);
  gl.bufferData(gl.ARRAY_BUFFER,data,gl.STATIC_DRAW);
 }
 draw(view){
  const gl=this.gl,program=this.program;
  this.canvas.width=view.canvas.width;this.canvas.height=view.canvas.height;
  gl.viewport(0,0,this.canvas.width,this.canvas.height);gl.useProgram(program);
  gl.bindBuffer(gl.ARRAY_BUFFER,this.buffer);
  for(const [name,offset] of [['position',0],['normal',12]]){const loc=gl.getAttribLocation(program,name);
   gl.enableVertexAttribArray(loc);gl.vertexAttribPointer(loc,3,gl.FLOAT,false,24,offset);}
  gl.uniform3fv(gl.getUniformLocation(program,'center'),view.center);
  gl.uniform2f(gl.getUniformLocation(program,'angles'),view.yaw,view.pitch);
  const s=.8*Math.min(view.width,view.height)/view.extent*view.zoom;
  gl.uniform3f(gl.getUniformLocation(program,'scale'),2*s/view.width,2*s/view.height,1/Math.max(view.homeExtent,view.extent,1));
  gl.enable(gl.DEPTH_TEST);gl.clearColor(0,0,0,0);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);
  gl.drawArrays(gl.TRIANGLES,0,this.count);
  if(gl.isContextLost())throw Error('WebGL context lost');
  view.ctx.drawImage(this.canvas,0,0,view.width,view.height);
 }
 dispose(){this.gl.deleteBuffer(this.buffer);this.gl.deleteProgram(this.program);
  this.gl.getExtension('WEBGL_lose_context')?.loseContext();}
}
'''
