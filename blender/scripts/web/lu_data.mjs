// 园路 3D 化的取样：在网页里沿园路中线每 0.25 米取一排横断面，向下打射线到地形网格上取真实地面高（网格是 1 米格的折面，
// 和 height() 的光滑值有出入，路面要贴的是看得见的那张网格）；同时标出桥面（水上）、石磴（陡坡，另有台阶）、与其它路的岔口。
// 输出 blender/data/lu_<名>.json，给 blender/scripts/sites/paths_build.py 用。
// 用法：先在仓库根目录起个静态服务（如 npx http-server -p 8765），再
//   node blender/scripts/web/lu_data.mjs http://localhost:8765/index.html 0 zhou     # 0 = PATHS 里第几条；zhou = 输出名
// 依赖 playwright（chromium）。
import {createRequire} from 'module';import fs from 'fs';
const require=createRequire(import.meta.url);let pw;try{pw=require('playwright');}catch(e){pw=await import('/opt/node22/lib/node_modules/playwright/index.mjs');}
const [,,url,idxS,name]=process.argv;const IDX=+idxS;
const b=await pw.chromium.launch({args:['--use-angle=swiftshader','--enable-unsafe-swiftshader'],...(process.env.PW_CHROME?{executablePath:process.env.PW_CHROME}:{}),...(process.env.PW_PROXY?{proxy:JSON.parse(process.env.PW_PROXY)}:{})});
const p=await b.newPage({viewport:{width:320,height:180}});
if(process.env.PW_ROUTE){const R=JSON.parse(process.env.PW_ROUTE);await p.route(/cdn\.jsdelivr\.net\/npm\//,async r=>{const u=r.request().url();const m=u.match(/three@[^/]+\/(.*)$/);try{await r.fulfill({path:m?R.three+m[1]:R.eztree,contentType:'text/javascript'});}catch(e){r.abort();}});await p.route(/fonts\.(googleapis|gstatic)/,r=>r.abort());}
await p.goto(url);await p.waitForFunction(()=>window.__dgy,null,{timeout:900000});
const out=await p.evaluate((IDX)=>{const d=window.__dgy,T=d.THREE,P=d.PATHS[IDX],hw=P.w/2;
 const c=new T.CatmullRomCurve3(P.pts.map(q=>new T.Vector3(q[0],0,q[1])),false,'centripetal'),L=c.getLength(),n=Math.ceil(L/0.25),sp=c.getSpacedPoints(n);
 const ray=new T.Raycaster(),down=new T.Vector3(0,-1,0),gy=(x,z)=>{ray.set(new T.Vector3(x,80,z),down);const h=ray.intersectObject(d.terrainMesh,false)[0];return h?h.point.y:d.height(x,z);};
 const OFF=[];for(let k=-6;k<=6;k++)OFF.push(+(k*(hw+0.7)/6).toFixed(3));
 // 别的路的中线（取岔口）
 const others=[];d.PATHS.forEach((Q,j)=>{if(j===IDX)return;const cc=new T.CatmullRomCurve3(Q.pts.map(q=>new T.Vector3(q[0],0,q[1])),false,'centripetal');for(const v of cc.getSpacedPoints(Math.ceil(cc.getLength()/0.5)))others.push([v.x,v.z,Q.w/2]);});
 const hs=sp.map(v=>d.height(v.x,v.z)),ds=L/n;
 const rows=sp.map((v,i)=>{const a=sp[Math.max(0,i-1)],b2=sp[Math.min(n,i+1)];let tx=b2.x-a.x,tz=b2.z-a.z;const tl=Math.hypot(tx,tz)||1;tx/=tl;tz/=tl;
  const nx=-tz,nz=tx;const y=OFF.map(o=>+gy(v.x+nx*o,v.z+nz*o).toFixed(3));
  const i0=Math.max(0,i-8),i1=Math.min(n,i+8);const steep=hs[i]>0.3&&Math.abs(hs[i1]-hs[i0])/((i1-i0)*ds)>0.2;const wet=hs[i]<0.3;
  // 岔口：左右两侧各看有没有别的路中线贴过来
  let jl=0,jr=0;for(const [ox,oz,ow] of others){const dx=ox-v.x,dz=oz-v.z,along=dx*tx+dz*tz,side=dx*nx+dz*nz;if(Math.abs(along)<ow+0.6&&Math.abs(side)<hw+ow+1.2){if(side<0)jl=1;else jr=1;}}
  return {x:+v.x.toFixed(3),z:+v.z.toFixed(3),tx:+tx.toFixed(4),tz:+tz.toFixed(4),y,steep:+steep,wet:+wet,jl,jr};});
 return {name:IDX,w:P.w,off:OFF,rows};},IDX);
fs.mkdirSync(new URL('../../data/',import.meta.url),{recursive:true});
const f=new URL(`../../data/lu_${name}.json`,import.meta.url);fs.writeFileSync(f,JSON.stringify(out));
console.log('rows',out.rows.length,'steep',out.rows.filter(r=>r.steep).length,'wet',out.rows.filter(r=>r.wet).length,'junction',out.rows.filter(r=>r.jl||r.jr).length,'->',f.pathname);
await b.close();
