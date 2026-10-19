// Presentation is deliberately separate from build callbacks: a fast CPU stage
// must not flash several captions or consume the progress reserved for GPU work.
export const LOADING_STAGES = [
  ['备料',1800], ['研彩调色',1400], ['展卷布景',400],
  ['堆山凿池',200], ['铺石子路，架桥',100], ['起楼阁，砌粉墙',200],
  ['修馆舍，筑茅屋',300], ['种树栽竹，植荷，叠驳岸',1300],
  ['雕梁画栋',4500], ['上瓦挂匾',600], ['铺草',350],
  ['点野花，种蕨草',1400], ['调天光',900], ['梳理全园',2500],
  ['上传全园模型',3000], ['上传全园贴图',3000],
  ['编译全园材质',6500], ['编译全园阴影',1000],
  ['合成光影',1000], ['绘制首帧',3500],
];

export const LOADING_CAPTIONS = [
  '备料', '堆山凿池', '铺石子路，架桥', '起楼阁，砌粉墙',
  '修馆舍，筑茅屋', '种树栽竹，植荷，叠驳岸', '上瓦挂匾',
  '铺草，点野花', '研彩调色', '雕梁画栋', '调天光',
  '落下树影', '映出水光', '展卷迎客',
];

const clamp = (v,a,b) => Math.min(b,Math.max(a,v));

export function createLoadingProgress({now=()=>performance.now(), captionMs=1600}={}) {
  const total=LOADING_STAGES.reduce((n,s)=>n+s[1],0), started=now();
  const stages=LOADING_STAGES.map(([id,ms],i)=>({id,ms,i}));
  let sum=0;
  for(const stage of stages){stage.a=sum/total;sum+=stage.ms;stage.b=sum/total;}
  let current=stages[0], stageStarted=started, last=started, reported=0;
  let value=0, target=0, caption=0, captionAt=started, complete=false, scale=1;
  const timings=[];
  function stage(id, fraction=0){
    if(complete)return;
    const next=stages.find(s=>s.id===id);
    if(!next||next.i<current.i)return; // late download callbacks cannot move backwards
    if(next!==current){
      const t=now();
      timings.push({id:current.id,ms:t-stageStarted});
      // Adapt the animation speed to this device without changing stage weights.
      const expected=next.a*total;
      if(expected>3000)scale=clamp((t-started)/expected,0.4,3);
      current=next;stageStarted=t;reported=0;
    }
    if(Number.isFinite(fraction))reported=Math.max(reported,clamp(fraction,0,1));
  }
  function sample(){
    const t=now(),dt=clamp(t-last,0,1000);last=t;
    // Stay within the current stage while an upload/compile has no callbacks.
    // The tail is reserved until completion of the real work is reported.
    const elapsed=Math.max(0,t-stageStarted),budget=current.ms*scale;
    const estimated=0.9*elapsed/(elapsed+budget);
    target=complete?1:Math.min(0.985,Math.max(target,current.a+(current.b-current.a)*Math.max(reported,estimated)));
    const rate=Math.min(0.00005,Math.max(0.000004,1/(total*scale),(target-value)/3200));
    value=complete?1:Math.min(target,value+dt*rate);
    const desired=Math.min(LOADING_CAPTIONS.length-1,Math.floor(value*LOADING_CAPTIONS.length));
    if(complete){caption=LOADING_CAPTIONS.length-1;}
    else if(desired>caption&&t-captionAt>=captionMs){caption=desired;captionAt=t;}
    return {value,target,caption:LOADING_CAPTIONS[caption],stage:current.id,elapsedMs:t-started,complete};
  }
  function finish(){
    if(!complete){timings.push({id:current.id,ms:now()-stageStarted});complete=true;}
    return sample();
  }
  return {stage,sample,finish,snapshot:()=>({timings:[...timings],...sample()})};
}

export function mountLoadingProgress({bar,step,pct,translate=s=>s,now=()=>performance.now()}){
  const progress=createLoadingProgress({now}),captions=[];
  let stopped=false,lastCaption='',lastCaptionAt=-Infinity,lastPercent=-1,rendering=false,renderCaption='',renderAt=0,renderFrom=0;
  const reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;
  function paint(state=progress.sample()){
    if(rendering&&!state.complete)state={...state,caption:renderCaption};
    const percent=+(state.value*100).toFixed(2);
    if(!rendering&&percent!==lastPercent){bar.style.transform=`scaleX(${state.value.toFixed(5)})`;lastPercent=percent;}
    pct.textContent=Math.round(percent)+'% · '+Math.round(state.elapsedMs/1000)+'s';
    if(state.caption!==lastCaption){
      lastCaption=state.caption;lastCaptionAt=now();step.textContent=translate(state.caption);
      captions.push({text:state.caption,ms:state.elapsedMs,progress:percent});
      if(!reduced&&step.animate)step.animate([{opacity:.35},{opacity:.75}],{duration:260});
    }
  }
  const timer=setInterval(()=>paint(),100);paint();
  return {
    stage(id,fraction){
      progress.stage(id,fraction);
      if(id==='绘制首帧'&&!rendering){
        renderAt=now();renderFrom=progress.sample().value;
        renderCaption=renderAt-lastCaptionAt>=1600?'映出水光':lastCaption;
        rendering=true;paint();
        // First WebGL draw can block JS for several seconds. A compositor
        // transform keeps the reserved final stretch moving during that draw.
        bar.style.transition='transform 3.5s linear';bar.style.transform='scaleX(.985)';
      }
    },
    finish(){
      const visible=rendering?renderFrom+(.985-renderFrom)*clamp((now()-renderAt)/3500,0,1):progress.sample().value;
      const fillMs=reduced?0:clamp((1-visible)/.00005,650,1800);
      stopped=true;rendering=false;clearInterval(timer);bar.style.transition=`transform ${fillMs}ms linear`;paint(progress.finish());
      // One short, bounded fill; never delay build work to play a caption queue.
      return new Promise(resolve=>setTimeout(resolve,fillMs));
    },
    stop(){stopped=true;clearInterval(timer);},
    snapshot(){return {...progress.snapshot(),captions:[...captions],stopped};},
  };
}
