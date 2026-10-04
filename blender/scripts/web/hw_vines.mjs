// 蘅芜苑藤萝的挂点：第十七回“或垂山巅，或穿石隙，甚至垂檐绕柱，萦砌盘阶”。
// 从院落模型 hengwu 算：
//   R 垂山巅 —— 山石上朝上、朝外的面（肩、顶），从那里往下垂；沿垂线向下射线求与山石的第一个交点定长度，挂点外移避免穿进石头
//   S 穿石隙 —— 山石侧面（近竖直）的点，短藤从石缝里钻出
//   P 萦砌盘阶 —— 甬路、台基的外沿（只属于一个三角形的边），藤蔓贴地沿边盘过去
// 柱子、檐口位置固定，直接写在 index.html 里。
//   H 玲珑石 —— 巨石正面补的几块太湖石（models/p/hushi.glb），网页照此摆放；也算进山石，藤从它们身上垂
//   D 贴石垂藤 —— 从 R、S 的挂点沿石面往下“爬”：每下 0.2 m 先向石面靠拢、碰到石头再往外推，得到贴着起伏的折线
// 输出 models/b/hw_vines.json：{H:[[x,y,z,ry,h,k]…],R:[[x,y,z,dx,dz,len]…],S:[[x,y,z,dx,dz]…],P:[[x,z,ang]…],D:[[dx,dz,x0,y0,z0,x1,y1,z1…]…]}（院落模型坐标，网页 y 向上）
import {NodeIO} from '@gltf-transform/core';import {ALL_EXTENSIONS} from '@gltf-transform/extensions';import {MeshoptDecoder} from 'meshoptimizer';import {writeFileSync} from 'fs';
await MeshoptDecoder.ready;
const io=new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({'meshopt.decoder':MeshoptDecoder});
const doc=await io.read(new URL('../../../models/b/hengwu.wasm',import.meta.url).pathname);
const tris=(re)=>{const T=[];for(const n of doc.getRoot().listNodes()){const mesh=n.getMesh();if(!mesh||!re.test(n.getName()))continue;const M=n.getWorldMatrix();
 for(const p of mesh.listPrimitives()){const a=p.getAttribute('POSITION'),ix=p.getIndices(),v=[0,0,0],P=[];
  for(let i=0;i<a.getCount();i++){a.getElement(i,v);P.push([M[0]*v[0]+M[4]*v[1]+M[8]*v[2]+M[12],M[1]*v[0]+M[5]*v[1]+M[9]*v[2]+M[13],M[2]*v[0]+M[6]*v[1]+M[10]*v[2]+M[14]]);}
  const n3=ix?ix.getCount():P.length;for(let t=0;t<n3;t+=3){const k=[0,1,2].map(j=>ix?ix.getScalar(t+j):t+j);T.push({i:k.map(j=>j+'@'+n.getName()),p:k.map(j=>P[j])});}}}return T;};
let seed=99;const rnd=()=>{seed=(seed*16807)%2147483647;return seed/2147483647;};
const sub=(a,b)=>[a[0]-b[0],a[1]-b[1],a[2]-b[2]],cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
// 玲珑石摆放：[x, 底 y, z, 转角, 高, 宽/高比]（模型高 1、宽约 0.56×0.62）
const H=[[0.4,-0.2,9.0,0.4,7.2,0.9],[-3.4,-0.2,9.6,2.1,4.2,0.9],[3.6,-0.2,9.4,4.0,4.8,0.85],[-5.6,-0.2,8.6,1.0,3.0,1.0],[5.8,-0.2,8.4,5.2,3.4,0.95],[1.8,2.4,7.4,3.1,3.0,0.9]];  // 近门的小石不放：Tripo 石头近看面数不够
const rock=tris(/群石/);
{const hd=await io.read(new URL('../../../models/p/hushi.glb',import.meta.url).pathname);const hm=hd.getRoot().listMeshes()[0].listPrimitives()[0];const a=hm.getAttribute('POSITION'),ix=hm.getIndices(),v=[0,0,0],V=[];for(let i=0;i<a.getCount();i++){a.getElement(i,v);V.push([...v]);}
 for(const [hx,hy,hz,ry,h,k] of H){const c=Math.cos(ry),s2=Math.sin(ry),P=V.map(([x,y,z])=>{x*=h*k;y*=h;z*=h*k;return [hx+x*c+z*s2,hy+y,hz-x*s2+z*c];});
  for(let t=0;t<ix.getCount();t+=3)rock.push({p:[0,1,2].map(j=>P[ix.getScalar(t+j)])});}}for(const t of rock){const c=cross(sub(t.p[1],t.p[0]),sub(t.p[2],t.p[0])),L=Math.hypot(...c)||1;t.n=c.map(v=>v/L);t.A=L/2;t.c=[0,1,2].map(k=>(t.p[0][k]+t.p[1][k]+t.p[2][k])/3);}
// 向下射线与山石求交（Möller–Trumbore，方向 0,-1,0）
const down=(o)=>{let best=1e9;for(const t of rock){const [a,b,c]=t.p;if(Math.max(a[1],b[1],c[1])>o[1]+0.01)if(Math.min(a[1],b[1],c[1])>o[1])continue;
 const mnx=Math.min(a[0],b[0],c[0]),mxx=Math.max(a[0],b[0],c[0]),mnz=Math.min(a[2],b[2],c[2]),mxz=Math.max(a[2],b[2],c[2]);if(o[0]<mnx||o[0]>mxx||o[2]<mnz||o[2]>mxz)continue;
 const e1=sub(b,a),e2=sub(c,a),d=[0,-1,0],h=cross(d,e2),det=e1[0]*h[0]+e1[1]*h[1]+e1[2]*h[2];if(Math.abs(det)<1e-9)continue;const f=1/det,s=sub(o,a),u=f*(s[0]*h[0]+s[1]*h[1]+s[2]*h[2]);if(u<0||u>1)continue;
 const q=cross(s,e1),v=f*(d[0]*q[0]+d[1]*q[1]+d[2]*q[2]);if(v<0||u+v>1)continue;const tt=f*(e2[0]*q[0]+e2[1]*q[1]+e2[2]*q[2]);if(tt>0.02&&tt<best)best=tt;}return best;};
const pickArea=(list,n,minD,acc)=>{const tot=list.reduce((s,t)=>s+t.A,0),out=[];let tries=0;while(out.length<n&&tries<n*60){tries++;let r=rnd()*tot,t=list[0];for(const x of list){r-=x.A;if(r<=0){t=x;break;}}
 let u=rnd(),v=rnd();if(u+v>1){u=1-u;v=1-v;}const p=[0,1,2].map(k=>t.p[0][k]+(t.p[1][k]-t.p[0][k])*u+(t.p[2][k]-t.p[0][k])*v);if(out.some(o=>Math.hypot(o[0]-p[0],o[1]-p[1],o[2]-p[2])<minD))continue;const r2=acc(p,t);if(r2)out.push(r2);}return out;};
const f2=v=>+v.toFixed(2);
// R：山石的肩、顶
const R=pickArea(rock.filter(t=>t.n[1]>0.25&&t.c[1]>1.0),520,0.36,(p,t)=>{let hx=t.n[0],hz=t.n[2],hl=Math.hypot(hx,hz);if(hl<0.05){const a=rnd()*6.283;hx=Math.cos(a);hz=Math.sin(a);hl=1;}hx/=hl;hz/=hl;
 for(const off of[0.12,0.25,0.4]){const o=[p[0]+hx*off,p[1]+0.02,p[2]+hz*off],d=down(o);const len=Math.min(d,p[1]+0.05,1.2+rnd()*4.2);if(len>=0.7)return [f2(o[0]),f2(o[1]),f2(o[2]),f2(hx),f2(hz),f2(len)];}return null;});
// S：山石侧面的石缝
const S=pickArea(rock.filter(t=>Math.abs(t.n[1])<0.35&&t.c[1]>0.5&&t.c[1]<6.5),220,0.5,(p,t)=>{const hl=Math.hypot(t.n[0],t.n[2])||1;return [f2(p[0]),f2(p[1]),f2(p[2]),f2(t.n[0]/hl),f2(t.n[2]/hl)];});
// P：甬路、台基外沿
const pave=tris(/地面_pave/),ec=new Map();for(const t of pave)for(let k=0;k<3;k++){const a=t.p[k],b=t.p[(k+1)%3];const ka=a.map(f2).join(),kb=b.map(f2).join(),key=ka<kb?ka+'|'+kb:kb+'|'+ka;const e=ec.get(key);if(e)e.n++;else ec.set(key,{a,b,n:1});}
const P=[];for(const e of ec.values()){if(e.n!==1)continue;const dx=e.b[0]-e.a[0],dz=e.b[2]-e.a[2],L=Math.hypot(dx,dz);for(let s=0.3;s<L;s+=0.5+rnd()*0.7){if(rnd()<0.2)continue;P.push([f2(e.a[0]+dx*s/L),f2(e.a[2]+dz*s/L),f2(Math.atan2(dx,dz))]);}}
// 山石表面体素（0.1 m）
const VX=0.1,X0=-16,Y0=-2,Z0=-16,NX=320,NY=120,NZ=320,occ=new Uint8Array(NX*NY*NZ);
const vi=(x,y,z)=>{const i=Math.floor((x-X0)/VX),j=Math.floor((y-Y0)/VX),k=Math.floor((z-Z0)/VX);return i<0||j<0||k<0||i>=NX||j>=NY||k>=NZ?-1:(j*NZ+k)*NX+i;};
for(const t of rock){const [a,b,c]=t.p,e=Math.max(Math.hypot(...sub(a,b)),Math.hypot(...sub(b,c)),Math.hypot(...sub(c,a))),n=Math.max(1,Math.ceil(e/0.05));
 for(let i=0;i<=n;i++)for(let j=0;j<=n-i;j++){const u=i/n,w=j/n,q=[0,1,2].map(k=>a[k]*(1-u-w)+b[k]*u+c[k]*w);const id=vi(...q);if(id>=0)occ[id]=1;}}
const solid=(q)=>{const id=vi(...q);return id>=0&&occ[id]===1;};
const near=(q,r=0.12)=>{for(let dx=-r;dx<=r+1e-6;dx+=VX)for(let dy=-r;dy<=r+1e-6;dy+=VX)for(let dz=-r;dz<=r+1e-6;dz+=VX)if(solid([q[0]+dx,q[1]+dy,q[2]+dz]))return true;return false;};
const drape=(x,y,z,dx,dz,len)=>{let p=[x,y,z];const out=[...p.map(f2)];let tot=0,side=(rnd()-0.5)*0.06;
 while(tot<len&&p[1]>0.08){let q=[p[0]+dz*side,p[1]-0.2,p[2]-dx*side];side+=(rnd()-0.5)*0.03;side=Math.max(-0.06,Math.min(0.06,side));
  let k=0;while(k<10&&!near(q)){q=[q[0]-dx*0.05,q[1],q[2]-dz*0.05];k++;}if(k===10)q=[p[0],p[1]-0.2,p[2]];   // 靠不上石头就直垂
  k=0;while(k<30&&near(q,0.06)){q=[q[0]+dx*0.04,q[1],q[2]+dz*0.04];k++;}                                   // 别钻进石头
  tot+=Math.hypot(q[0]-p[0],q[1]-p[1],q[2]-p[2]);p=q;out.push(...p.map(f2));}
 return out.length>=9?[f2(dx),f2(dz),...out]:null;};
const D=[];for(const [x,y,z,dx,dz,len] of R){const d=drape(x,y,z,dx,dz,Math.min(y+0.1,len*1.15+rnd()*1.2));if(d)D.push(d);}
for(const [x,y,z,dx,dz] of S){const d=drape(x+dx*0.05,y,z+dz*0.05,dx,dz,0.4+rnd()*0.9);if(d)D.push(d);}
writeFileSync(new URL('../../../models/b/hw_vines.json',import.meta.url),JSON.stringify({H,R,S,P,D}));
console.log('R',R.length,'S',S.length,'P',P.length,'D',D.length,'pts',D.reduce((s,d)=>s+(d.length-2)/3,0));
