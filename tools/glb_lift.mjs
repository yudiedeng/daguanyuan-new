// 把网页模型（models/b/<id>.wasm）里落在盒子里的整块构件抬高——用来给屋顶下面让出斗栱层。
// 用法：node tools/glb_lift.mjs in.wasm out.wasm '<json>'
//   json：{"box":[x0,y0,x1,y1],"zmin":5.4,"zmax":5.68,"dz":0.66,"re":"材质正则(可省)"}，Blender 坐标（Z 向上）。
//   判定按连通块（共用顶点的三角形连成一块）：整块平面范围在盒内、最低点 > zmin、最高点 > zmax 即整块上移 dz；
//   另给 "ring":[x0,y0,x1,y1],"zlow":z 时，其余顶点凡在盒内、ring 外、高于 zlow 的也上移（出檐部分，原模型三角形多不焊接）。
//   不可重复执行（每跑一次就再抬一次）；从原始模型出发跑一次。
// 依赖：blender/scripts/web 下 npm i。
import {createRequire} from 'module';
const require=createRequire(new URL('../blender/scripts/web/package.json',import.meta.url));
const {NodeIO}=require('@gltf-transform/core');const {ALL_EXTENSIONS}=require('@gltf-transform/extensions');
const {MeshoptDecoder,MeshoptEncoder}=require('meshoptimizer');const {meshopt}=require('@gltf-transform/functions');const fs=require('fs');
await MeshoptDecoder.ready;await MeshoptEncoder.ready;
const io=new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({'meshopt.decoder':MeshoptDecoder,'meshopt.encoder':MeshoptEncoder});
const [,,src,dst,spec]=process.argv;
const S=JSON.parse(spec);const [X0,Y0,X1,Y1]=S.box;const re=S.re?new RegExp(S.re):null;
const doc=await io.readBinary(new Uint8Array(fs.readFileSync(src)));const R=doc.getRoot();
const mul=(m,v)=>[m[0]*v[0]+m[4]*v[1]+m[8]*v[2]+m[12],m[1]*v[0]+m[5]*v[1]+m[9]*v[2]+m[13],m[2]*v[0]+m[6]*v[1]+m[10]*v[2]+m[14]];
let moved=0,blocks=0;
for(const node of R.listNodes()){const mesh=node.getMesh();if(!mesh)continue;const W=node.getWorldMatrix();
 const sy=Math.hypot(W[4],W[5],W[6]);   // 节点只有平移+等比缩放：世界 dy → 局部 dy/sy
 for(const p of mesh.listPrimitives()){if(re&&!re.test(p.getMaterial()?.getName()||''))continue;
  const pos=p.getAttribute('POSITION'),ia=p.getIndices().getArray();const nv=pos.getCount();
  const par=new Int32Array(nv).map((_,i)=>i);const f=i=>{while(par[i]!==i){par[i]=par[par[i]];i=par[i];}return i;};
  for(let t=0;t<ia.length;t+=3){const a=f(ia[t]);par[f(ia[t+1])]=a;par[f(ia[t+2])]=a;}
  const bb=new Map(),e=[];
  for(let i=0;i<nv;i++){const w=mul(W,pos.getElement(i,e));const x=w[0],y=-w[2],z=w[1];const r=f(i);let q=bb.get(r);
   if(!q){q=[1e9,1e9,1e9,-1e9,-1e9,-1e9];bb.set(r,q);}q[0]=Math.min(q[0],x);q[1]=Math.min(q[1],y);q[2]=Math.min(q[2],z);q[3]=Math.max(q[3],x);q[4]=Math.max(q[4],y);q[5]=Math.max(q[5],z);}
  const go=new Set();for(const [r,q] of bb)if(q[0]>=X0&&q[3]<=X1&&q[1]>=Y0&&q[4]<=Y1&&q[2]>S.zmin&&q[5]>S.zmax)go.add(r);
  blocks+=go.size;
  const ring=v=>{if(!S.ring)return false;const x=v[0],y=-v[2],z=v[1];const [a,b,c,d]=S.ring;
   return x>=X0&&x<=X1&&y>=Y0&&y<=Y1&&z>S.zlow&&!(x>a&&x<c&&y>b&&y<d);};
  for(let i=0;i<nv;i++){pos.getElement(i,e);if(go.has(f(i))||ring(mul(W,e))){e[1]+=S.dz/sy;pos.setElement(i,e);moved++;}}}}
await doc.transform(meshopt({encoder:MeshoptEncoder,level:'medium'}));
fs.writeFileSync(dst,await io.writeBinary(doc));
console.log('lifted',blocks,'blocks,',moved,'verts;',fs.statSync(src).size,'->',fs.statSync(dst).size,'bytes');
