import { partitionOcclusionSurface } from './occlusion-surface-patches.mjs';

// Full-mesh conservative coverage. At run time each real triangle contributes
// only its facing/clip decision and three signed topology edges. Shared edges
// cancel, so only the true projected outline is rasterized. A grid cell touched
// by that outline remains unknown; all other nonzero-winding cells are entirely
// covered. Holes survive even when smaller than one grid cell.
function opaque(T,m){
  if(!m||m.visible===false||m.transparent||m.opacity!==1||m.alphaTest>0||m.alphaMap||m.alphaHash||m.alphaToCoverage||m.wireframe||
    m.depthWrite===false||m.depthTest===false||m.colorWrite===false||m.depthFunc!==T.LessEqualDepth||m.blending!==T.NormalBlending||
    m.displacementMap||m.transmission>0||m.polygonOffset||m.clippingPlanes?.length||m.isShaderMaterial||m.isRawShaderMaterial)return false;
  if(!(m.isMeshBasicMaterial||m.isMeshLambertMaterial||m.isMeshPhongMaterial||m.isMeshStandardMaterial||m.isMeshNormalMaterial||m.isMeshToonMaterial))return false;
  if(!m.userData?.dgyOcclusionStaticSurface&&(m.onBeforeCompile!==T.Material.prototype.onBeforeCompile||m.userData?.shadowDynamic))return false;
  return m.side===T.FrontSide||m.side===T.BackSide||m.side===T.DoubleSide;
}
function staticMesh(T,m){return m?.isMesh&&!m.isSkinnedMesh&&!m.isInstancedMesh&&!m.isBatchedMesh&&!m.geometry?.isInstancedBufferGeometry&&
  !m.geometry?.morphAttributes?.position?.length&&!m.geometry?.morphAttributes?.normal?.length&&!m.animations?.length&&!m.userData?.dynamic&&m.onBeforeRender===T.Object3D.prototype.onBeforeRender;}
const eq16=(a,b)=>{for(let i=0;i<16;i++)if(a[i]!==b[i])return false;return true;};
const clamp=(x,a,b)=>Math.max(a,Math.min(b,x));
const EDGE=1e-7,DEPTH=2e-5;

// Allocate preparation by local building and complete material family. Splitting
// a large rock into several spatial meshes must not turn it into many unrelated
// candidates, and hi/lo/HLOD copies must not each claim a first-place budget.
// This changes selection only, never the conservative coverage proof.
export function selectOcclusionPreparationSources(sources,{maxBuildTriangles=2000000,primaryBudgetFraction=.8}={}){
  const regions=new Map(),families=new Map(),selected=[],chosen=new Set();let total=0;
  for(const source of sources){
    const region=source.region??'default',variant=source.variant??'base',family=source.family??source.mesh?.id??source.name;
    const key=region+'\u0000'+variant+'\u0000'+family;let entry=families.get(key);
    if(!entry){entry={region,variant,family,sources:[],count:0,surface:0,priority:0};families.set(key,entry);
      let bucket=regions.get(region);if(!bucket){bucket={region,primary:[],secondary:[],selectedTriangles:0,selectedMeshes:0};regions.set(region,bucket);}
      (variant==='hi'||variant==='base'?bucket.primary:bucket.secondary).push(entry);}
    entry.sources.push(source);entry.count+=source.count;entry.surface+=source.surface??source.priority*Math.sqrt(source.count);
  }
  for(const family of families.values())family.priority=family.surface/Math.sqrt(family.count);
  const buckets=[...regions.values()].sort((a,b)=>String(a.region).localeCompare(String(b.region)));
  for(const bucket of buckets){bucket.primary.sort((a,b)=>b.priority-a.priority);bucket.secondary.sort((a,b)=>{
    const tier=v=>v==='hlod'?0:v==='lo'?1:2;return tier(a.variant)-tier(b.variant)||b.priority-a.priority;});}
  function rounds(kind,limit){
    let pending=true;for(let round=0;pending;round++){pending=false;
      for(const bucket of buckets){const family=bucket[kind][round];if(!family)continue;pending=true;
        if(chosen.has(family)||total+family.count>limit)continue;
        chosen.add(family);total+=family.count;selected.push(...family.sources);bucket.selectedTriangles+=family.count;bucket.selectedMeshes+=family.sources.length;
      }
    }
  }
  rounds('primary',maxBuildTriangles*clamp(primaryBudgetFraction,0,1));
  rounds('secondary',maxBuildTriangles);rounds('primary',maxBuildTriangles);
  const stats={budgetTriangles:maxBuildTriangles,availableMeshes:sources.length,availableTriangles:sources.reduce((sum,r)=>sum+r.count,0),
    preparedMeshes:selected.length,preparedTriangles:total,regions:buckets.length,coveredRegions:buckets.filter(b=>b.selectedMeshes).length,
    primaryTriangles:selected.filter(r=>r.variant==='hi'||r.variant==='base'||!r.variant).reduce((sum,r)=>sum+r.count,0),
    secondaryTriangles:selected.filter(r=>r.variant&&r.variant!=='hi'&&r.variant!=='base').reduce((sum,r)=>sum+r.count,0),
    perRegion:buckets.map(b=>({region:b.region,availableTriangles:[...b.primary,...b.secondary].reduce((sum,f)=>sum+f.count,0),
      preparedTriangles:b.selectedTriangles,preparedMeshes:b.selectedMeshes,
      families:[...b.primary,...b.secondary].filter(f=>chosen.has(f)).map(f=>({family:f.family,variant:f.variant,triangles:f.count,meshes:f.sources.length}))}))};
  return {selected,stats};
}

// Callers can supply semantic region names (e.g. building ids) for diagnostics.
// The default also handles generic scenes: use the branch immediately below the
// sources' common ancestor, with a spatial-cell fallback for direct root meshes.
function preparationRegions(sources){
  if(!sources.length)return ()=>null;
  const ancestors=[];for(let p=sources[0].parent;p;p=p.parent)ancestors.push(p);
  let common=null;for(const p of ancestors){if(sources.every(mesh=>{for(let q=mesh.parent;q;q=q.parent)if(q===p)return true;return false;})){common=p;break;}}
  return mesh=>{let branch=mesh;while(branch.parent&&branch.parent!==common)branch=branch.parent;let variant='base';
    for(let p=mesh;p&&p!==common;p=p.parent){if(p.name==='hi')variant='hi';else if(p.name==='hlod')variant='hlod';else if(p.name==='lo'||p.name==='lo-detail')variant='lo';}
    return {region:branch===mesh?null:branch.uuid,variant};};
}

// splitBig divides a continuous wall or rock only to improve render culling.
// Its artificial cuts are not holes. Weld compatible parts into a virtual
// occlusion record while leaving every product mesh and material untouched.
function mergeCompatibleSources(sources,maxTriangles){
  const groups=new Map(),records=[];
  for(const source of sources){
    const {mesh}=source;
    if(Array.isArray(mesh.material)){records.push({...source,parts:[source]});continue;}
    const key=source.region+'\u0000'+source.variant+'\u0000'+source.family+'\u0000'+mesh.material.uuid+'\u0000'+mesh.matrixWorld.elements.join(',');
    let group=groups.get(key);if(!group){group=[];groups.set(key,group);}group.push(source);
  }
  for(const parts of groups.values()){
    const count=parts.reduce((sum,p)=>sum+p.count,0);
    if(count>maxTriangles){for(const part of parts)records.push({...part,parts:[part]});continue;}
    const bounds=parts[0].bounds.clone();for(let i=1;i<parts.length;i++)bounds.union(parts[i].bounds);
    records.push({...parts[0],count,bounds,parts});
  }
  return records;
}

function* prepareConservativeOcclusion({THREE:T,occluders=[],width=64,height=36,maxDistance=120,
  maxTrianglesPerMesh=150000,maxBuildTriangles=2000000,maxFrameTriangles=200000,maxMeshes=12,
  maxPatches,maxProjectedEdges=40000,maxRasterCells=120000,getObjectBounds=null,isOccluderCurrent=null,
  getPreparationGroup=null,primaryBudgetFraction=.8,mergeSources=true,
  maxUpdateMs=3,maxRasterSourceTriangles=8000,maxRowEvents=2048,
  surfacePatchSize=2,surfacePatchTriangles=2048,partitionLargeSources=true,now=()=>performance.now()}={}){
  if(!T)throw new Error('THREE is required');width=clamp(width|0,4,512);height=clamp(height|0,4,288);
  if(maxPatches!==undefined)maxMeshes=Math.min(maxMeshes,maxPatches);
  const size=width*height,depth=new Float64Array(size),boundary=new Uint8Array(size),rows=Array.from({length:height},()=>[]),rowWinding=new Int32Array(height);
  const rowPools=Array.from({length:height},()=>[]);
  const records=[],byObject=new WeakMap(),candidates=[],previous=[];
  const vp=new T.Matrix4(),frustum=new T.Frustum(),eye=new T.Vector3(),tmp=new T.Vector3(),pv=new Float64Array(3);
  const cw=new Float64Array(16),cp=new Float64Array(16),query={};let camera=null,enabled=true,ready=false,layerMask=0,deadline=Infinity;
  const stats={meshes:0,sourceTriangles:0,rejectedMeshes:0,buildMs:0,updateMs:0,reused:false,candidateMeshes:0,
    projectedTriangles:0,rasterTriangles:0,rasterCells:0,coveredCells:0,boundaryEdges:0,budgetSkipped:0,
    rasterPatches:0,rasterMeshes:0,queries:0,culled:0,staleQueries:0,coverageRevision:0,
    budgetMs:maxUpdateMs,budgetExhausted:false,complexitySkipped:0,surfacePatches:0,partitionedSources:0};
  const start=performance.now(),metadata=[],a=new T.Vector3(),b=new T.Vector3(),c=new T.Vector3(),n=new T.Vector3(),ab=new T.Vector3();
  const sources=[...new Set(occluders)];let inspected=0,prepared=0,totalWork=0;
  const inferGroup=preparationRegions(sources);
  for(const mesh of sources){
    yield {done:inspected++,total:Math.max(1,sources.length),phase:'inspect'};
    const geometry=mesh.geometry,p=geometry?.attributes?.position,index=geometry?.index;
    if(!staticMesh(T,mesh)||!p||p.itemSize<3||p.isGLBufferAttribute){stats.rejectedMeshes++;continue;}
    const materials=Array.isArray(mesh.material)?mesh.material:[mesh.material];
    if(!materials.some(m=>opaque(T,m))){stats.rejectedMeshes++;continue;}
    const total=index?index.count:p.count,from=geometry.drawRange.start,to=Math.min(total,from+geometry.drawRange.count),count=(to-from)/3;
    if(!Number.isInteger(count)||from%3||count>maxTrianglesPerMesh||!count){stats.rejectedMeshes++;continue;}
    mesh.updateWorldMatrix(true,false);geometry.computeBoundingBox();
    const bounds=geometry.boundingBox.clone().applyMatrix4(mesh.matrixWorld).expandByScalar(1e-4);bounds.getSize(tmp);
    // Broad structural surfaces earn the finite preprocessing budget first.
    // This is selection only: skipped meshes never contribute occlusion.
    const surface=Math.max(tmp.x*tmp.y,tmp.x*tmp.z,tmp.y*tmp.z);
    const group=getPreparationGroup?.(mesh)||inferGroup(mesh)||{};bounds.getCenter(a);
    metadata.push({mesh,geometry,p,index,from,to,count,bounds,surface,priority:surface/Math.sqrt(count),
      region:group.region??(Math.floor(a.x/40)+','+Math.floor(a.z/40)),variant:group.variant??'base',
      family:group.family??materials.map(m=>m.name||m.type).join('|')});
  }
  const preparation=selectOcclusionPreparationSources(metadata,{maxBuildTriangles,primaryBudgetFraction});stats.preparation=preparation.stats;
  stats.rejectedMeshes+=metadata.length-preparation.selected.length;totalWork=preparation.stats.preparedTriangles;
  // Keep the detailed audit available without copying hundreds of mesh records
  // whenever a frame's timing counters are serialized.
  Object.defineProperty(stats,'preparedSources',{value:preparation.selected.map(r=>({objectId:r.mesh.id,name:r.mesh.name,region:r.region,variant:r.variant,family:r.family,triangles:r.count}))});
  const combined=mergeSources?mergeCompatibleSources(preparation.selected,Math.min(maxFrameTriangles,maxRasterSourceTriangles)):preparation.selected.map(source=>({...source,parts:[source]}));
  stats.mergedSources=preparation.selected.length-combined.length;
  for(const r of combined){
    yield {done:prepared,total:Math.max(1,totalWork),phase:'build'};
    const {mesh,count}=r;
    const materials=Array.isArray(mesh.material)?mesh.material:[mesh.material];
    const vertexMap=new Map(),vertices=[],edges=[],edgeMap=new Map();
    const triangles=new Uint32Array(count*3),edgeIds=new Int32Array(count*3),planes=new Float64Array(count*4),materialIds=new Int32Array(count).fill(-1);
    const vertexLimit=r.parts.reduce((sum,part)=>sum+part.p.count,0)+1;
    const edge=(a,b)=>{const lo=Math.min(a,b),hi=Math.max(a,b),key=lo*vertexLimit+hi;let id=edgeMap.get(key);
      if(id===undefined){id=edges.length/2;edges.push(lo,hi);edgeMap.set(key,id);}return(id+1)*(a<b?1:-1);};
    let triangleOffset=0;
    for(const part of r.parts){
      const {geometry,p,index,from,to}=part;
      const groups=Array.isArray(mesh.material)?geometry.groups:[{start:0,count:index?index.count:p.count,materialIndex:0}];
      const vertexIds=new Int32Array(p.count).fill(-1);
      const vertex=i=>{if(vertexIds[i]>=0)return vertexIds[i];const x=p.getX(i),y=p.getY(i),z=p.getZ(i),key=x+','+y+','+z;let id=vertexMap.get(key);
        if(id===undefined){a.set(x,y,z).applyMatrix4(part.mesh.matrixWorld);id=vertices.length/3;vertices.push(a.x,a.y,a.z);vertexMap.set(key,id);}vertexIds[i]=id;return id;};
    for(const group of groups){
      if(!opaque(T,materials[group.materialIndex]))continue;
      const begin=Math.max(from,group.start),end=Math.min(to,group.start+group.count);if(begin%3||end%3)continue;
      for(let i=begin;i+2<end;i+=3){
        if((i-begin)%3072===0)yield {done:prepared+triangleOffset+(i-from)/3,total:Math.max(1,totalWork),phase:'build'};
        const t=triangleOffset+(i-from)/3,v0=vertex(index?index.getX(i):i),v1=vertex(index?index.getX(i+1):i+1),v2=vertex(index?index.getX(i+2):i+2);
        a.fromArray(vertices,v0*3);b.fromArray(vertices,v1*3);c.fromArray(vertices,v2*3);n.subVectors(b,a).cross(ab.subVectors(c,a));
        const len=n.length();if(!(len>1e-12)||!Number.isFinite(len))continue;n.multiplyScalar(1/len);
        planes[t*4]=n.x;planes[t*4+1]=n.y;planes[t*4+2]=n.z;planes[t*4+3]=n.dot(a);
        triangles[t*3]=v0;triangles[t*3+1]=v1;triangles[t*3+2]=v2;
        edgeIds[t*3]=edge(v0,v1);edgeIds[t*3+1]=edge(v1,v2);edgeIds[t*3+2]=edge(v2,v0);materialIds[t]=group.materialIndex;
      }
    }
      Object.assign(part,{pVersion:p.version??p.data?.version,iVersion:index?.version,drawStart:geometry.drawRange.start,drawCount:geometry.drawRange.count,
        groups:JSON.stringify(geometry.groups),matrix:part.mesh.matrixWorld.elements.slice()});
      triangleOffset+=part.count;
    }
    Object.assign(r,{vertices:new Float64Array(vertices),screen:new Float64Array(vertices.length),valid:new Uint8Array(vertices.length/3),
      edges:new Uint32Array(edges),balance:new Int32Array(edges.length/2),backBalance:new Int32Array(edges.length/2),triangles,edgeIds,planes,materialIds,
      flip:mesh.matrixWorld.determinant()<0?-1:1,state:'',rank:0});
    if(partitionLargeSources&&r.count>maxRasterSourceTriangles&&surfacePatchSize>0&&surfacePatchTriangles>0){
      const work=partitionOcclusionSurface({THREE:T,record:r,cellSize:surfacePatchSize,maxTriangles:Math.min(surfacePatchTriangles,maxRasterSourceTriangles)});let step;
      do{step=work.next();if(!step.done)yield {done:prepared+count,total:Math.max(1,totalWork),phase:'build'};}while(!step.done);
      records.push(...step.value);stats.surfacePatches+=step.value.length;stats.partitionedSources++;
      // Querying a source itself still uses its complete original bounds, not
      // one arbitrary spatial patch. Keep only its live certificate, not all
      // duplicated topology arrays after the bounded records are prepared.
      const certificate={mesh:r.mesh,parts:r.parts,bounds:r.bounds};for(const part of r.parts)byObject.set(part.mesh,certificate);
    }else{records.push(r);for(const part of r.parts)byObject.set(part.mesh,r);}
    stats.sourceTriangles+=count;
    prepared+=count;
  }
  yield {done:totalWork,total:totalWork,phase:'build'};
  stats.meshes=records.length;stats.buildMs=performance.now()-start;depth.fill(Infinity);
  function invalidateCoverage(){ready=false;stats.coverageRevision++;}
  function outOfTime(){if(now()<deadline)return false;stats.budgetExhausted=true;return true;}
  function clearRasterStats(){for(const key of ['projectedTriangles','rasterTriangles','rasterCells','coveredCells','boundaryEdges','budgetSkipped','rasterPatches','rasterMeshes'])stats[key]=0;}
  function sourceRejection(part,view,expectedMaterial){
    const {mesh,geometry,p,index}=part;if(isOccluderCurrent&&isOccluderCurrent(mesh)!==true)return 'registry';
    if(mesh.geometry!==geometry)return 'geometry';
    if(geometry.attributes.position!==p)return 'position-attribute';
    if(geometry.index!==index)return 'index-attribute';
    if((p.version??p.data?.version)!==part.pVersion)return 'position-version';
    if(index?.version!==part.iVersion)return 'index-version';
    if(geometry.drawRange.start!==part.drawStart||geometry.drawRange.count!==part.drawCount)return 'draw-range';
    if(!eq16(mesh.matrixWorld.elements,part.matrix))return 'world-matrix';
    if(!mesh.layers.test(view.layers))return 'layers';
    if(!staticMesh(T,mesh))return 'dynamic';
    for(let node=mesh;node;node=node.parent){if(!node.visible)return 'hidden';if(node.animations?.length||node.userData?.dynamic)return 'dynamic-ancestor';}
    if(Array.isArray(mesh.material)&&JSON.stringify(geometry.groups)!==part.groups)return 'material-groups';
    if(expectedMaterial&&mesh.material!==expectedMaterial)return 'split-material';
    return null;
  }
  function validRecord(r,view,cache=null){
    // Hundreds of original-triangle patches can share one source certificate.
    // Recheck it on EVERY update, once per live source, before reusing its
    // material decision for sibling patches in that same synchronous update.
    const cached=cache?.get(r.parts);if(cached){if(cached.valid)Object.assign(r,cached.state);return cached.valid;}
    for(const part of r.parts)if(sourceRejection(part,view,r.parts.length>1?r.mesh.material:null)){cache?.set(r.parts,{valid:false});return false;}
    const {mesh}=r;
    r.materials=Array.isArray(mesh.material)?mesh.material:[mesh.material];r.sides??=[];r.sides.length=r.materials.length;let state='',any=false;
    for(let i=0;i<r.materials.length;i++){const m=r.materials[i],ok=opaque(T,m);r.sides[i]=ok?m.side:-1;state+=ok?'_'+m.side:'_x';any||=ok;}r.state=state;
    cache?.set(r.parts,{valid:any,state:{materials:r.materials,sides:r.sides,state:r.state}});return any;
  }
  function project(x,y,z,out,offset=0){
    const e=vp.elements,w=e[3]*x+e[7]*y+e[11]*z+e[15],cz=e[2]*x+e[6]*y+e[10]*z+e[14];
    if(!(w>1e-7)||cz<=-w+1e-6||cz>=w-1e-6)return false;
    const sx=((e[0]*x+e[4]*y+e[8]*z+e[12])/w+1)*width*.5,sy=((e[1]*x+e[5]*y+e[9]*z+e[13])/w+1)*height*.5;
    if(!Number.isFinite(sx)||!Number.isFinite(sy))return false;out[offset]=sx;out[offset+1]=sy;out[offset+2]=cz/w;return true;
  }
  function block(x0,y0,x1,y1){
    const minX=Math.min(x0,x1),maxX=Math.max(x0,x1),dx=x1-x0;
    if(maxX< -EDGE||minX>width+EDGE||Math.max(y0,y1)< -EDGE||Math.min(y0,y1)>height+EDGE)return;
    for(let x=clamp(Math.floor(minX-EDGE),0,width-1),last=clamp(Math.floor(maxX+EDGE),0,width-1);x<=last;x++){
      let lo,hi;if(Math.abs(dx)<1e-14){lo=Math.min(y0,y1);hi=Math.max(y0,y1);}
      else{const t0=clamp((x-EDGE-x0)/dx,0,1),t1=clamp((x+1+EDGE-x0)/dx,0,1),a=y0+(y1-y0)*t0,b=y0+(y1-y0)*t1;lo=Math.min(a,b);hi=Math.max(a,b);}
      for(let y=Math.max(0,Math.floor(lo-EDGE)),last=Math.min(height-1,Math.floor(hi+EDGE));y<=last;y++)boundary[y*width+x]=1;
    }
  }
  function raster(r){
    const {vertices,screen,valid,balance,backBalance,triangles,edgeIds,planes,materialIds,sides}=r;
    valid.fill(0);balance.fill(0);backBalance.fill(0);let frontFar=-Infinity,backFar=-Infinity,frontAccepted=0,backAccepted=0;
    // Prove each facing subset separately. From inside caves, most of the real
    // visible rock can be back-facing even if a small part is front-facing.
    // Mixing both subsets adds unnecessary fold boundaries; dropping either
    // loses valid coverage. Independent complete cell covers can safely union.
    for(let t=0;t<r.count;t++){
      // A partial triangle set must never contribute a cancelled outline.
      if((t&127)===0&&outOfTime()){stats.projectedTriangles+=t;return;}
      const side=sides[materialIds[t]];if(side===undefined||side<0)continue;
      const at=t*4,d=planes[at]*eye.x+planes[at+1]*eye.y+planes[at+2]*eye.z-planes[at+3];
      const sign=d>1e-7?1:d< -1e-7?-1:0;if(!sign||(side===T.FrontSide&&sign*r.flip<0)||(side===T.BackSide&&sign*r.flip>0))continue;
      let ok=true;
      for(let k=0;k<3;k++){const v=triangles[t*3+k],at=v*3;if(!valid[v])valid[v]=project(vertices[at],vertices[at+1],vertices[at+2],screen,at)?1:2;if(valid[v]!==1)ok=false;}
      if(!ok)continue;const back=side===T.DoubleSide&&sign<0,target=back?backBalance:balance;let far=-Infinity;
      for(let k=0;k<3;k++){const edge=edgeIds[t*3+k];target[Math.abs(edge)-1]+=(edge>0?sign:-sign);far=Math.max(far,screen[triangles[t*3+k]*3+2]);}
      if(back){backAccepted++;backFar=Math.max(backFar,far);}else{frontAccepted++;frontFar=Math.max(frontFar,far);}
    }
    stats.projectedTriangles+=r.count;
    if(frontAccepted)rasterSubset(r,balance,frontFar,frontAccepted);
    if(backAccepted&&!stats.budgetExhausted)rasterSubset(r,backBalance,backFar,backAccepted);
  }
  function rasterSubset(r,balance,far,accepted){
    const {screen}=r;
    let edgeCount=0;for(let i=0;i<balance.length;i++)if(balance[i])edgeCount++;
    if(stats.boundaryEdges+edgeCount>maxProjectedEdges){stats.budgetSkipped++;return;}
    boundary.fill(0);rowWinding.fill(0);for(const row of rows)row.length=0;
    for(let i=0;i<balance.length;i++){
      if((i&15)===0&&outOfTime())return;
      const count=balance[i];if(!count)continue;const a=r.edges[i*2]*3,b=r.edges[i*2+1]*3,x0=screen[a],y0=screen[a+1],x1=screen[b],y1=screen[b+1];block(x0,y0,x1,y1);
      if(y0===y1||Math.min(x0,x1)>width-.5)continue;const low=Math.min(y0,y1),high=Math.max(y0,y1),sign=(y1>y0?1:-1)*count;
      for(let y=Math.max(0,Math.ceil(low-.5)),end=Math.min(height-1,Math.ceil(high-.5)-1);y<=end;y++){
        const x=x0+(x1-x0)*(y+.5-y0)/(y1-y0);
        // Crossings left of the first sample only set its initial winding;
        // crossings beyond the last sample cannot affect any screen cell.
        // The exact edge still marks every cell it touches as unknown above.
        if(x<=.5){rowWinding[y]+=sign;continue;}if(x>width-.5)continue;
        const row=rows[y];if(row.length>=maxRowEvents){stats.budgetSkipped++;return;}
        const pool=rowPools[y],event=pool[row.length]??=([]);event[0]=x;event[1]=sign;row.push(event);
      }
    }
    // All real edges have now been processed. Each completed row is an
    // independent full-cell proof; later timeout leaves other rows unknown.
    for(let y=0;y<height;y++){if(outOfTime())return;const row=rows[y];row.sort((a,b)=>a[0]-b[0]);if(outOfTime())return;let winding=rowWinding[y],j=0;
      for(let x=0;x<width;x++){while(j<row.length&&row[j][0]<=x+.5){winding+=row[j][1];j++;}const at=y*width+x;if(winding!==0&&!boundary[at])depth[at]=Math.min(depth[at],far+DEPTH);}}
    stats.boundaryEdges+=edgeCount;stats.rasterTriangles+=accepted;stats.rasterPatches++;stats.rasterCells+=size;
  }
  function update(view){
    const start=now();deadline=start+Math.max(0,maxUpdateMs);stats.queries=stats.culled=stats.staleQueries=0;stats.reused=false;stats.budgetExhausted=false;stats.complexitySkipped=0;
    if(!enabled||!view?.isPerspectiveCamera||view.isArrayCamera||view.coordinateSystem!==T.WebGLCoordinateSystem){if(ready)invalidateCoverage();stats.updateMs=now()-start;return stats;}
    view.updateMatrixWorld();let same=ready&&view===camera&&eq16(view.matrixWorld.elements,cw)&&eq16(view.projectionMatrix.elements,cp)&&view.layers.mask===layerMask;
    camera=view;eye.setFromMatrixPosition(view.matrixWorld);vp.multiplyMatrices(view.projectionMatrix,view.matrixWorldInverse);frustum.setFromProjectionMatrix(vp);candidates.length=0;
    const validationCache=new Map();
    for(let i=0;i<records.length;i++){if((i&31)===0&&outOfTime()){invalidateCoverage();depth.fill(Infinity);clearRasterStats();stats.candidateMeshes=0;stats.updateMs=now()-start;return stats;}
      const r=records[i],d=r.bounds.distanceToPoint(eye);if(d>maxDistance||!frustum.intersectsBox(r.bounds))continue;
      // Large audited surfaces are normally partitioned into exact original
      // triangle patches during preparation. Explicit limits may still leave
      // an oversized record, which must fail open rather than overrun a frame.
      if(r.count>maxRasterSourceTriangles){stats.complexitySkipped++;continue;}
      if(!validRecord(r,view,validationCache))continue;
      const old=previous[candidates.length];if(!old||old.record!==r||old.state!==r.state)same=false;candidates.push(r);r.bounds.getSize(tmp);
      // Dense rocks need the closest complete surface, not the cheapest moss
      // fragment. Small authored walls retain their established cost ranking.
      r.rank=r.surfacePatch?Math.min(32,tmp.lengthSq())/Math.max(.25,d*d):tmp.lengthSq()/Math.max(1,d*d)/Math.max(1,r.count);}
    if(previous.length!==candidates.length)same=false;stats.candidateMeshes=candidates.length;
    if(same){stats.reused=true;stats.updateMs=now()-start;return stats;}
    invalidateCoverage();depth.fill(Infinity);cw.set(view.matrixWorld.elements);cp.set(view.projectionMatrix.elements);layerMask=view.layers.mask;
    previous.length=0;for(const r of candidates)previous.push({record:r,state:r.state});
    clearRasterStats();
    candidates.sort((a,b)=>b.rank-a.rank);
    for(const r of candidates){const passes=r.sides.includes(T.DoubleSide)?2:1;
      if(outOfTime())break;
      if(stats.projectedTriangles+r.count>maxFrameTriangles||stats.rasterMeshes>=maxMeshes||stats.rasterCells+size*passes>maxRasterCells){stats.budgetSkipped++;continue;}
      raster(r);stats.rasterMeshes++;if(stats.budgetExhausted)break;
    }
    for(let i=0;i<size;i++)if(Number.isFinite(depth[i]))stats.coveredCells++;ready=true;stats.updateMs=now()-start;return stats;
  }
  function projectBox(box){
    if(!box||box.isEmpty()||box.containsPoint(eye))return false;let x0=Infinity,x1=-Infinity,y0=Infinity,y1=-Infinity,z0=Infinity;
    for(let i=0;i<8;i++){if(!project(i&1?box.max.x:box.min.x,i&2?box.max.y:box.min.y,i&4?box.max.z:box.min.z,pv))return false;
      x0=Math.min(x0,pv[0]);x1=Math.max(x1,pv[0]);y0=Math.min(y0,pv[1]);y1=Math.max(y1,pv[1]);z0=Math.min(z0,pv[2]);}
    if(![x0,x1,y0,y1,z0].every(Number.isFinite)||x1<0||x0>width||y1<0||y0>height)return false;
    Object.assign(query,{x0:clamp(Math.floor(x0-EDGE),0,width-1),x1:clamp(Math.floor(x1+EDGE),0,width-1),y0:clamp(Math.floor(y0-EDGE),0,height-1),y1:clamp(Math.floor(y1+EDGE),0,height-1),z0:z0-DEPTH});return true;
  }
  function isOccluded(box,view=camera){stats.queries++;
    if(!enabled||!ready||!view||view!==camera||view.layers.mask!==layerMask||!eq16(view.matrixWorld.elements,cw)||!eq16(view.projectionMatrix.elements,cp)){stats.staleQueries++;return false;}
    if(!stats.coveredCells||!projectBox(box))return false;for(let y=query.y0;y<=query.y1;y++)for(let x=query.x0;x<=query.x1;x++)if(!(depth[y*width+x]<query.z0))return false;stats.culled++;return true;
  }
  function auditSources(view=camera){
    if(!view)return {records:records.length,reason:'no-camera'};view.updateMatrixWorld();
    const origin=new T.Vector3().setFromMatrixPosition(view.matrixWorld),clip=new T.Frustum().setFromProjectionMatrix(new T.Matrix4().multiplyMatrices(view.projectionMatrix,view.matrixWorldInverse));
    const counts={},examples=[];
    for(const r of records){let reason=r.bounds.distanceToPoint(origin)>maxDistance?'distance':!clip.intersectsBox(r.bounds)?'frustum':null,source=r.parts[0];
      if(!reason)for(const part of r.parts){const failure=sourceRejection(part,view,r.parts.length>1?r.mesh.material:null);if(failure){reason=failure;source=part;break;}}
      if(!reason&&!validRecord(r,view))reason='material-opacity';if(!reason&&r.count>maxRasterSourceTriangles)reason='complexity';reason??='eligible';counts[reason]=(counts[reason]||0)+1;
      if(examples.length<40&&reason!=='distance'&&reason!=='frustum')examples.push({reason,objectId:source.mesh.id,name:source.mesh.name,region:r.region,variant:r.variant,family:r.family,parts:r.parts.length,triangles:r.count});
    }
    return {records:records.length,counts,examples};
  }
  return {update,isOccluded,auditSources,stats,width,height,
    isObjectOccluded(object,view=camera){const r=byObject.get(object),box=getObjectBounds?.(object)||object?.userData?.dgySpatialWorldBounds||(r&&camera&&validRecord(r,camera)?r.bounds:null);return !!box&&isOccluded(box,view);},
    get coverageRevision(){return stats.coverageRevision;},
    get enabled(){return enabled;},set enabled(v){enabled=!!v;invalidateCoverage();},invalidate(){invalidateCoverage();},
    dispose(){enabled=false;invalidateCoverage();camera=null;records.length=0;candidates.length=0;previous.length=0;depth.fill(Infinity);},
  };
}

export function createConservativeOcclusion(options){
  const work=prepareConservativeOcclusion(options);let step;
  do{step=work.next();}while(!step.done);
  return step.value;
}

export async function prepareConservativeOcclusionAsync(options,{
  budgetMs=8,now=()=>performance.now(),
  yieldFrame=()=>new Promise(resolve=>requestAnimationFrame(()=>setTimeout(resolve,0))),onProgress=()=>{},
}={}){
  const work=prepareConservativeOcclusion(options);let slice=now(),latest;
  while(true){
    const step=work.next();
    if(step.done){if(latest)onProgress(latest);return step.value;}
    // Inspection is bounded metadata work; triangle preprocessing is the rest.
    const {done,total,phase}=step.value;
    latest={done:phase==='inspect'?.1*done/total:.1+.9*(total?done/total:1),total:1};
    if(now()-slice>=budgetMs){onProgress(latest);await yieldFrame();slice=now();}
  }
}
