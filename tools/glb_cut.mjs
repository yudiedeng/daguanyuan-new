// 从网页模型（models/b/<id>.wasm）里剪掉落在指定盒子里的三角形——用来给实心外壳开门洞、拆隔断。
// 用法：node tools/glb_cut.mjs in.wasm out.wasm '<json>'
//   json：[[x0,y0,z0,x1,y1,z1,"材质名正则(可省)"], ...]，坐标为该院落 .blend 的 Blender 坐标（Z 向上）。
//   判定：三角形质心在盒内即删。可重复执行（已删的不会再出现）。
// 依赖：blender/scripts/web 下 npm i（@gltf-transform/core、extensions、meshoptimizer）。
import {createRequire} from 'module';
const require=createRequire(new URL('../blender/scripts/web/package.json',import.meta.url));
const {NodeIO}=require('@gltf-transform/core');const {ALL_EXTENSIONS}=require('@gltf-transform/extensions');
const {MeshoptDecoder,MeshoptEncoder}=require('meshoptimizer');const {compactPrimitive,meshopt}=require('@gltf-transform/functions');const fs=require('fs');
await MeshoptDecoder.ready;await MeshoptEncoder.ready;
const io=new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({'meshopt.decoder':MeshoptDecoder,'meshopt.encoder':MeshoptEncoder});
const [,,src,dst,spec]=process.argv;
const boxes=JSON.parse(spec).map(b=>({lo:[b[0],b[2],-b[4]],hi:[b[3],b[5],-b[1]],re:b[6]?new RegExp(b[6]):null}));// Blender→glTF: (x, z, -y)
const doc=await io.readBinary(new Uint8Array(fs.readFileSync(src)));const R=doc.getRoot();
const mul=(m,v)=>[m[0]*v[0]+m[4]*v[1]+m[8]*v[2]+m[12],m[1]*v[0]+m[5]*v[1]+m[9]*v[2]+m[13],m[2]*v[0]+m[6]*v[1]+m[10]*v[2]+m[14]];
let cut=0,total=0;
for(const node of R.listNodes()){const mesh=node.getMesh();if(!mesh)continue;const W=node.getWorldMatrix();
 for(const p of mesh.listPrimitives()){const mat=p.getMaterial()?.getName()||'';const bs=boxes.filter(b=>!b.re||b.re.test(mat));if(!bs.length)continue;
  const pos=p.getAttribute('POSITION'),idx=p.getIndices();const n=idx.getCount();const keep=[];const e=[];
  const P=i=>mul(W,pos.getElement(i,e));
  for(let t=0;t<n;t+=3){const a=P(idx.getScalar(t)),b=P(idx.getScalar(t+1)),c=P(idx.getScalar(t+2));total++;
   const m=[(a[0]+b[0]+c[0])/3,(a[1]+b[1]+c[1])/3,(a[2]+b[2]+c[2])/3];
   if(bs.some(B=>m[0]>=B.lo[0]&&m[0]<=B.hi[0]&&m[1]>=B.lo[1]&&m[1]<=B.hi[1]&&m[2]>=B.lo[2]&&m[2]<=B.hi[2])){cut++;continue;}
   keep.push(idx.getScalar(t),idx.getScalar(t+1),idx.getScalar(t+2));}
  if(!keep.length){p.dispose();continue;}// 整个材质都剪光了：直接去掉这个图元（空缓冲会让 meshopt 编码报错）
  if(keep.length!==n){const A=idx.getArray().constructor;idx.setArray(new A(keep));compactPrimitive(p);}}
 if(!mesh.listPrimitives().length){mesh.dispose();node.dispose();}}
await doc.transform(meshopt({encoder:MeshoptEncoder,level:'medium'}));
fs.writeFileSync(dst,await io.writeBinary(doc));
console.log('cut',cut,'of',total,'tris;',fs.statSync(src).size,'->',fs.statSync(dst).size,'bytes');
