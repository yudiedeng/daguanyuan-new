// 蘅芜苑主楼匾上的立体金字：2026-10-05 按 .blend 重导时这组字（节点 hengwu_匾蘅芜苑_字）没导出来，匾成了空的。
// 从重导前的旧模型（git c811011^ 的 models/b/hengwu.wasm）里取出这组字中主楼那一块（局部 z < 5，院门那块网页另有写字），存成 models/b/hw_bian.wasm。
// 用法：git show c811011^:models/b/hengwu.wasm > /tmp/hw_old.wasm && node hw_bian.mjs /tmp/hw_old.wasm ../../../models/b/hw_bian.wasm
import {NodeIO} from '@gltf-transform/core';import {ALL_EXTENSIONS} from '@gltf-transform/extensions';
import {dequantize,prune,quantize,meshopt,transformPrimitive} from '@gltf-transform/functions';
import {MeshoptDecoder,MeshoptEncoder} from 'meshoptimizer';import fs from 'fs';
await MeshoptDecoder.ready;await MeshoptEncoder.ready;
const io=new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({'meshopt.decoder':MeshoptDecoder,'meshopt.encoder':MeshoptEncoder});
const [,,src,dst]=process.argv;const doc=await io.read(src);await doc.transform(dequantize());const R=doc.getRoot(),scene=R.listScenes()[0];
let keep=null;for(const n of R.listNodes()){if(n.getName()==='hengwu_匾蘅芜苑_字')keep=n;}
if(!keep)throw new Error('没找到 hengwu_匾蘅芜苑_字');
const W=keep.getWorldMatrix();const mesh=keep.getMesh();
for(const p of mesh.listPrimitives()){transformPrimitive(p,W);const pos=p.getAttribute('POSITION'),idx=p.getIndices(),I=idx.getArray(),out=[],v=[0,0,0];
 for(let t=0;t<I.length;t+=3){let z=0;for(let j=0;j<3;j++){pos.getElement(I[t+j],v);z+=v[2];}if(z/3<5)out.push(I[t],I[t+1],I[t+2]);}
 idx.setArray(new Uint32Array(out));console.log('主楼匾字三角形',out.length/3,'/',I.length/3);}
for(const n of R.listNodes())if(n!==keep)n.dispose();
keep.setMatrix([1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1]);for(const c of scene.listChildren())if(c!==keep)scene.removeChild(c);if(!scene.listChildren().includes(keep))scene.addChild(keep);
await doc.transform(prune(),quantize(),meshopt({encoder:MeshoptEncoder,level:'medium'}));
fs.writeFileSync(dst,await io.writeBinary(doc));console.log('写出',dst,fs.statSync(dst).size,'bytes');
