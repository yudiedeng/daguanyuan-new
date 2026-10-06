// 远景简化版：models/b/<id>.wasm -> models/b/lod/<id>.wasm（节点、材质原样，只按误差上限减面）。
// 网页里院落离相机 50 m 以外、以及湖面/清溪倒影里用它；误差按院落尺寸的 ERR（默认 0.0015，约 1–2 像素）。
// 用法：node lod_glb.mjs [ERR] id1 id2 ...
import {NodeIO} from '@gltf-transform/core';import {ALL_EXTENSIONS} from '@gltf-transform/extensions';
import {dequantize,weld,simplifyPrimitive,prune,quantize,meshopt,getBounds} from '@gltf-transform/functions';
import {MeshoptDecoder,MeshoptEncoder,MeshoptSimplifier} from 'meshoptimizer';import fs from 'fs';
await MeshoptDecoder.ready;await MeshoptEncoder.ready;await MeshoptSimplifier.ready;
const io=new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({'meshopt.decoder':MeshoptDecoder,'meshopt.encoder':MeshoptEncoder});
const args=process.argv.slice(2);const ERR=/^[0-9.]+$/.test(args[0])?+args.shift():0.0015;
const B='../../../models/b/';const DIR=process.env.LODDIR||'lod';fs.mkdirSync(B+DIR,{recursive:true});
const tri=d=>d.getRoot().listMeshes().reduce((s,m)=>s+m.listPrimitives().reduce((t,p)=>t+(p.getIndices()?p.getIndices().getCount():p.getAttribute('POSITION').getCount())/3,0),0);
for(const id of args){const doc=await io.read(B+id+'.wasm');const t0=tri(doc);
 // simplify 的误差相对每个图元自己的尺寸；换算成整座院落的绝对误差，小构件不至于被减坏
 const S=getBounds(doc.getRoot().listScenes()[0]);const size=Math.max(...S.max.map((v,i)=>v-S.min[i]));
 await doc.transform(dequantize(),weld());
 for(const m of doc.getRoot().listMeshes())for(const p of m.listPrimitives()){const pos=p.getAttribute('POSITION');let lo=[1e9,1e9,1e9],hi=[-1e9,-1e9,-1e9];const v=[0,0,0];for(let i=0;i<pos.getCount();i++){pos.getElement(i,v);for(let k=0;k<3;k++){lo[k]=Math.min(lo[k],v[k]);hi[k]=Math.max(hi[k],v[k]);}}
  const ps=Math.max(hi[0]-lo[0],hi[1]-lo[1],hi[2]-lo[2])||1;p.setExtras({...p.getExtras(),lodErr:Math.min(0.5,ERR*size/ps)});}
 for(const m of doc.getRoot().listMeshes())for(const p of m.listPrimitives())simplifyPrimitive(p,{simplifier:MeshoptSimplifier,ratio:0,error:p.getExtras().lodErr,lockBorder:false});
 for(const m of doc.getRoot().listMeshes())for(const p of m.listPrimitives()){const i=p.getIndices(),n=i?i.getCount():p.getAttribute('POSITION').getCount();if(n<3||p.getAttribute('POSITION').getCount()<3){m.removePrimitive(p);p.dispose();}}  // 减没了的小件（远处本来就看不见）去掉
 await doc.transform(prune({keepAttributes:true}),quantize(),meshopt({encoder:MeshoptEncoder,level:'medium'}));
 const out=B+DIR+'/'+id+'.wasm';fs.writeFileSync(out,await io.writeBinary(doc));
 console.log(id,(t0/1e3).toFixed(0)+'k ->',(tri(doc)/1e3).toFixed(0)+'k','size',size.toFixed(0)+'m',(fs.statSync(B+id+'.wasm').size/1e6).toFixed(1)+'MB ->',(fs.statSync(out).size/1e6).toFixed(1)+'MB');}
