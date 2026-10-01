import {NodeIO} from '@gltf-transform/core';import {ALL_EXTENSIONS} from '@gltf-transform/extensions';import {MeshoptDecoder,MeshoptEncoder} from 'meshoptimizer';import fs from 'fs';
await MeshoptDecoder.ready;await MeshoptEncoder.ready;
// 用法：npm i @gltf-transform/core @gltf-transform/extensions meshoptimizer
//       node tools/glb_add_gate_doors.mjs models/b/xiaoxiang_ct.wasm models/b/xiaoxiang_ct.wasm
const [,,src,dst,plain]=process.argv;
const io=new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({'meshopt.decoder':MeshoptDecoder,'meshopt.encoder':MeshoptEncoder});
const doc=await io.readBinary(new Uint8Array(fs.readFileSync(src)));const R=doc.getRoot();
if(R.listNodes().some(n=>n.getName().startsWith('门楼_门扇')))throw 'already has doors';
const mat=nm=>R.listMaterials().find(m=>m.getName()===nm);
const WOOD=mat('SAMPLE_旧绿漆木'),BRASS=mat('XS_门环旧铜');if(!WOOD||!BRASS)throw 'material missing';
const buf=R.listBuffers()[0],scene=R.listScenes()[0];
// ---------- tiny geometry kit (positions+normals+indices) ----------
function G(){return {p:[],n:[],i:[]};}
function quad(g,a,b,c,d,n){const o=g.p.length/3;for(const v of[a,b,c,d]){g.p.push(...v);g.n.push(...n);}g.i.push(o,o+1,o+2,o,o+2,o+3);}
function box(g,x0,y0,z0,x1,y1,z1){
 quad(g,[x0,y0,z1],[x1,y0,z1],[x1,y1,z1],[x0,y1,z1],[0,0,1]);quad(g,[x1,y0,z0],[x0,y0,z0],[x0,y1,z0],[x1,y1,z0],[0,0,-1]);
 quad(g,[x1,y0,z1],[x1,y0,z0],[x1,y1,z0],[x1,y1,z1],[1,0,0]);quad(g,[x0,y0,z0],[x0,y0,z1],[x0,y1,z1],[x0,y1,z0],[-1,0,0]);
 quad(g,[x0,y1,z1],[x1,y1,z1],[x1,y1,z0],[x0,y1,z0],[0,1,0]);quad(g,[x0,y0,z0],[x1,y0,z0],[x1,y0,z1],[x0,y0,z1],[0,-1,0]);}
// dome on +z face: centre (cx,cy,cz), radius r, height h
function dome(g,cx,cy,cz,r,h,seg=10,rings=4){const o=g.p.length/3;
 for(let j=0;j<=rings;j++){const t=j/rings*Math.PI/2,rr=Math.cos(t)*r,zz=Math.sin(t)*h;for(let i=0;i<=seg;i++){const a=i/seg*Math.PI*2,x=Math.cos(a),y=Math.sin(a);
  g.p.push(cx+x*rr,cy+y*rr,cz+zz);const nx=x*Math.cos(t)/r,ny=y*Math.cos(t)/r,nz=Math.sin(t)/h,l=Math.hypot(nx,ny,nz);g.n.push(nx/l,ny/l,nz/l);}}
 for(let j=0;j<rings;j++)for(let i=0;i<seg;i++){const a=o+j*(seg+1)+i,b=a+seg+1;g.i.push(a,a+1,b+1,a,b+1,b);}}
// cylinder along z from cz to cz+t
function disc(g,cx,cy,cz,r,t,seg=16){const o=g.p.length/3;
 for(let i=0;i<=seg;i++){const a=i/seg*Math.PI*2,x=Math.cos(a),y=Math.sin(a);g.p.push(cx+x*r,cy+y*r,cz,cx+x*r,cy+y*r,cz+t);g.n.push(x,y,0,x,y,0);}
 for(let i=0;i<seg;i++){const a=o+i*2;g.i.push(a,a+2,a+3,a,a+3,a+1);}
 const c=g.p.length/3;g.p.push(cx,cy,cz+t);g.n.push(0,0,1);const r0=g.p.length/3;
 for(let i=0;i<=seg;i++){const a=i/seg*Math.PI*2;g.p.push(cx+Math.cos(a)*r,cy+Math.sin(a)*r,cz+t);g.n.push(0,0,1);}for(let i=0;i<seg;i++)g.i.push(c,r0+i,r0+i+1);}
// torus in xy plane
function torus(g,cx,cy,cz,R0,r,seg=20,s2=6){const o=g.p.length/3;
 for(let i=0;i<=seg;i++){const a=i/seg*Math.PI*2;for(let j=0;j<=s2;j++){const b=j/s2*Math.PI*2;const nx=Math.cos(a)*Math.cos(b),ny=Math.sin(a)*Math.cos(b),nz=Math.sin(b);
  g.p.push(cx+Math.cos(a)*R0+nx*r,cy+Math.sin(a)*R0+ny*r,cz+nz*r);g.n.push(nx,ny,nz);}}
 for(let i=0;i<seg;i++)for(let j=0;j<s2;j++){const a=o+i*(s2+1)+j,b=a+s2+1;g.i.push(a,b,b+1,a,b+1,a+1);}}
function mesh(name,g,m){const pos=doc.createAccessor().setType('VEC3').setArray(new Float32Array(g.p)).setBuffer(buf);
 const nor=doc.createAccessor().setType('VEC3').setArray(new Float32Array(g.n)).setBuffer(buf);
 const idx=doc.createAccessor().setType('SCALAR').setArray(new Uint16Array(g.i)).setBuffer(buf);
 return doc.createMesh(name).addPrimitive(doc.createPrimitive().setAttribute('POSITION',pos).setAttribute('NORMAL',nor).setIndices(idx).setMaterial(m));}
// ---------- door leaves ----------
// 门洞：走马板下沿 y=2.80，两侧抱框内缘 x=6.45 / 8.55，门扇关闭时位于 z≈15.975。
// 门扇向院内（-z）敞开 90°，贴在门洞两侧；正面（门钉、铺首一面）朝向门洞中线。
const W=1.03,T=0.07,Y0=0.06,Y1=2.78;
for(const side of[-1,1]){                       // -1 左扇（西），+1 右扇（东）
 const s=side<0?1:-1;                            // 局部 x 方向：从门轴指向门缝
 const leaf=G(),stud=G(),pu=G();
 box(leaf,Math.min(0,s*W),Y0,-T/2,Math.max(0,s*W),Y1,T/2);
 // 门钉：5 路 × 7 行
 const cols=5,rows=7;for(let r=0;r<rows;r++)for(let c=0;c<cols;c++){const lx=s*(0.17+c*(W-0.34)/(cols-1)),ly=0.42+r*(Y1-0.42-0.5)/(rows-1);dome(stud,lx,ly,T/2,0.028,0.024);}
 // 铺首：兽面座 + 鼻 + 衔环，靠门缝一侧
 const px=s*(W-0.2),py=1.3;disc(pu,px,py,T/2,0.1,0.016,20);dome(pu,px,py+0.015,T/2+0.016,0.035,0.03);torus(pu,px,py-0.085,T/2+0.03,0.075,0.009);
 const hx=side<0?6.53:8.47,hz=15.93,ry=side<0?Math.PI/2:-Math.PI/2;
 const n=doc.createNode('门楼_门扇_'+(side<0?'左':'右')).setMesh(mesh('门楼_门扇',leaf,WOOD)).setTranslation([hx,0,hz]).setRotation([0,Math.sin(ry/2),0,Math.cos(ry/2)]);
 n.addChild(doc.createNode('门楼_门钉_'+(side<0?'左':'右')).setMesh(mesh('门楼_门钉',stud,BRASS)));
 n.addChild(doc.createNode('门楼_铺首_'+(side<0?'左':'右')).setMesh(mesh('门楼_铺首',pu,BRASS)));
 scene.addChild(n);}
fs.writeFileSync(dst,await io.writeBinary(doc));
if(plain){const io2=new NodeIO().registerExtensions(ALL_EXTENSIONS.filter(e=>e.EXTENSION_NAME!=='EXT_meshopt_compression')).registerDependencies({'meshopt.decoder':MeshoptDecoder});
 const d2=await io.readBinary(new Uint8Array(fs.readFileSync(dst)));d2.getRoot().listExtensionsUsed().filter(e=>e.extensionName==='EXT_meshopt_compression').forEach(e=>e.dispose());fs.writeFileSync(plain,await io.writeBinary(d2));}
console.log('ok',fs.statSync(src).size,'->',fs.statSync(dst).size);
