// 把道具 GLB 里名为“花叶”“芭蕉叶”的贴图材质改成 alphaMode MASK（Blender 导出是 BLEND），并都设双面。用法：node alpha_mask.mjs models/p/yh_*.glb
import {NodeIO} from '@gltf-transform/core';import {ALL_EXTENSIONS} from '@gltf-transform/extensions';import {MeshoptDecoder,MeshoptEncoder} from 'meshoptimizer';import fs from 'fs';
await MeshoptDecoder.ready;await MeshoptEncoder.ready;const io=new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({'meshopt.decoder':MeshoptDecoder,'meshopt.encoder':MeshoptEncoder});
for(const f of process.argv.slice(2)){const d=await io.read(f);for(const m of d.getRoot().listMaterials()){m.setDoubleSided(true);if(m.getName()==='花叶'||m.getName()==='芭蕉叶'){m.setAlphaMode('MASK');m.setAlphaCutoff(0.5);}}fs.writeFileSync(f,await io.writeBinary(d));console.log('mask',f);}
