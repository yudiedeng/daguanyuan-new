// 把 Tripo 道具贴图里发黄发亮的叶片像素压暗、压饱和（花不动），直接改写 GLB。用法：node leaf_dark.mjs models/p/huacong_mudan.glb [强度=0.62]
import {NodeIO} from '@gltf-transform/core';import {ALL_EXTENSIONS} from '@gltf-transform/extensions';import {MeshoptDecoder,MeshoptEncoder} from 'meshoptimizer';import sharp from 'sharp';import fs from 'fs';
await MeshoptDecoder.ready;await MeshoptEncoder.ready;const io=new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({'meshopt.decoder':MeshoptDecoder,'meshopt.encoder':MeshoptEncoder});
const [,,f,k='0.62']=process.argv;const K=+k;const d=await io.read(f);let n=0;
for(const m of d.getRoot().listMaterials()){const t=m.getBaseColorTexture();if(!t)continue;const {data,info}=await sharp(Buffer.from(t.getImage())).ensureAlpha().raw().toBuffer({resolveWithObject:true});
 for(let i=0;i<data.length;i+=4){const r=data[i],g=data[i+1],b=data[i+2];if(g>r*0.95&&g>b*1.15){const l=(r+g+b)/3;data[i]=(r*0.55+l*0.15)*K;data[i+1]=(g*0.7+l*0.1)*K;data[i+2]=(b*0.6+l*0.15)*K;n++;}}
 t.setImage(await sharp(data,{raw:info}).webp({quality:85}).toBuffer());t.setMimeType('image/webp');}
fs.writeFileSync(f,await io.writeBinary(d));console.log('darkened px',n);
