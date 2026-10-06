// 园路 3D 化的取样：在网页里沿每条园路中线每 0.25 米取一排横断面，向下打射线到地形网格上取真实地面高（网格是 1 米格的折面，
// 和 height() 的光滑值有出入，路面要贴的是看得见的那张网格）。每行再标出：
//   skip —— 桥上（BRIDGES 的桥身范围）或石磴（与 buildPath 里 stairs() 完全同一算法）：这里另有桥、台阶，路面不建；
//   inn  —— 落在别的路的路面里（那条路在这里是“穿过”的，或两条都到头时编号小的那条优先）：不建，免得两层路面叠在一起；
//   jl/jr —— 左/右侧有别的路接进来：这一侧不立路牙、不镶砖，路面铺满到边，好和支路接上。
// 输出 blender/data/lu_<名>.json（名取 PATHS 里的 lu 字段），给 blender/scripts/sites/paths_build.py 用。
// 用法：先在仓库根目录起个静态服务（如 npx http-server -p 8765），再
//   node blender/scripts/web/lu_data.mjs http://localhost:8765/index.html            # 所有带 lu 的路
//   node blender/scripts/web/lu_data.mjs http://localhost:8765/index.html zhou p3    # 只取这几条
// 依赖 playwright（chromium）。
import {createRequire} from 'module';import fs from 'fs';
const require=createRequire(import.meta.url);let pw;try{pw=require('playwright');}catch(e){pw=await import('/opt/node22/lib/node_modules/playwright/index.mjs');}
const [,,url,...only]=process.argv;
const b=await pw.chromium.launch({args:['--use-angle=swiftshader','--enable-unsafe-swiftshader'],...(process.env.PW_CHROME?{executablePath:process.env.PW_CHROME}:{}),...(process.env.PW_PROXY?{proxy:JSON.parse(process.env.PW_PROXY)}:{})});
const p=await b.newPage({viewport:{width:320,height:180}});
if(process.env.PW_ROUTE){const R=JSON.parse(process.env.PW_ROUTE);await p.route(/cdn\.jsdelivr\.net\/npm\//,async r=>{const u=r.request().url();const m=u.match(/three@[^/]+\/(.*)$/);try{await r.fulfill({path:m?R.three+m[1]:R.eztree,contentType:'text/javascript'});}catch(e){r.abort();}});await p.route(/fonts\.(googleapis|gstatic)/,r=>r.abort());}
await p.goto(url);await p.waitForFunction(()=>window.__dgy,null,{timeout:900000});
const outs=await p.evaluate((only)=>{const d=window.__dgy,T=d.THREE,PS=d.LU_PATHS;   // 所有带 lu 的路（PATHS 里的和各院自己画的）
 // 地形网格是 PlaneGeometry(340,410,340,410)：1 米一格，x 从 -170、z 从 -200 起；每格两个三角 (a,b,d)(b,c,d)。直接按三角插值，不用射线（射线没有加速结构，几千次就要几十分钟）
 const PA=d.terrainMesh.geometry.attributes.position,NX=341,gy=(x,z)=>{const fx=x+170,fz=z+200,c=Math.floor(fx),r=Math.floor(fz);if(c<0||r<0||c>=340||r>=410)return d.height(x,z);
  const u=fx-c,v=fz-r,Y=(cc,rr)=>PA.getY(cc+NX*rr);const a=Y(c,r),b=Y(c,r+1),cc=Y(c+1,r+1),dd=Y(c+1,r);
  return u+v<=1?a+(dd-a)*u+(b-a)*v:cc+(b-cc)*(1-u)+(dd-cc)*(1-v);};
 const curve=P=>new T.CatmullRomCurve3((P.tail?P.pts.concat(P.tail):P.pts).map(q=>new T.Vector3(q[0],0,q[1])),false,'centripetal');
 // 每条路的中线（0.25 米一点），用来判断“落在别的路面里”和“有路接进来”
 const lines=PS.map(P=>{if(!P.lu)return null;const c=curve(P);return c.getSpacedPoints(Math.ceil(c.getLength()/0.25)).map(v=>[v.x,v.z]);});
 const near=(L,x,z)=>{let best=1e9,bi=0;for(let i=0;i<L.length;i++){const dd=(L[i][0]-x)**2+(L[i][1]-z)**2;if(dd<best){best=dd;bi=i;}}return [Math.sqrt(best),bi];};
 const res=[];
 PS.forEach((P,IDX)=>{if(!P.lu||(only.length&&!only.includes(P.lu)))return;const hw=P.w/2;
  const c=curve(P),L=c.getLength(),n=Math.ceil(L/0.25),sp=c.getSpacedPoints(n);
  // 石磴范围：照抄 buildPath 的算法
  // 石磴按原路（不含 tail）算，和 buildPath 一样；记下台阶段上的点，行落在这些点 0.3 米内才跳过
  const c0=new T.CatmullRomCurve3(P.pts.map(q=>new T.Vector3(q[0],0,q[1])),false,'centripetal'),L0=c0.getLength();
  const S2=c0.getSpacedPoints(Math.max(8,Math.ceil(L0/0.2))).map(v=>[v.x,v.z]),m=S2.length,ds=L0/(m-1),hs=S2.map(q=>d.height(q[0],q[1]));
  const steep=hs.map((h,i)=>{const a=Math.max(0,i-5),b2=Math.min(m-1,i+5);return h>0.3&&Math.abs(hs[b2]-hs[a])/((b2-a)*ds)>0.2;});
  const stairP=[];for(let i=0;i<m;){if(!steep[i]){i++;continue;}let j=i;while(j<m&&steep[j])j++;if((j-i)*ds>=2)for(let k=i;k<j;k++)stairP.push(S2[k]);i=j;}
  const OFF=[];for(let k=-6;k<=6;k++)OFF.push(+(k*(hw+0.7)/6).toFixed(3));
  const rows=sp.map((v,i)=>{const a=sp[Math.max(0,i-1)],b2=sp[Math.min(n,i+1)];let tx=b2.x-a.x,tz=b2.z-a.z;const tl=Math.hypot(tx,tz)||1;tx/=tl;tz/=tl;const nx=-tz,nz=tx,s=i*L/n;
   let skip=stairP.some(q=>(q[0]-v.x)**2+(q[1]-v.z)**2<0.09)?1:0;
   for(const B of d.BRIDGES){const dx=v.x-B.x,dz=v.z-B.z,al=dx*Math.sin(B.ry)+dz*Math.cos(B.ry),sd=dx*Math.cos(B.ry)-dz*Math.sin(B.ry);if(Math.abs(al)<B.L/2-0.5&&Math.abs(sd)<hw+1)skip=1;}
   let inn=0,jl=0,jr=0;
   PS.forEach((Q,j)=>{if(j===IDX||!lines[j])return;const Lq=lines[j],hq=Q.w/2,[dist,bi]=near(Lq,v.x,v.z),through=bi>0&&bi<Lq.length-1;
    if(dist<hq+0.02&&(through||j<IDX))inn=1;
    // 有别的路从侧面接进来：它的中线贴到本路边上
    for(const q of Lq){const dx=q[0]-v.x,dz=q[1]-v.z,al=dx*tx+dz*tz,sd=dx*nx+dz*nz;if(Math.abs(al)<hq+0.3&&Math.abs(sd)<hw+0.6&&Math.abs(sd)>0.2){if(sd<0)jl=1;else jr=1;}}});
   const y=OFF.map(o=>+gy(v.x+nx*o,v.z+nz*o).toFixed(3));
   return {x:+v.x.toFixed(3),z:+v.z.toFixed(3),tx:+tx.toFixed(4),tz:+tz.toFixed(4),y,skip,inn,jl,jr};});
  res.push({lu:P.lu,idx:IDX,w:P.w,off:OFF,rows});});
 return res;},only);
fs.mkdirSync(new URL('../../data/',import.meta.url),{recursive:true});
for(const out of outs){const f=new URL(`../../data/lu_${out.lu}.json`,import.meta.url);fs.writeFileSync(f,JSON.stringify(out));
 const R=out.rows;console.log(out.lu,'rows',R.length,'skip',R.filter(r=>r.skip).length,'inn',R.filter(r=>r.inn).length,'junction',R.filter(r=>r.jl||r.jr).length);}
await b.close();
