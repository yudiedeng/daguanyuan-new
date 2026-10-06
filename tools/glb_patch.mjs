// 给网页模型（models/b/<id>.wasm）打补丁，不整座重导（.blend 与线上模型已有差异时用，比如线上屋面减过面）：
//   node tools/glb_patch.mjs in.wasm out.wasm patch.glb '<json>'
//   patch.glb：从 .blend 只导出要换/要加的对象（export_glb 同样坐标约定）。
//   json：{"rename":{"旧材质":"新材质"}, "drop":["整份删掉的材质"], "retag":{"线上材质":"补丁材质"}}
//     retag：线上模型里材质 A 的三角形，若与补丁里材质 B 的某个三角形重合（质心各轴差 1.2 cm 内），删掉（补丁里那份以 B 加回）。
//   补丁里的网格按材质各成一个节点并入，再 meshopt 压缩。
import {createRequire} from 'module';
const require=createRequire(new URL('../blender/scripts/web/package.json',import.meta.url));
const {NodeIO}=require('@gltf-transform/core');const {ALL_EXTENSIONS}=require('@gltf-transform/extensions');
const {MeshoptDecoder,MeshoptEncoder}=require('meshoptimizer');const {compactPrimitive,meshopt,prune,transformPrimitive,join,weld,quantize,dedup}=require('@gltf-transform/functions');const fs=require('fs');
await MeshoptDecoder.ready;await MeshoptEncoder.ready;
const io=new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({'meshopt.decoder':MeshoptDecoder,'meshopt.encoder':MeshoptEncoder});
const [,,src,dst,patchPath,spec]=process.argv;const S=JSON.parse(spec||'{}');
const doc=await io.read(src),R=doc.getRoot(),scene=R.listScenes()[0];
const P=await io.read(patchPath);
const mul=(m,v)=>[m[0]*v[0]+m[4]*v[1]+m[8]*v[2]+m[12],m[1]*v[0]+m[5]*v[1]+m[9]*v[2]+m[13],m[2]*v[0]+m[6]*v[1]+m[10]*v[2]+m[14]];
const G=0.02,TOL=0.012;const cell=c=>c.map(x=>Math.floor(x/G));
const add=(set,c)=>{const k=cell(c).join(',');(set.get(k)||set.set(k,[]).get(k)).push(c);};
const has=(set,c)=>{const [i,j,k]=cell(c);for(let a=-1;a<=1;a++)for(let b=-1;b<=1;b++)for(let d=-1;d<=1;d++){const l=set.get((i+a)+','+(j+b)+','+(k+d));if(l)for(const q of l)if(Math.abs(q[0]-c[0])<TOL&&Math.abs(q[1]-c[1])<TOL&&Math.abs(q[2]-c[2])<TOL)return true;}return false;};
// 补丁里各材质的三角形质心
const cent={};
for(const n of P.getRoot().listNodes()){const me=n.getMesh();if(!me)continue;const W=n.getWorldMatrix();
 for(const p of me.listPrimitives()){const mn=p.getMaterial()?.getName()||'';const pos=p.getAttribute('POSITION'),idx=p.getIndices();const e=[];const set=cent[mn]??=new Map();
  for(let i=0;i<idx.getCount();i+=3){const a=mul(W,pos.getElement(idx.getScalar(i),e)),b=mul(W,pos.getElement(idx.getScalar(i+1),e)),c=mul(W,pos.getElement(idx.getScalar(i+2),e));add(set,[(a[0]+b[0]+c[0])/3,(a[1]+b[1]+c[1])/3,(a[2]+b[2]+c[2])/3]);}}}
let removed=0;
for(const n of R.listNodes()){const me=n.getMesh();if(!me)continue;const W=n.getWorldMatrix();
 for(const p of me.listPrimitives()){const m=p.getMaterial();const mn=m?.getName()||'';
  if((S.drop||[]).includes(mn)){p.dispose();continue;}
  const tgt=(S.retag||{})[mn];if(!tgt||!cent[tgt])continue;
  const pos=p.getAttribute('POSITION'),idx=p.getIndices();const e=[];const keep=[];
  for(let i=0;i<idx.getCount();i+=3){const t=[idx.getScalar(i),idx.getScalar(i+1),idx.getScalar(i+2)];const a=mul(W,pos.getElement(t[0],e)),b=mul(W,pos.getElement(t[1],e)),c=mul(W,pos.getElement(t[2],e));
   if(has(cent[tgt],[(a[0]+b[0]+c[0])/3,(a[1]+b[1]+c[1])/3,(a[2]+b[2]+c[2])/3]))removed++;else keep.push(...t);}
  const ni=doc.createAccessor().setType('SCALAR').setArray(new Uint32Array(keep)).setBuffer(idx.getBuffer());p.setIndices(ni);}}
for(const m of R.listMaterials()){const nn=(S.rename||{})[m.getName()];if(nn)m.setName(nn);}
// 并入补丁：按材质各一个节点；同名材质沿用线上那份
const mats=Object.fromEntries(R.listMaterials().map(m=>[m.getName(),m]));const buf=R.listBuffers()[0];const groups={};
for(const n of P.getRoot().listNodes()){const me=n.getMesh();if(!me)continue;const W=n.getWorldMatrix();
 for(const p of me.listPrimitives()){const mn=p.getMaterial()?.getName()||'';const q=doc.createPrimitive();
  for(const sem of p.listSemantics()){if(sem!=='POSITION'&&sem!=='NORMAL'&&!(sem==='TEXCOORD_0'&&/雕花|彩画_/.test(mn)))continue;const a=p.getAttribute(sem);q.setAttribute(sem,doc.createAccessor().setType(a.getType()).setArray(a.getArray().slice()).setBuffer(buf));}
  q.setIndices(doc.createAccessor().setType('SCALAR').setArray(new Uint32Array(p.getIndices().getArray())).setBuffer(buf));
  q.setMaterial(mats[mn]??=doc.createMaterial(mn));transformPrimitive(q,W);(groups[mn]??=[]).push(q);}}
for(const [mn,ps] of Object.entries(groups)){const me=doc.createMesh(mn);for(const p of ps)me.addPrimitive(p);scene.addChild(doc.createNode('YHP_'+mn.replace(/^M_/,'')).setMesh(me));}
await doc.transform(prune({keepAttributes:true}),dedup({propertyTypes:['Accessor','Mesh']}),join({keepNamed:false,keepMeshes:true}),weld(),prune({keepAttributes:true}),meshopt({encoder:MeshoptEncoder,level:'medium'}));
fs.writeFileSync(dst,await io.writeBinary(doc));
console.log('retag removed',removed,'tris; added',Object.keys(groups).join(' '),'; bytes',fs.statSync(dst).size);
