// Tripo 生成的道具 GLB -> models/p/<名>.glb：去掉地台外的多余节点、底面中心归到原点、高度归一为 1 m、
// 减面（meshopt simplify）、贴图缩到 512 并转 webp、meshopt 压缩。网页里按需要的高度缩放。
// 用法：node pack_prop.mjs in.glb out.glb [目标三角形数=6000] [贴图边长=512] [keep]   （keep：不归一尺寸，保留原坐标，如竹下落叶片）
import {NodeIO} from '@gltf-transform/core';import {ALL_EXTENSIONS} from '@gltf-transform/extensions';
import {dedup,weld,prune,simplify,textureCompress,meshopt,flatten,join,getBounds,transformMesh} from '@gltf-transform/functions';
import {MeshoptDecoder,MeshoptEncoder,MeshoptSimplifier} from 'meshoptimizer';import sharp from 'sharp';import fs from 'fs';
await MeshoptDecoder.ready;await MeshoptEncoder.ready;await MeshoptSimplifier.ready;
const io=new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({'meshopt.decoder':MeshoptDecoder,'meshopt.encoder':MeshoptEncoder});
const [,,src,dst,tri='6000',tex='512',mode='']=process.argv;
const doc=await io.read(src);const R=doc.getRoot(),scene=R.listScenes()[0];
await doc.transform(flatten(),join(),weld());
const tris=()=>R.listMeshes().reduce((s,m)=>s+m.listPrimitives().reduce((a,p)=>a+(p.getIndices()?p.getIndices().getCount():p.getAttribute('POSITION').getCount())/3,0),0);
const t0=tris(),ratio=Math.min(1,+tri/t0);
if(ratio<1)await doc.transform(simplify({simplifier:MeshoptSimplifier,ratio,error:0.01}));
// 归一：底面中心在原点，高 1
const b=getBounds(scene),h=b.max[1]-b.min[1],cx=(b.min[0]+b.max[0])/2,cz=(b.min[2]+b.max[2])/2,s=1/h;
const M=[s,0,0,0, 0,s,0,0, 0,0,s,0, -cx*s,-b.min[1]*s,-cz*s,1];
if(mode!=='keep')for(const n of R.listNodes()){const m=n.getMesh();if(!m)continue;transformMesh(m,M);n.setMatrix([1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1]);}
for(const m of R.listMaterials()){m.setMetallicFactor(Math.min(m.getMetallicFactor(),0.6));}
// 带透明的贴图（花叶贴图集、芭蕉叶）不经 textureCompress：sharp 缩放、编 webp 都会把透明处的颜色抹黑，远处 mip 后叶片发黑。
// 这类贴图原样存无损 webp（exact 保留透明处颜色），其余有损 webp 缩到 tex
const alphaTex=new Set(R.listMaterials().filter(m=>m.getAlphaMode()!=='OPAQUE').map(m=>m.getBaseColorTexture()).filter(Boolean));
for(const t of R.listTextures())if(alphaTex.has(t))t.setName('A__'+t.getName());
await doc.transform(textureCompress({encoder:sharp,targetFormat:'webp',resize:[+tex,+tex],quality:80,pattern:/^(?!A__).+$/}));
for(const t of alphaTex){t.setImage(await sharp(Buffer.from(t.getImage())).webp({lossless:true,exact:true}).toBuffer());t.setMimeType('image/webp');t.setName(t.getName().replace(/^A__/,''));}
await doc.transform(dedup(),prune(),meshopt({encoder:MeshoptEncoder,level:'medium'}));
fs.writeFileSync(dst,await io.writeBinary(doc));
console.log(src.split('/').pop(),'tris',Math.round(t0),'->',Math.round(tris()),'w/d',((b.max[0]-b.min[0])*s).toFixed(2),((b.max[2]-b.min[2])*s).toFixed(2),'bytes',fs.statSync(dst).size);
