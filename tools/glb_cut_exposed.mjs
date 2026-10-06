// 剪掉“露在屋顶外”的面：指定材质（如 旧木）的三角形，从质心往正上方打射线，碰不到屋面材质（如 灰瓦|屋脊）的就删。
// 用来去掉建模时穿出瓦面的檩条、椽子（栊翠庵配殿、山门屋面上露出的长木条）。
// 用法：node tools/glb_cut_exposed.mjs in.wasm out.wasm '<被剪材质正则>' '<屋面材质正则>' [只剪高于此 y 的面，默认 2]
import {createRequire} from 'module';
const require=createRequire(new URL('../blender/scripts/web/package.json',import.meta.url));
const {NodeIO}=require('@gltf-transform/core');const {ALL_EXTENSIONS}=require('@gltf-transform/extensions');
const {MeshoptDecoder,MeshoptEncoder}=require('meshoptimizer');const {compactPrimitive,meshopt}=require('@gltf-transform/functions');const fs=require('fs');
await MeshoptDecoder.ready;await MeshoptEncoder.ready;
const io=new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({'meshopt.decoder':MeshoptDecoder,'meshopt.encoder':MeshoptEncoder});
const [,,src,dst,cutS,roofS,minYS]=process.argv;const cutRe=new RegExp(cutS),roofRe=new RegExp(roofS),minY=+(minYS??2);
const doc=await io.readBinary(new Uint8Array(fs.readFileSync(src)));const Rt=doc.getRoot();
const mul=(m,v)=>[m[0]*v[0]+m[4]*v[1]+m[8]*v[2]+m[12],m[1]*v[0]+m[5]*v[1]+m[9]*v[2]+m[13],m[2]*v[0]+m[6]*v[1]+m[10]*v[2]+m[14]];
// 屋面三角形按 0.5 米格子索引
const C=0.5,G=new Map();
for(const node of Rt.listNodes()){const mesh=node.getMesh();if(!mesh)continue;const W=node.getWorldMatrix();
 for(const p of mesh.listPrimitives()){if(!roofRe.test(p.getMaterial()?.getName()||''))continue;const a=p.getAttribute('POSITION'),I=p.getIndices(),e=[];
  for(let t=0;t<I.getCount();t+=3){const v=[0,1,2].map(k=>mul(W,a.getElement(I.getScalar(t+k),e)));
   const x0=Math.floor(Math.min(v[0][0],v[1][0],v[2][0])/C),x1=Math.floor(Math.max(v[0][0],v[1][0],v[2][0])/C),z0=Math.floor(Math.min(v[0][2],v[1][2],v[2][2])/C),z1=Math.floor(Math.max(v[0][2],v[1][2],v[2][2])/C);
   for(let i=x0;i<=x1;i++)for(let j=z0;j<=z1;j++){const k=i+','+j;(G.get(k)||G.set(k,[]).get(k)).push(v);}}}}
// 竖直向上的射线与三角形（只看 xz 投影里是否包含该点、交点是否在上方）
const above=(x,y,z)=>{const L=G.get(Math.floor(x/C)+','+Math.floor(z/C));if(!L)return false;
 for(const [a,b,c] of L){const d=(b[2]-c[2])*(a[0]-c[0])+(c[0]-b[0])*(a[2]-c[2]);if(Math.abs(d)<1e-12)continue;
  const l1=((b[2]-c[2])*(x-c[0])+(c[0]-b[0])*(z-c[2]))/d,l2=((c[2]-a[2])*(x-c[0])+(a[0]-c[0])*(z-c[2]))/d,l3=1-l1-l2;if(l1<-1e-6||l2<-1e-6||l3<-1e-6)continue;
  if(l1*a[1]+l2*b[1]+l3*c[1]>y+0.005)return true;}return false;};
let cut=0,total=0;
for(const node of Rt.listNodes()){const mesh=node.getMesh();if(!mesh)continue;const W=node.getWorldMatrix();
 for(const p of mesh.listPrimitives()){if(!cutRe.test(p.getMaterial()?.getName()||''))continue;const a=p.getAttribute('POSITION'),idx=p.getIndices(),e=[],keep=[];
  for(let t=0;t<idx.getCount();t+=3){const v=[0,1,2].map(k=>mul(W,a.getElement(idx.getScalar(t+k),e)));total++;const m=[0,1,2].map(i=>(v[0][i]+v[1][i]+v[2][i])/3);
   // 质心和三个顶点都露在外面才删（贴着瓦面下沿、只露一角的不动）
   if(m[1]>minY&&!above(...m)&&v.every(q=>!above(...q))){cut++;continue;}keep.push(idx.getScalar(t),idx.getScalar(t+1),idx.getScalar(t+2));}
  if(keep.length!==idx.getCount()){const A=idx.getArray().constructor;idx.setArray(new A(keep));compactPrimitive(p);}}}
await doc.transform(meshopt({encoder:MeshoptEncoder,level:'medium'}));fs.writeFileSync(dst,await io.writeBinary(doc));
console.log('cut',cut,'of',total,'tris');
