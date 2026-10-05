// 蘅芜苑院门：右边门枕石上的石鼓建模时放偏了（x 0.80…0.98，左边是 -0.80…-0.62），挪回与左边对称。
// 用法：node fix_hw_drum.mjs   （改 models/b/hengwu.wasm；只动右鼓那几块面，可重复执行——已对称则不动）
import {NodeIO} from '@gltf-transform/core';import {ALL_EXTENSIONS} from '@gltf-transform/extensions';
import {MeshoptDecoder,MeshoptEncoder} from 'meshoptimizer';import fs from 'fs';
await MeshoptDecoder.ready;await MeshoptEncoder.ready;
const io=new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({'meshopt.decoder':MeshoptDecoder,'meshopt.encoder':MeshoptEncoder});
const F=new URL('../../../models/b/hengwu.wasm',import.meta.url).pathname;const doc=await io.read(F);
const inv=m=>{const [a,b,c,,e,f,g,,i,j,k,,x,y,z]=m;const det=a*(f*k-g*j)-b*(e*k-g*i)+c*(e*j-f*i);const r=[(f*k-g*j)/det,-(b*k-c*j)/det,(b*g-c*f)/det,-(e*k-g*i)/det,(a*k-c*i)/det,-(a*g-c*e)/det,(e*j-f*i)/det,-(a*j-b*i)/det,(a*f-b*e)/det];return v=>{const p=[v[0]-x,v[1]-y,v[2]-z];return [r[0]*p[0]+r[3]*p[1]+r[6]*p[2],r[1]*p[0]+r[4]*p[1]+r[7]*p[2],r[2]*p[0]+r[5]*p[1]+r[8]*p[2]];};};
let n=0;const W=(M,v)=>[M[0]*v[0]+M[4]*v[1]+M[8]*v[2]+M[12],M[1]*v[0]+M[5]*v[1]+M[9]*v[2]+M[13],M[2]*v[0]+M[6]*v[1]+M[10]*v[2]+M[14]];
const drum=w=>w[0]>0.6&&w[0]<1.0&&w[1]>0.41&&w[1]<0.83&&w[2]>14.04&&w[2]<14.46;
for(const node of doc.getRoot().listNodes()){if(!/南墙_stone/.test(node.getName()))continue;const M=node.getWorldMatrix(),toL=inv(M);
 for(const p of node.getMesh().listPrimitives()){const a=p.getAttribute('POSITION'),v=[0,0,0];let mx=-9;
  for(let i=0;i<a.getCount();i++){a.getElement(i,v);const w=W(M,v);if(drum(w))mx=Math.max(mx,w[0]);}
  if(mx<0.9)continue;   // 已经对称（右鼓外沿 0.80）
  for(let i=0;i<a.getCount();i++){a.getElement(i,v);const w=W(M,v);if(drum(w)){w[0]-=0.18;a.setElement(i,toL(w));n++;}}}}
console.log('moved verts',n);
if(n)fs.writeFileSync(F,await io.writeBinary(doc));
