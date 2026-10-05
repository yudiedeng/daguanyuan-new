// 潇湘馆院内种竹的掩码：院落模型 xiaoxiang_ct + 正房 xiaoxiang 的占地（土山泥地和山上点石除外，竹子可以长在土山上）。
// 高出地面 0.6 m 以上的（房、游廊、墙、梨树、芭蕉…）再向外扩一格；贴地的（甬路、泉沟、沟边石）只占本身；外加院中太湖石、石桌石墩、风炉、花冢（index.html 的 PROPS.xiaoxiang_ct）。
// 网格：院落坐标（模型原点）x −14…14、z −13…17，步长 0.5 m，逐行（z）逐列（x）1 位，base64。
// 用法：node xx_bamboo_mask.mjs   → 打印字符串，贴到 index.html buildXiaoxiang 的 XXMASK
import {NodeIO} from '@gltf-transform/core';import {ALL_EXTENSIONS} from '@gltf-transform/extensions';import {MeshoptDecoder} from 'meshoptimizer';
await MeshoptDecoder.ready;
const io=new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({'meshopt.decoder':MeshoptDecoder});
const R=0.5,X0=-14,Z0=-13,NX=57,NZ=61,occ=new Uint8Array(NX*NZ);  // 1 贴地  2 高出地面
const mark=(x,z,c=2)=>{const i=Math.round((x-X0)/R),j=Math.round((z-Z0)/R);if(i>=0&&i<NX&&j>=0&&j<NZ)occ[j*NX+i]=Math.max(occ[j*NX+i],c);};
const GROW=[[/^梨树_/,[-1.95,0.6,-8.6],2.6],[/^芭蕉_/,[1.4,0,-6.9],1.5]];  // 与 index.html BLD 里 xiaoxiang_ct 的 grow 一致
const root=new URL('../../../models/b/',import.meta.url);
for(const f of ['xiaoxiang_ct','xiaoxiang']){const doc=await io.read(new URL(f+'.wasm',root).pathname);
 for(const n of doc.getRoot().listNodes()){const mesh=n.getMesh();if(!mesh||/^土山/.test(n.getName()))continue;let M=n.getWorldMatrix();
  for(const [re,[cx,cy,cz],k] of GROW)if(re.test(n.getName())){M=M.map((v,i)=>i<12?v*k:v);M[12]=cx+(M[12]-cx)*k;M[13]=cy+(M[13]-cy)*k;M[14]=cz+(M[14]-cz)*k;}  // 与 index.html 的 grow 一致
  for(const p of mesh.listPrimitives()){const a=p.getAttribute('POSITION'),ix=p.getIndices(),v=[0,0,0],P=[];
   for(let i=0;i<a.getCount();i++){a.getElement(i,v);P.push([M[0]*v[0]+M[4]*v[1]+M[8]*v[2]+M[12],M[2]*v[0]+M[6]*v[1]+M[10]*v[2]+M[14],M[1]*v[0]+M[5]*v[1]+M[9]*v[2]+M[13]]);}
   const T=ix?ix.getCount()/3:P.length/3;
   for(let t=0;t<T;t++){const q=[0,1,2].map(k=>P[ix?ix.getScalar(t*3+k):t*3+k]);
    const c=Math.max(q[0][2],q[1][2],q[2][2])>0.6?2:1,e=Math.max(...[0,1,2].map(k=>Math.hypot(q[k][0]-q[(k+1)%3][0],q[k][1]-q[(k+1)%3][1]))),s=Math.max(1,Math.ceil(e/0.2));
    for(let i=0;i<=s;i++)for(let j=0;j<=s-i;j++){const u=i/s,w=j/s;mark(q[0][0]*(1-u-w)+q[1][0]*u+q[2][0]*w,q[0][1]*(1-u-w)+q[1][1]*u+q[2][1]*w,c);}}}}}
for(const [cx,cz,r] of [[-6.6,11.6,1.3],[-10.9,9.7,0.9],[5.0,7.6,1.7],[6.45,8.75,0.5],[-5.0,-10.0,1.0]])for(let x=cx-r;x<=cx+r;x+=0.25)for(let z=cz-r;z<=cz+r;z+=0.25)if(Math.hypot(x-cx,z-cz)<=r)mark(x,z);
const bits=new Uint8Array(Math.ceil(NX*NZ/8));
for(let j=0;j<NZ;j++)for(let i=0;i<NX;i++){let b=occ[j*NX+i]>0;for(let dj=-1;dj<=1;dj++)for(let di=-1;di<=1;di++){const a=i+di,c=j+dj;if(a>=0&&a<NX&&c>=0&&c<NZ&&occ[c*NX+a]===2)b=1;}const k=j*NX+i;if(b)bits[k>>3]|=1<<(k&7);}
console.log(Buffer.from(bits).toString('base64'));
