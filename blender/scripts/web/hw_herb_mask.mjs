// 蘅芜苑院内铺异草的掩码：院落模型 hengwu 的占地（院土、原有异草、藤萝不算）。
// 房、游廊、墙（高出地面 0.6 m 以上）再向外扩一格；甬路、台阶只占本身；山石不扩——异草要长到石脚、石缝里（“或穿石隙”）。
// 网格：院落坐标（模型原点）x −17.5…17.5、z −13.5…13.5，步长 0.5 m，逐行（z）逐列（x）1 位，base64。
// 用法：node hw_herb_mask.mjs   → 打印字符串，贴到 index.html buildHengwuYard 的 HWMASK
import {NodeIO} from '@gltf-transform/core';import {ALL_EXTENSIONS} from '@gltf-transform/extensions';import {MeshoptDecoder} from 'meshoptimizer';
await MeshoptDecoder.ready;
const io=new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({'meshopt.decoder':MeshoptDecoder});
const R=0.5,X0=-17.5,Z0=-13.5,NX=71,NZ=55,occ=new Uint8Array(NX*NZ);  // 1 贴地或山石  2 房屋墙廊
const mark=(x,z,c)=>{const i=Math.round((x-X0)/R),j=Math.round((z-Z0)/R);if(i>=0&&i<NX&&j>=0&&j<NZ)occ[j*NX+i]=Math.max(occ[j*NX+i],c);};
const doc=await io.read(new URL('../../../models/b/hengwu.wasm',import.meta.url).pathname);
for(const n of doc.getRoot().listNodes()){const mesh=n.getMesh(),nm=n.getName();if(!mesh||/地面_soil|异草|藤萝/.test(nm))continue;const M=n.getWorldMatrix(),rock=/群石/.test(nm);
 for(const p of mesh.listPrimitives()){const a=p.getAttribute('POSITION'),ix=p.getIndices(),v=[0,0,0],P=[];
  for(let i=0;i<a.getCount();i++){a.getElement(i,v);P.push([M[0]*v[0]+M[4]*v[1]+M[8]*v[2]+M[12],M[2]*v[0]+M[6]*v[1]+M[10]*v[2]+M[14],M[1]*v[0]+M[5]*v[1]+M[9]*v[2]+M[13]]);}
  const T=ix?ix.getCount()/3:P.length/3;
  for(let t=0;t<T;t++){const q=[0,1,2].map(k=>P[ix?ix.getScalar(t*3+k):t*3+k]);
   if(Math.min(q[0][2],q[1][2],q[2][2])>2.2)continue;  // 檐口、屋面不占地
   const c=!rock&&Math.max(q[0][2],q[1][2],q[2][2])>0.6?2:1,e=Math.max(...[0,1,2].map(k=>Math.hypot(q[k][0]-q[(k+1)%3][0],q[k][1]-q[(k+1)%3][1]))),s=Math.max(1,Math.ceil(e/0.2));
   for(let i=0;i<=s;i++)for(let j=0;j<=s-i;j++){const u=i/s,w=j/s;const y=q[0][2]*(1-u-w)+q[1][2]*u+q[2][2]*w;if(rock&&y>0.35)continue;  // 山石只按贴地的一圈占地
    mark(q[0][0]*(1-u-w)+q[1][0]*u+q[2][0]*w,q[0][1]*(1-u-w)+q[1][1]*u+q[2][1]*w,c);}}}}
const bits=new Uint8Array(Math.ceil(NX*NZ/8));let free=0;const rows=[];
for(let j=0;j<NZ;j++){let r='';for(let i=0;i<NX;i++){let b=occ[j*NX+i]>0;for(let dj=-1;dj<=1;dj++)for(let di=-1;di<=1;di++){const a=i+di,c=j+dj;if(a>=0&&a<NX&&c>=0&&c<NZ&&occ[c*NX+a]===2)b=1;}const k=j*NX+i;if(b)bits[k>>3]|=1<<(k&7);else free++;r+=b?'#':'.';}rows.push(r);}
if(process.argv[2]==='-v')console.error(rows.join('\n')+'\nfree cells '+free);
console.log(Buffer.from(bits).toString('base64'));
