// Blender 导出的植物 GLB（hw_plants.py）-> 网页用：保留顶点色，焊接、量化、meshopt 压缩；每个物体一个节点（名字不变）。
// 用法：node pack_plants.mjs in.glb out.(wasm|glb)
import {NodeIO} from '@gltf-transform/core';import {ALL_EXTENSIONS} from '@gltf-transform/extensions';
import {dedup,weld,prune,quantize,meshopt} from '@gltf-transform/functions';
import {MeshoptDecoder,MeshoptEncoder} from 'meshoptimizer';import fs from 'fs';
await MeshoptDecoder.ready;await MeshoptEncoder.ready;
const io=new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({'meshopt.decoder':MeshoptDecoder,'meshopt.encoder':MeshoptEncoder});
const [,,src,dst]=process.argv;const doc=await io.read(src);const R=doc.getRoot();
for(const m of R.listMeshes())for(const p of m.listPrimitives())for(const s of p.listSemantics())if(!['POSITION','NORMAL','COLOR_0'].includes(s))p.setAttribute(s,null);
await doc.transform(prune(),dedup(),weld(),quantize({quantizeColor:8}),meshopt({encoder:MeshoptEncoder,level:'medium'}));
fs.writeFileSync(dst,await io.writeBinary(doc));
console.log(dst.split('/').pop(),'bytes',fs.statSync(dst).size,R.listNodes().map(n=>n.getName()).join(' '));
