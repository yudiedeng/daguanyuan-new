// 原始 GLB -> models/b/<id>.wasm（与现有网页模型同一结构）：
//   一材质一节点（节点名沿用参考模型里同材质节点的名字）、去 UV（雕花_* 透雕板、彩画_* 除外）、焊接、量化、meshopt 压缩。
// 用法：node pack_glb.mjs in.glb out.wasm [ref.wasm] [keepcolor] [简化误差]
//   keepcolor：保留顶点颜色 COLOR_0（潇湘馆正房的做旧数据）；简化误差：meshopt 按误差上限简化（相对尺寸，如 0.0006），不给就不简化。
//   ref.wasm：当前线上模型，用来继承节点命名；主匾（*匾_匾底，非对联）若参考模型用 M_匾心 则沿用。
import {NodeIO} from '@gltf-transform/core';import {ALL_EXTENSIONS} from '@gltf-transform/extensions';
import {dedup,join,weld,prune,quantize,meshopt,transformPrimitive,simplify} from '@gltf-transform/functions';
import {MeshoptDecoder,MeshoptEncoder,MeshoptSimplifier} from 'meshoptimizer';import fs from 'fs';
await MeshoptDecoder.ready;await MeshoptEncoder.ready;await MeshoptSimplifier.ready;
const io=new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({'meshopt.decoder':MeshoptDecoder,'meshopt.encoder':MeshoptEncoder});
const [,,src,dst,refPath,keep,simpErr]=process.argv;const KEEPC=keep==='keepcolor';
const nameOf={};let refHasBianxin=false;
if(refPath&&fs.existsSync(refPath)){const ref=await io.read(refPath);for(const n of ref.getRoot().listNodes()){const m=n.getMesh()?.listPrimitives()[0]?.getMaterial()?.getName();if(m){nameOf[m]??=n.getName();if(m==='M_匾心')refHasBianxin=true;}}}
const doc=await io.read(src);const R=doc.getRoot(),scene=R.listScenes()[0];
let bianxin=null;
const groups=new Map(); // material name -> {mat, prims:[], names:[]}
for(const node of R.listNodes()){const mesh=node.getMesh();if(!mesh)continue;const W=node.getWorldMatrix();
 for(const p of mesh.listPrimitives()){
  const keepUV=/雕花|彩画_/.test(p.getMaterial()?.getName()||'');  // 透雕板、彩画要贴图，留 UV
  for(const s of p.listSemantics())if(s!=='POSITION'&&s!=='NORMAL'&&!(keepUV&&s==='TEXCOORD_0')&&!(KEEPC&&s==='COLOR_0'))p.setAttribute(s,null);
  let mat=p.getMaterial();
  if(refHasBianxin&&/匾_匾底$/.test(node.getName())&&!/联/.test(node.getName())){bianxin??=mat.clone().setName('M_匾心');mat=bianxin;p.setMaterial(mat);}
  const q=p.clone();transformPrimitive(q,W);
  const k=mat?mat.getName():'';if(!groups.has(k))groups.set(k,{prims:[],names:[]});const g=groups.get(k);g.prims.push(q);g.names.push(node.getName());}}
for(const n of R.listNodes())n.dispose();for(const m of R.listMeshes())if(!m.listParents().some(p=>p.propertyType==='Node'))m.dispose();
for(const [k,g] of groups){const name=nameOf[k]||g.names.sort()[0];const mesh=doc.createMesh(name);for(const p of g.prims)mesh.addPrimitive(p);scene.addChild(doc.createNode(name).setMesh(mesh));}
const pre=[prune({keepAttributes:true}),dedup({propertyTypes:['Accessor','Mesh']}),join({keepNamed:false,keepMeshes:true}),weld()];if(simpErr)pre.push(simplify({simplifier:MeshoptSimplifier,ratio:0,error:+simpErr,lockBorder:true}));
await doc.transform(...pre,prune({keepAttributes:true}),quantize(),meshopt({encoder:MeshoptEncoder,level:'medium'}));
fs.writeFileSync(dst,await io.writeBinary(doc));
console.log('nodes',R.listNodes().length,'bytes',fs.statSync(dst).size);
for(const n of R.listNodes())console.log(' ',n.getName(),n.getMesh().listPrimitives().map(p=>p.getMaterial()?.getName()).join(','));
