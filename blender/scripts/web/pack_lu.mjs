// 园路模型（paths_build.py 导出的 GLB）-> models/b/lu_<名>.wasm：
//   和 pack_glb.mjs 不同，不按材质合并——每 12 米一块（base / peb）各自留一个节点，网页才能按远近、视锥剔除；
//   保留顶点色（路面颜色全在顶点色里），焊接、量化、meshopt 压缩。
// 用法：node blender/scripts/web/pack_lu.mjs /tmp/lu_zhou.glb models/b/lu_zhou.wasm
import {NodeIO} from '@gltf-transform/core';import {ALL_EXTENSIONS} from '@gltf-transform/extensions';
import {weld,prune,quantize,meshopt,dedup} from '@gltf-transform/functions';
import {MeshoptDecoder,MeshoptEncoder} from 'meshoptimizer';import fs from 'fs';
await MeshoptDecoder.ready;await MeshoptEncoder.ready;
const io=new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({'meshopt.decoder':MeshoptDecoder,'meshopt.encoder':MeshoptEncoder});
const [,,src,dst]=process.argv;
const doc=await io.read(src);
await doc.transform(dedup(),weld(),prune(),quantize({quantizePosition:16,quantizeColor:8,quantizeNormal:8}),meshopt({encoder:MeshoptEncoder,level:'medium'}));
fs.writeFileSync(dst,await io.writeBinary(doc));
let tris=0;for(const m of doc.getRoot().listMeshes())for(const p of m.listPrimitives())tris+=p.getIndices().getCount()/3;
console.log(doc.getRoot().listNodes().length,'nodes',tris,'tris',fs.statSync(dst).size,'bytes ->',dst);
