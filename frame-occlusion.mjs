// Per-frame GPU visibility for the main camera (HZB occlusion, verdicts read back on a later frame).
//
// After the main view is drawn, its own depth (cave walls, rockeries, terrain, walls, roofs, trunks, dense foliage) is
// reduced to a depth pyramid and every candidate box is tested against it in one draw. The verdicts go to a pixel-pack
// buffer and are read once the GPU has signalled a fence; the main pass of the following frames skips hidden
// candidates, the reflection planner skips hidden water and mirrors, the grass skips hidden cells.
// Reading the buffer (getBufferSubData) is still a synchronous round trip in Chrome: it waits until the GPU process has
// worked through everything queued before it, its own and other work (such as compositing the last frame). How long
// that is depends on where in the frame it happens: right after the frame's own logic the wait was ~12 ms, at the very
// start of the frame (before the frame's logic) ~2 ms. With autoPoll off, update() does not read; the application calls
// poll() at a cheap point (the start of its frame) instead.
//
// Which surface may occlude is decided per pixel. While the main view is drawn, every draw leaves its kind of occluder in
// the target's alpha channel (only the alpha blend factors change; nothing reads that alpha, the colours are the same):
//  - fixed surfaces write alpha 1 (the shaders' own opaque output, untouched); alpha-to-coverage ones output the coverage
//    as alpha, so their covered samples keep the larger of it and what was there (never more trusted than the truth);
//  - surfaces whose vertices sway with a declared speed bound multiply it by SWAY_ALPHA (just below 1);
//  - untrusted surfaces set it to 0: objects that moved recently, fast or unknown vertex animation, see-through surfaces
//    that write depth;
//  - draws that do not write depth leave it alone.
// MSAA resolves average the samples, so a pixel is fixed only if all its samples are, untrusted if any sample is.
//
// A verdict certifies "hidden from EVERY eye within eps of the eye path it was made for, while the occluders cannot
// have moved further than the margin they were eroded by":
//  - eye motion: the path is the measured camera velocity carried over the readback latency (a camera that walks
//    forward sees occluders slide outward from the view centre, so a box needs cover only on its inner side, by the
//    parallax of the path); eps covers speed and direction changes off the path. The camera may rotate freely; once
//    the eye leaves the path tube, or the verdict outlives its time budget, it expires and everything is drawn until
//    fresh verdicts arrive (a camera at rest has a second, still certificate);
//  - swaying pixels erode their surroundings by the extra shift their speed bound allows over the verdict's life;
//  - untrusted pixels never occlude;
//  - a trusted occluder that starts moving or leaves the scene drops every verdict in flight.
// At the screen edge (edgeClamp, the default) only the part of a box that is on screen is tested, as engines with
// hardware queries do; the verdict records the edges it was clamped at, and is not used once the view has turned so
// far that the outside of such an edge comes into view (a box whose covering occluders would have to come from beyond
// the edge along the eye path is not certified at all). With edgeClamp off, boxes whose test region reaches the edge
// are never certified (exact mode).
// One instance serves one camera and its target; shadows and every other camera are untouched. A planar reflection
// (mirror camera with an oblique clip-plane projection, 8-bit target, scissored renders) gets its own instance:
// kindBits 8 for the alpha encoding, afterRender(drawn) for the rectangle that was rendered, its own idKey.

const MAX_LEVELS = 13; // half-resolution pyramid of an 8K target; texture units 1..13, boxes on unit 0
const MAX_HOLES = 16;
const DEPTH_ULP = 4 / 16777216; // 24-bit depth (and float32 linearisation): quantisation margin factor, x z^2 / near
const SWAY_ALPHA = 1 - 1 / 1024; // exact in half float; hundreds of swaying layers stay above 0.8, any untrusted sample pulls a resolve below

const VS = `#version 300 es
void main(){vec2 p=vec2(float((gl_VertexID<<1)&2),float(gl_VertexID&2));gl_Position=vec4(p*2.0-1.0,0.0,1.0);}`;

const HEAD = `#version 300 es
precision highp float;precision highp int;precision highp sampler2D;
out vec4 oc;
`;

// level 0 from the depth and the occluder kind (target alpha) of each 2x2 pixel block: (farthest, nearest, nearest
// swaying) linear depth. Cleared pixels (sky), untrusted pixels and samples inside a hole (rectangle x depth range of a
// depth-only draw that is not fixed) are 1e30: they never occlude and never set the erosion.
const REDUCE0 = HEAD + `uniform sampler2D uDepth,uKind;uniform ivec2 uMax;uniform vec2 uPz,uNdc;uniform vec3 uObl,uK;uniform ivec4 uValid;uniform int uHoles;
uniform ivec4 uHR[${MAX_HOLES}];uniform vec2 uHZ[${MAX_HOLES}];
// view depth of a depth-buffer value at pixel q; uObl: the x / y terms of an oblique (clip-plane) projection's depth row
float lin(float d,ivec2 q){vec2 n=(vec2(q)+0.5)*uNdc-1.0;return d>=1.0?1e30:uPz.y/((2.0*d-1.0)+uPz.x-(uObl.x*n.x+uObl.y*n.y+uObl.z));}
void main(){ivec2 p=ivec2(gl_FragCoord.xy)*2;float a=0.0,b=1e30,s=1e30;
for(int j=0;j<2;j++)for(int i=0;i<2;i++){ivec2 q=min(p+ivec2(i,j),uMax);float z=lin(texelFetch(uDepth,q,0).r,q),k=texelFetch(uKind,q,0).a;
 if(!(k>=uK.x&&k<=uK.y)||q.x<uValid.x||q.y<uValid.y||q.x>uValid.z||q.y>uValid.w)z=1e30;
 for(int h=0;h<${MAX_HOLES};h++){if(h>=uHoles||z>=1e29)break;ivec4 r=uHR[h];
  if(q.x>=r.x&&q.x<=r.z&&q.y>=r.y&&q.y<=r.w&&z>=uHZ[h].x&&z<=uHZ[h].y)z=1e30;}
 a=max(a,z);b=min(b,z);if(k<uK.z)s=min(s,z);}
oc=vec4(a,b,s,1.0);}`;

const REDUCE = HEAD + `uniform sampler2D uSrc;uniform ivec2 uMax;
void main(){ivec2 p=ivec2(gl_FragCoord.xy)*2;vec3 a=texelFetch(uSrc,min(p,uMax),0).rgb,b=texelFetch(uSrc,min(p+ivec2(1,0),uMax),0).rgb,
c=texelFetch(uSrc,min(p+ivec2(0,1),uMax),0).rgb,d=texelFetch(uSrc,min(p+ivec2(1,1),uMax),0).rgb;
oc=vec4(max(max(a.r,b.r),max(c.r,d.r)),min(min(a.g,b.g),min(c.g,d.g)),min(min(a.b,b.b),min(c.b,d.b)),1.0);}`;

// Two certificates per box, for two sets of later eyes and views: "moving" (a tube of radius eps around the eye path,
// view turn alpha; both follow the measured camera motion, with floors) and "still" (a camera at rest: a tiny ball and
// alpha). Output: red = hidden for the
// moving ball, green = hidden for the still one; blue, alpha = hidden-edge bits plus bit 16 (rotation-independent),
// or why not (moving, still): 1 inactive, 2 the eye ball
// touches the box, 3 the box reaches the near zone, 4 off screen, then + 16 x step: 5 the region reaches the screen
// edge, 6 something in the region is not in front, 8 swaying occluders at a clamped screen edge, 9 a surface of the
// region may cross the near plane of a later frame; 7 no fit.
function testShader(levels, dbg = false) {
  let fetch = '';
  for (let i = 0; i < levels; i++) fetch += (i ? 'else ' : '') + `if(L==${i})return texelFetch(uH[${i}],p,0).rgb;`;
  return HEAD + `uniform sampler2D uBox;uniform sampler2D uH[${levels}];uniform int uLevels,uTW,uCount;uniform ivec2 uScreen;uniform ivec4 uVR;
uniform mat4 uView,uProj;uniform vec3 uEye,uD,uDw;uniform vec2 uPP,uFxy,uEps2,uN02,uRadial2;uniform vec4 uRot;uniform float uF,uMot,uQ,uClampStill,uClampEdge,uEarly;uniform int uRT;
vec3 fetchL(int L,ivec2 p){${fetch}return vec3(1e30,0.0,0.0);}
// (farthest, nearest, nearest swaying) occluder depth over the pixel rectangle [x0,x1]x[y0,y1] (inclusive, inside the
// screen), read at the finest level where it spans at most 8x8 texels; texels overlapping its edge widen it
// (conservative every way)
vec3 region(int x0,int y0,int x1,int y1,float zLim){int L=0;
for(;L<uLevels-1;L++){int s=L+1;if(((x1>>s)-(x0>>s))<uRT&&((y1>>s)-(y0>>s))<uRT)break;}
int s=L+1;float a=0.0,b=1e30,c=1e30;
for(int ty=y0>>s;ty<=(y1>>s);ty++){for(int tx=x0>>s;tx<=(x1>>s);tx++){vec3 v=fetchL(L,ivec2(tx,ty));a=max(a,v.r);b=min(b,v.g);c=min(c,v.b);}
 if(a>=zLim)break;} // an occluder that is not in front of the box: the test fails whatever the rest of the region holds
return vec3(a,b,c);}
float gZb=0.0,gMx=0.0,gR=0.0; // debug output: box depth, farthest occluder of the last region, its widening
bool gIndependent=false;
int gEdge=0; // screen edges (1 left, 2 right, 4 bottom, 8 top) the box was clamped at: a later turn of the view can bring its
             // outside part into view, the verdict is checked against the actual turn when it is used
// lvl 0: every eye within eps of the path uEye + s uDw, s in [0,1] (camera space uD: right, up, forward); lvl 1: every
// eye within eps of uEye (a camera at rest; eps < 0: not certified)
int certify(vec3 mn,vec3 mx,int lvl){
gIndependent=false;
float eps=lvl==0?uEps2.x:uEps2.y,n0=lvl==0?uN02.x:uN02.y;vec2 rot=lvl==0?uRot.xy:uRot.zw;bool clampE=uClampEdge>0.5||(lvl==1&&uClampStill>0.5);
if(eps<0.0)return 1;
vec3 D=lvl==0?uD:vec3(0.0),Dw=lvl==0?uDw:vec3(0.0);float fw=max(D.z,0.0);
// the eye path (or the near zone around it) touches the box: no certificate
vec3 ec=uEye+0.5*Dw;if(distance(clamp(ec,mn,mx),ec)<=0.5*length(Dw)+eps+n0)return 2;
float zb=1e30;vec2 lo=vec2(1e30),hi=vec2(-1e30);
for(int i=0;i<8;i++){vec3 q=vec3((i&1)!=0?mx.x:mn.x,(i&2)!=0?mx.y:mn.y,(i&4)!=0?mx.z:mn.z);vec4 v=uView*vec4(q,1.0);float z=-v.z;
if(z<n0)return 3;zb=min(zb,z);vec4 k=uProj*v;vec2 s=(k.xy/k.w*0.5+0.5)*vec2(uScreen);lo=min(lo,s);hi=max(hi,s);}
gZb=zb;
// uVR: the drawn rectangle (pixels, inclusive): the whole screen, or the scissor of a partial render (only it holds depth)
vec2 vlo=vec2(uVR.xy),vhi=vec2(uVR.zw)+1.0;
// a box beyond an edge of it (in the frustum only by its bounding sphere): hidden while it stays beyond for every eye of
// the certificate (its image under an eye move b-scaled along the path, x -> pp + (x - pp - b F D.xy) / (1 - b D.z),
// b in [0, 1/zb], is extreme at the ends; widened as below) and the view does not turn that edge's outside into view
int off=(hi.x<vlo.x?1:0)|(lo.x>=vhi.x?2:0)|(hi.y<vlo.y?4:0)|(lo.y>=vhi.y?8:0);
if(off!=0){if(!clampE)return 4;
 float dA=zb-fw-eps;if(dA<=1e-3||zb<=D.z+1e-3)return 4;
 float b=1.0/zb,q=1.0/(1.0-b*D.z);vec2 l1=uPP+(lo-uPP-b*uFxy*D.xy)*q,h1=uPP+(hi-uPP-b*uFxy*D.xy)*q,rl=min(lo,l1),rh=max(hi,h1);
 float rho=length(max(abs(rl-uPP),abs(rh-uPP))),A=eps/dA;if(1.42*A>=0.9)return 4;
 float R=(A*(uF+rho)+2.0)/(1.0-1.42*A);rl-=R;rh+=R;
 if(((off&1)!=0&&rh.x<vlo.x)||((off&2)!=0&&rl.x>=vhi.x)||((off&4)!=0&&rh.y<vlo.y)||((off&8)!=0&&rl.y>=vhi.y)){gEdge=off;gIndependent=true;return 0;}
 return 4;}
// a camera at rest: nothing beyond the screen edge can come into view, the box is what is on screen of it. With
// edgeClamp (the default) the moving certificate does the same: what turns into view at the edge is drawn from the
// first verdict that sees it (one or two frames late at worst, as engines with hardware queries do)
gEdge=0;
if(clampE){gEdge=(lo.x<vlo.x?1:0)|(hi.x>vhi.x?2:0)|(lo.y<vlo.y?4:0)|(hi.y>vhi.y?8:0);lo=max(lo,vlo);hi=min(hi,vhi-0.5);}
// The region whose occluders can cover the box from every eye of the certificate. An eye move s*D carries a surface
// at depth Z by the affine image warp x -> pp + (x-pp)(1 - s D.z/Z) + (s/Z) F D.xy, and the occluder that covers a box
// point afterwards started where the inverse warp of that point lies: within the bounds of the box rect scaled about
// the principal point by 1 - a D.z and shifted by b F D.xy, a, b in [0, 1/zA], for occluders at depth >= zA (exact
// for a box at infinity, nearer boxes lie in between). That rect is widened by the shift of an eye move eps off the
// path, of swaying occluders (depth >= zS) moving uMot, of the widening itself (1.42 R off-axis), and 2 px for
// rasterisation and resolve. Start from the box's own depth and grow while the region holds nearer occluders than
// assumed; give up when it holds something that is not in front of the box.
float zA=zb,zS=1e30;
for(int it=0;it<6;it++){
float dA=zA-fw-eps;if(dA<=1e-3)return 9+16*it;
float a=1.0/zA;vec2 sc=vec2(1.0-a*D.z),tr=a*uFxy*D.xy,l1=uPP+(lo-uPP)*sc,h1=uPP+(hi-uPP)*sc;
vec2 rl=min(min(lo,l1),min(lo,l1)+tr),rh=max(max(hi,h1),max(hi,h1)+tr);
// the occluders that cover it later would come from beyond the screen edge (the eye path carries content inward
// there): unknown, at most a 3 px strip is let go
if(clampE&&(rl.x<vlo.x-3.0||rl.y<vlo.y-3.0||rh.x>vhi.x+3.0||rh.y>vhi.y+3.0))return 5+16*it;
float rho=length(max(abs(rl-uPP),abs(rh-uPP))),A=eps/dA+(zS<1e29?uMot/max(zS-fw-uMot,1e-3):0.0);
if(1.42*A>=0.9)return 7;
float R=(A*(uF+rho)+2.0)/(1.0-1.42*A);gR=R;int r=int(ceil(R));
int ax=int(floor(rl.x))-r,ay=int(floor(rl.y))-r,bx=int(floor(rh.x))+r,by=int(floor(rh.y))+r;
bool edge=ax<uVR.x||ay<uVR.y||bx>uVR.z||by>uVR.w;int ux0=ax,uy0=ay,ux1=bx,uy1=by;
if(edge){if(!clampE)return 5+16*it;ax=max(ax,uVR.x);ay=max(ay,uVR.y);bx=min(bx,uVR.z);by=min(by,uVR.w);}
vec3 m=region(ax,ay,bx,by,uEarly>0.5?zb:3e38);gMx=m.x;
// exact mode: swaying occluders that could leave the screen across a clamped edge, none within their own shift of it
if(edge&&m.z<1e29&&uClampEdge<0.5){int w=int(ceil(uMot*(uF+rho+1.42*R)/max(m.z-uMot,1e-3)+2.0));
 if(ux0<uVR.x&&region(ax,ay,min(ax+w,bx),by,3e38).z<1e29)return 8+16*it;
 if(ux1>uVR.z&&region(max(bx-w,ax),ay,bx,by,3e38).z<1e29)return 8+16*it;
 if(uy0<uVR.y&&region(ax,ay,bx,min(ay+w,by),3e38).z<1e29)return 8+16*it;
 if(uy1>uVR.w&&region(ax,max(by-w,ay),bx,by,3e38).z<1e29)return 8+16*it;}
// near zone: a surface at depth z and angle theta off the view axis stays beyond every later near plane (<= nearMax)
// while z cos(theta+alpha)/cos(theta) - eps - forward travel >= nearMax; theta at its widest over the region
vec2 t=max(abs(vec2(ax,ay)-uPP),abs(vec2(bx+1,by+1)-uPP))/uFxy;float den=rot.x-length(t)*rot.y;
// A second proof is independent of view rotation: old view depth lower-bounds the surface's radial distance.
// Subtract the entire eye/surface motion, then the farthest current frustum ray still puts it beyond the near plane.
// Only boxes whose actual covering region passes this proof receive bit 16; other boxes keep their turn cone.
float radial=lvl==0?uRadial2.x:uRadial2.y;bool independent=radial<1e29&&m.y>=radial;
if(!independent&&(den<=0.02||m.y<n0/den))return 9+16*it;
// hidden needs the nearest point of the box behind the farthest occluder of the region, by more than the depth
// quantisation there
if(!(zb>m.x+0.01+2e-4*m.x+uQ*m.x*m.x))return 6+16*it;
if(m.y>=zA&&m.z>=zS){gIndependent=independent;return 0;}
zA=min(zA,m.y)*0.9;zS=min(zS,m.z)*0.9;}
return 7;}
void main(){ivec2 c=ivec2(gl_FragCoord.xy);int id=c.y*uTW+c.x;oc=vec4(0.0);if(id>=uCount)return;
vec4 A=texelFetch(uBox,ivec2(c.x*2,c.y),0),B=texelFetch(uBox,ivec2(c.x*2+1,c.y),0);
int cm=1,cs=1,em=0,es=0;if(A.w>0.5){cm=certify(A.xyz,B.xyz,0);em=gEdge|(gIndependent?16:0);es=em;if(cm!=0){cs=certify(A.xyz,B.xyz,1);es=gEdge|(gIndependent?16:0);}else cs=0;}
// hidden: blue / alpha hold the clamped edges instead of the reason
oc=${dbg ? 'vec4(float(cm)+float(cs)/128.0,gZb,gMx,gR)' : 'vec4(cm==0?1.0:0.0,cs==0?1.0:0.0,float(cm==0?em:cm)/255.0,float(cs==0?es:cs)/255.0)'};}`;
}

const finiteBox = b => b?.isBox3 && !b.isEmpty() && Number.isFinite(b.min.x) && Number.isFinite(b.min.y) && Number.isFinite(b.min.z) &&
  Number.isFinite(b.max.x) && Number.isFinite(b.max.y) && Number.isFinite(b.max.z);
const materialsOf = o => Array.isArray(o.material) ? o.material : [o.material];
const recipeKey = m => { try { return m.customProgramCacheKey(); } catch { return ''; } };

// A ray visible through an ordinary perspective frustum has view depth >= radial distance / cornerLength.
// Old occluder depth is a lower bound on its old radial distance. This threshold therefore proves that every
// covering surface remains beyond the near plane, for any view rotation and every certified eye/surface motion.
// Oblique reflection clip planes need the original angle-dependent proof instead.
export function rotationIndependentNearDepth(p, near, travel, eps, motion) {
  if (p[2] !== 0 || p[6] !== 0 || p[3] !== 0 || p[7] !== 0 || p[11] !== -1 || p[15] !== 0 || !(p[0] > 0 && p[5] > 0)) return Infinity;
  return near * Math.hypot(1, (1 + Math.abs(p[8])) / p[0], (1 + Math.abs(p[9])) / p[5]) + travel + eps + motion + 0.01;
}
const projectionShape = [0, 5, 8, 9, 2, 6, 3, 7, 11, 15];

// The normal, zero-wait completion probe (also used by three.js). Under sustained native keyboard input Chromium
// may defer completion notifications for both sync APIs; poll() therefore also has a bounded queue watchdog below.
export function frameFenceReady(gl, sync) {
  const status = gl.clientWaitSync(sync, gl.SYNC_FLUSH_COMMANDS_BIT, 0);
  if (status === gl.WAIT_FAILED) throw new Error('GPU visibility fence probe failed');
  return status === gl.ALREADY_SIGNALED || status === gl.CONDITION_SATISFIED;
}

// A deferred notification must not exhaust the PBO ring. Once the oldest pending verdict has missed two use frames,
// read the NEWEST pending buffer, not the stalled oldest result: its original camera/time certificate stays useful.
// getBufferSubData orders against that buffer's preceding readPixels, so the watchdog gets completed bytes even if
// the browser has not delivered the fence notification yet. The GPU may still make this read wait; use it only when
// normal non-blocking probes have actually stalled, not simply because the camera is moving or FPS is low.
export function stalledFrameReadback(slots, readingFrame, maxFrames = 2) {
  let newest = null, age = 0;
  for (const slot of slots) if (slot.sync && slot.meta) {
    age = Math.max(age, readingFrame - slot.meta.frame);
    if (!newest || slot.meta.frame > newest.meta.frame) newest = slot;
  }
  return age >= maxFrames ? newest : null;
}

export function frameOcclusionSupport(renderer) {
  const gl = renderer?.getContext?.();
  if (!gl || renderer.capabilities?.isWebGL2 !== true) return { supported: false, reason: 'WebGL2 is required' };
  if (renderer.capabilities?.reverseDepthBuffer || renderer.capabilities?.logarithmicDepthBuffer) return { supported: false, reason: 'ordinary depth required' };
  if (!gl.getExtension('EXT_color_buffer_float')) return { supported: false, reason: 'EXT_color_buffer_float unavailable' };
  if (gl.getParameter(gl.MAX_TEXTURE_IMAGE_UNITS) < MAX_LEVELS + 1) return { supported: false, reason: 'not enough texture units' };
  return { supported: true, reason: '' };
}

/**
 * THREE, renderer, camera: the main camera. registry (optional): occlusion-scene-registry, re-checked at use.
 * swaySpeed(material): declared bound (m/s) on how fast a material's vertex animation moves vertices, or undefined.
 * swayReach(material): declared bound (m) on how far that animation moves vertices from their rest position, or
 * undefined; such draws are tested with their exact box widened by it instead of three's frustum sphere.
 * swayWind(material): true when that animation is driven by the wind; windScale(life) (once a frame): factor in [0, 1]
 * on their declared speeds (declared for the strongest wind) that holds for the next life seconds.
 * Per frame: update(camera, mainTarget) before the main render (after the scene's world matrices are updated), the
 * renderer hook renderer.dgyDrawClass = api.classify, and afterRender() right after the main render while its target
 * is bound. The main target needs an alpha channel and a depth texture.
 */
export function createFrameOcclusion({ THREE: T, renderer, camera, registry = null, maxCandidates = 32768, epsMin = 0.01, epsMax = 3,
  turnMin = 0.1745, turnMax = 0.5, stillMin = 5e-6, edgeClamp = true, cutDistance = 1.5, slotCount = 4, verifyPerFrame = 64, watchPerFrame = 128, refreshPerFrame = 256, recheck = 4, cooldown = 8, fastSpeed = 2.5,
  swaySpeed = null, swayReach = null, swayWind = null, windScale = null, idKey = 'dgyHzbId', kindBits = 16, autoPoll = true, carrier = null, maxFenceFrames = 2 } = {}) {
  const support = frameOcclusionSupport(renderer), gl = renderer.getContext(), state = renderer.state;
  // occluder kinds in the target's alpha: half float (SWAY_ALPHA, see above) or 8-bit unorm (one step below 1, no MSAA)
  const SWAY = kindBits === 8 ? 254 / 255 : SWAY_ALPHA, K_FIX = kindBits === 8 ? 1 - 0.5 / 255 : 0.99975, K_MAX = kindBits === 8 ? 1.001 : 1.00025;
  let valid = null; // [x0, y0, x1, y1] (target pixels, inclusive) of the part of the target drawn by this render
  // experiments: region read span (texels per axis), eps terms, path / life lengths in frames
  const tune = { rt: 16, epsMin, epsPath: 0.1, epsAcc: 1, nPath: 0.5, life: 1.5, hold: 8, noBlend: false, early: true, timeGpu: false, rep: 1, mot: 1 };
  const TW = 128, cap = Math.ceil(maxCandidates / TW) * TW;
  const stats = { ...support, enabled: support.supported, candidates: 0, reg: 0, objects: 0, boxes: 0, tested: 0, culled: 0, boxCulled: 0,
    hiddenResults: 0, rotationIndependent: 0, live: false, eps: 0, mot: 0, wind: 1, latency: 0, resultAge: 0, issued: 0, resolved: 0, skippedNoSlot: 0, expired: 0,
    drops: 0, lastDrop: '', invalidReason: 'no-result', pending: 0, oldestPending: 0, fencePolls: 0, fenceTimeouts: 0, recoveredReads: 0, discardedPending: 0, recoveryMode: false,
    draws: { fixed: 0, sway: 0, untrusted: 0, keep: 0, rect: 0 }, holes: 0, holeKinds: {}, levels: 0, width: 0, height: 0,
    updateMs: 0, afterMs: 0, readMs: 0, holds: 0, rests: 0, refreshed: 0, deactivated: 0, errors: 0, reason: support.reason };
  let enabled = support.supported, disposed = false, failed = false, frame = 0, epoch = 0, checked = false, gated = false;
  const cands = [], idOf = new Map(), since = new Int32Array(cap), checkedAt = new Int32Array(cap).fill(-1e9), boxData = new Float32Array(cap * 8);
  let rows = 0, dirtyLo = Infinity, dirtyHi = -1, verifyCursor = 0, refreshCursor = 0;
  const eye = new T.Vector3(), lastEye = new T.Vector3(), eyeNow = new T.Vector3(), tmpBox = new T.Box3(), tmpSphere = new T.Sphere();
  const fwd = new T.Vector3(), lastFwd = new T.Vector3(), fwdNow = new T.Vector3(), tmpC = new T.Vector3();
  const turn = new Float32Array(8), grow = new Float32Array(8); let lastNear = -1, level = 0; // per-frame view turn (rad), near-plane growth
  const tmpM = new T.Matrix4(), tmpV = new T.Vector4(), tmpB2 = new T.Box3();
  const disp = new Float32Array(8); let dispN = 0, haveLast = false, latMax = 1;
  const vel = new Float32Array(24), path = new T.Vector3(), pathC = new T.Vector3(), tmpQ = new T.Quaternion(); // per-frame eye velocity (world, m/s)
  const dts = new Float32Array(8); let dtN = 0, lastNow = -1;
  const lat = new Int32Array(16); let latN = 0;
  let res = null; // latest verdicts: { frame, time, life, eye, fwd, q, cam, path, eps: [moving, still], sin: [..], nearMax, count, epoch, data }
  let entering = 0, rotation = 0; // entering edges and certificates whose original turn cone still holds
  const bufs = [new Uint8Array(cap * 4), new Uint8Array(cap * 4)]; let flip = 0;
  const slots = [];
  let gpu = null; // GL objects, created on first use
  // this frame's main render: its target, whether its draws were classified, and the motion budget of swaying surfaces
  let target = null, armed = -1, motSpeed = 0, motWind = 0; // fastest swaying draw (not / driven by the wind)
  const holes = []; let holeN = 0; // depth-only draws that are not fixed (their alpha cannot be written)
  // trusted occluders of recent frames (their records: drawn = last frame drawn as one, wi = index in their list):
  // those seen moving before are checked every frame, the others watchPerFrame a frame in turn
  const REC = Symbol('frame-occlusion record'), watchMoved = [], watchStill = [];
  let watchKeep = 0, watchCursor = 0;
  function unwatch(list, i) { const last = list.pop(); if (i < list.length) { list[i] = last; last[REC].wi = i; } }
  // false: the entry at i is gone (stale, or its object moved) and another took its place
  function watchOne(list, i) {
    const o = list[i], r = o[REC];
    if (r.drawn < frame - watchKeep) { r.wi = -1; unwatch(list, i); return false; }
    if (o.parent && occluderSame(o, r)) return true;
    if (debug) note(debug.moved, (!sameTransform(o, r) ? 'T' : '') + (!sameGeometry(o, r) ? 'G' : '') + (!sameInstances(o, r) ? 'I' : '') + (!o.parent ? 'P' : '') + ' ' + label(o));
    const change = !o.parent ? 'removed' : !sameTransform(o, r) ? 'transform' : !sameGeometry(o, r) ? 'geometry' : 'instances';
    const detail = label(o) + ' [' + change + ']';
    r.wi = -1; unwatch(list, i); snap(o, r); r.moved = frame; r.everMoved = true; r.f = frame; if (inFlight()) bump('occluder moved', detail);
    return false;
  }
  const speedCache = new WeakMap();
  let debug = null; // { holes: {kind: {name: n}}, refresh: {why|name: n}, moved: {...} } while api.debug is on
  const label = o => { const p = []; for (let x = o; x && p.length < 3; x = x.parent) p.push(x.name || x.type); return p.join('<'); };
  const note = (table, k) => { table[k] = (table[k] || 0) + 1; };
  const defCompile = T.Material.prototype.onBeforeCompile, defRender = T.Object3D.prototype.onBeforeRender;
  const BLACK = new T.Color(0, 0, 0);

  // ---------- materials: how fast can this draw's vertices move (0: fixed, Infinity: unknown) ----------
  function vertexSpeed(m) {
    if (!m) return Infinity;
    const c = speedCache.get(m);
    if (c && c.bc === m.onBeforeCompile && c.sd === m.userData.shadowDynamic && c.vw === m.userData.dgyVWorld && c.ds === m.userData.dgySway) return c.v;
    const w = !!(swayWind && swayWind(m));
    let v = swaySpeed ? swaySpeed(m) : undefined;
    if (!Number.isFinite(v)) v = m.userData.dgySway;
    if (!Number.isFinite(v)) {
      if (m.isShaderMaterial || m.isRawShaderMaterial || m.displacementMap) v = Infinity;
      else if (m.userData.dgyOcclusionStaticSurface) v = 0; // audited building surface (occlusion-scene-registry)
      else if (m.onBeforeCompile === defCompile) v = m.userData.shadowDynamic ? Infinity : 0;
      else {
        const key = recipeKey(m), bm = key.replace(/^p\d+bm_/, '');
        // bmat AO recipes: their vWorld only forwards the vertex colour; other patch() recipes move vertices only by vWorld
        if (bm !== key && bm === m.name + '_ao') v = 0;
        else v = /^p\d+[^:]*$/.test(key) && !m.userData.shadowDynamic ? 0 : Infinity;
      }
    }
    speedCache.set(m, { bc: m.onBeforeCompile, sd: m.userData.shadowDynamic, vw: m.userData.dgyVWorld, ds: m.userData.dgySway, v, w });
    return v;
  }
  const maxSpeed = o => { let v = 0; for (const m of materialsOf(o)) v = Math.max(v, vertexSpeed(m)); return v; };

  // ---------- object state snapshots (transform, geometry, instances, materials) ----------
  class Snapshot {
    constructor() {
      this.w = new Float64Array(16); this.g = null; this.p = null; this.pv = -1; this.ix = null; this.iv = -1; this.im = null; this.imv = -1;
      this.n = 0; this.ic = -1; this.m = null; this.ms = null; this.moved = 0; this.f = 0; this.everMoved = false; this.drawn = -1; this.wi = -1;
    }
  }
  function snap(o, s = new Snapshot()) {
    const g = o.geometry, p = g?.attributes?.position;
    s.w.set(o.matrixWorld.elements); // float64: the exact matrix values
    s.g = g; s.p = p; s.pv = p ? p.version : -1; s.ix = g?.index || null; s.iv = g?.index ? g.index.version : -1;
    s.im = o.instanceMatrix || null; s.imv = o.instanceMatrix ? o.instanceMatrix.version : -1; s.n = o.count;
    s.ic = g?.isInstancedBufferGeometry ? g.instanceCount : -1;
    s.m = o.material; s.ms = materialsOf(o).map(m => m && m.onBeforeCompile);
    return s;
  }
  function sameTransform(o, s) { const e = o.matrixWorld.elements, w = s.w; for (let i = 0; i < 16; i++) if (e[i] !== w[i]) return false; return true; }
  function sameGeometry(o, s) {
    const g = o.geometry, p = g?.attributes?.position;
    return g === s.g && p === s.p && (p ? p.version : -1) === s.pv && (g?.index || null) === s.ix && (g?.index ? g.index.version : -1) === s.iv;
  }
  function sameInstances(o, s) {
    const g = o.geometry;
    return (o.instanceMatrix || null) === s.im && (o.instanceMatrix ? o.instanceMatrix.version : -1) === s.imv && o.count === s.n &&
      (g?.isInstancedBufferGeometry ? g.instanceCount : -1) === s.ic;
  }
  function sameMaterials(o, s) {
    const m = o.material; if (m !== s.m) return false;
    if (!Array.isArray(m)) return !!m && s.ms.length === 1 && m.onBeforeCompile === s.ms[0];
    if (m.length !== s.ms.length) return false;
    for (let i = 0; i < m.length; i++) if (!m[i] || m[i].onBeforeCompile !== s.ms[i]) return false;
    return true;
  }
  const sameState = (o, s) => sameTransform(o, s) && sameGeometry(o, s) && sameInstances(o, s) && sameMaterials(o, s);
  // as an occluder: instance re-layouts declared stable (visible instances stay put) are no motion
  const occluderSame = (o, s) => sameTransform(o, s) && sameGeometry(o, s) && (o.userData.dgyStableInstances === true || sameInstances(o, s));

  // ---------- conservative world boxes ----------
  const sphereBox = (sphere, matrix, out) => tmpSphere.copy(sphere).applyMatrix4(matrix).getBoundingBox(out);
  function instanceUnion(o, out) {
    const g = o.geometry; if (!g.boundingBox) g.computeBoundingBox();
    out.makeEmpty();
    for (let i = 0; i < o.count; i++) { o.getMatrixAt(i, tmpM); tmpM.premultiply(o.matrixWorld); out.union(tmpB2.copy(g.boundingBox).applyMatrix4(tmpM)); }
    return out;
  }
  // where this draw's surface can be (world). Fixed vertices: the exact geometry (x instances); animated vertices: an
  // explicitly declared padding or sway reach around it, the spatial index's certified box of a tree batch, or else the
  // volume three's own frustum culling relies on; otherwise unknown (null).
  const reachOf = o => {
    if (!swayReach) return NaN;
    let r = 0;
    for (const m of materialsOf(o)) { if (!m || vertexSpeed(m) === 0) continue; const v = swayReach(m); r = Math.max(r, Number.isFinite(v) && v >= 0 ? v : Infinity); }
    return r;
  };
  function drawBox(o, speed, out) {
    const g = o.geometry; if (!g?.attributes?.position || o.isSkinnedMesh || o.isBatchedMesh || o.morphTargetInfluences) return null;
    const wb = o.userData.dgySpatialWorldBounds; // every instance of the batch in every season, wind included
    if (speed !== 0 && wb?.isBox3 && finiteBox(wb) && !g.isInstancedBufferGeometry) return out.copy(wb);
    const reach = reachOf(o), pad = Number.isFinite(o.userData.dgyBoundsPad) ? o.userData.dgyBoundsPad : speed !== 0 && Number.isFinite(reach) ? reach : NaN;
    if (speed === 0 || Number.isFinite(pad)) {
      if (g.isInstancedBufferGeometry) return null; // vertices placed by the shader
      if (o.isInstancedMesh) instanceUnion(o, out);
      else { if (!g.boundingBox) g.computeBoundingBox(); out.copy(g.boundingBox).applyMatrix4(o.matrixWorld); }
      if (!finiteBox(out)) return null;
      return Number.isFinite(pad) && pad > 0 ? out.expandByScalar(pad) : out;
    }
    if (!o.frustumCulled || g.isInstancedBufferGeometry) return null;
    if (o.isInstancedMesh) { if (o.boundingSphere === null) o.computeBoundingSphere(); return sphereBox(o.boundingSphere, o.matrixWorld, out); }
    if (!g.boundingSphere) g.computeBoundingSphere();
    return sphereBox(g.boundingSphere, o.matrixWorld, out);
  }

  // ---------- candidates ----------
  function dirty(id) { const row = (id / TW) | 0; dirtyLo = Math.min(dirtyLo, row); dirtyHi = Math.max(dirtyHi, row); }
  function setBox(id, box) {
    const o = id * 8, c = cands[id];
    boxData[o] = box.min.x; boxData[o + 1] = box.min.y; boxData[o + 2] = box.min.z; boxData[o + 3] = c.active ? 1 : 0;
    boxData[o + 4] = box.max.x; boxData[o + 5] = box.max.y; boxData[o + 6] = box.max.z; boxData[o + 7] = 0;
    c.v = [box.min.x, box.min.y, box.min.z, box.max.x, box.max.y, box.max.z];
    // a verdict can use this box only if it was tested after the upload; frame advances in update()
    since[id] = frame + 1; dirty(id);
  }
  function add(key, object, box, kind) {
    if (idOf.has(key) || cands.length >= cap) return -1;
    const id = cands.length, ok = finiteBox(box);
    const c = { key, object, box: ok ? box : new T.Box3(), active: ok, v: null, kind, s: null };
    cands.push(c); idOf.set(key, id);
    if (object) { object[idKey] = id; c.s = snap(object); }
    stats[kind === 'box' ? 'boxes' : kind]++;
    rows = Math.ceil(cands.length / TW); setBox(id, c.box); stats.candidates = cands.length; return id;
  }
  // registry candidates: the registry's volume holds every layout it certified, a mesh's own surface box (exact geometry,
  // declared sway reach) is often far tighter (frustum spheres of whole batches). Both contain the surface, so the test
  // uses their intersection, measured again whenever the mesh's state changes.
  function tighten(id) {
    const c = cands[id], o = c.object;
    if (!o?.isMesh) return;
    const t = drawBox(o, maxSpeed(o), c.tb || (c.tb = new T.Box3()));
    if (t) t.intersect(c.box);
    setBox(id, t && finiteBox(t) ? t : c.box);
  }
  function deactivate(id) {
    const c = cands[id]; if (!c.active) return;
    c.active = false; boxData[id * 8 + 3] = 0; since[id] = frame + 1; dirty(id); stats.deactivated++;
  }
  // an extra (non-registry) object changed: measure it again, it is tested from the next frame on
  function refresh(id) {
    const c = cands[id], o = c.object;
    if (debug) note(debug.refresh, (!sameTransform(o, c.s) ? 'T' : '') + (!sameGeometry(o, c.s) ? 'G' : '') + (!sameInstances(o, c.s) ? 'I' : '') + (!sameMaterials(o, c.s) ? 'M' : '') + ' ' + label(o));
    snap(o, c.s); stats.refreshed++;
    const box = eligible(o) ? drawBox(o, maxSpeed(o), c.box) : null;
    if (box) { c.box = box; c.active = true; setBox(id, box); } else deactivate(id);
  }
  const sameValues = (v, b) => v && v[0] === b.min.x && v[1] === b.min.y && v[2] === b.min.z && v[3] === b.max.x && v[4] === b.max.y && v[5] === b.max.z;
  // A culled node hides its whole subtree from the main pass: no lights (they light other objects), no LOD objects
  // (updated while traversed), nothing drawn outside the box (points, lines, sprites), nothing animated.
  function subtreeSafe(root) {
    let safe = true;
    root.traverse(o => {
      if (o.isLight || o.isLOD || o.isCamera || o.isSprite || o.isPoints || o.isLine || o.isSkinnedMesh || o.userData.dynamic || o.animations?.length) safe = false;
    });
    return safe;
  }
  // an object whose draw can be skipped when its box is hidden: a plain mesh with nothing else attached to drawing it
  function eligible(o) {
    return o.isMesh && !o.isSkinnedMesh && !o.isBatchedMesh && !o.morphTargetInfluences && !o.userData.dynamic && !o.animations?.length &&
      o.onBeforeRender === defRender && !o.isReflector && !o.userData.rcKind && materialsOf(o).every(m => !!m);
  }

  // ---------- verdicts ----------
  // lvl 2: the camera is inside the still ball (either certificate holds), 1: inside the moving ball
  function hiddenId(id, lvl, ent = entering, rot = rotation) {
    if (!res || id >= res.count || since[id] > res.frame || !cands[id].active) return false;
    const d = res.data, k = id * 4;
    if (d[k] >= 128 && ((rot & 1) || (d[k + 2] & 16)) && (d[k + 2] & ent) === 0) return true;
    return lvl === 2 && d[k + 1] >= 128 && ((rot & 2) || (d[k + 3] & 16)) && (d[k + 3] & ent) === 0;
  }
  // box queries come in bursts (grass cells, water chunks) for one camera state: its level and entering edges are
  // kept while the camera's own transform, near plane and the verdict set stay the same (expiry is checked every time)
  const bq = { res: null, epoch: -1, p: new Float64Array(8), projection: new Float64Array(projectionShape.length).fill(NaN), lvl: 0, ent: 0, rot: 0 };
  function boxLevel() {
    const p = camera.position, q = camera.quaternion, b = bq.p;
    if (bq.res !== res || bq.epoch !== epoch || camera.parent !== null || camera.matrixAutoUpdate !== true || b[0] !== p.x || b[1] !== p.y || b[2] !== p.z ||
      b[3] !== q.x || b[4] !== q.y || b[5] !== q.z || b[6] !== q.w || b[7] !== camera.near ||
      projectionShape.some((key, i) => camera.projectionMatrix.elements[key] !== bq.projection[i])) {
      camera.updateMatrixWorld(); eyeNow.setFromMatrixPosition(camera.matrixWorld); forward(camera.matrixWorld, fwdNow);
      bq.lvl = validLevel(eyeNow, fwdNow, -Infinity); bq.ent = bq.lvl ? enteringEdges(camera.matrixWorld) : 0; bq.rot = rotationLevels(fwdNow);
      bq.res = res; bq.epoch = epoch; b[0] = p.x; b[1] = p.y; b[2] = p.z; b[3] = q.x; b[4] = q.y; b[5] = q.z; b[6] = q.w; b[7] = camera.near;
      projectionShape.forEach((key, i) => { bq.projection[i] = camera.projectionMatrix.elements[key]; });
    }
    return bq.lvl && nowS() - res.time <= res.life ? bq.lvl : 0;
  }
  // edges of the verdict's drawn rectangle (1 left, 2 right, 4 bottom, 8 top; the screen, or the scissor of a partial
  // render) whose outside the view has turned into by more than a pixel since, or that the rectangle drawn now
  // (nextRect, the screen by default) reaches beyond: verdicts clamped at those edges are not used
  const ray = new T.Vector3(), qRel = new T.Quaternion(), qNow = new T.Quaternion();
  let nextRect = null;
  function enteringEdges(m) {
    if (!res) return 0;
    qRel.copy(res.q).invert().multiply(qNow.setFromRotationMatrix(m));
    const { W, H, fx, fy, ppx, ppy } = res.cam, o = res.cam.vr, n = nextRect || [0, 0, W - 1, H - 1];
    let mask = (n[0] < o[0] ? 1 : 0) | (n[2] > o[2] ? 2 : 0) | (n[1] < o[1] ? 4 : 0) | (n[3] > o[3] ? 8 : 0);
    // Test the current frustum's corners against the old frustum's outside half-spaces. Sampling only the old
    // boundary misses a disjoint view after a large turn (all sampled rays can be behind the new camera).
    for (let j = 0; j < 4; j++) {
      const x = j & 1 ? n[2] + 1 : n[0], y = j & 2 ? n[3] + 1 : n[1];
      ray.set((x - ppx) / fx, (y - ppy) / fy, -1).applyQuaternion(qRel);
      if (ray.z >= 0) return 15;
      const z = -ray.z;
      if (ray.x < (o[0] - ppx) / fx * z - 1e-12) mask |= 1;
      if (ray.x > (o[2] + 1 - ppx) / fx * z + 1e-12) mask |= 2;
      if (ray.y < (o[1] - ppy) / fy * z - 1e-12) mask |= 4;
      if (ray.y > (o[3] + 1 - ppy) / fy * z + 1e-12) mask |= 8;
    }
    return mask;
  }
  const forward = (m, out) => out.set(-m.elements[8], -m.elements[9], -m.elements[10]).normalize();
  function rotationLevels(f) {
    if (!res || f.dot(res.fwd) <= 0) return 0;
    const sn = tmpC.crossVectors(f, res.fwd).length();
    return (sn <= res.sin[0] ? 1 : 0) | (sn <= res.sin[1] ? 2 : 0);
  }
  function validLevel(e, f, now) {
    if (!res || res.epoch !== epoch || camera.near > res.nearMax || now - res.time > res.life ||
      projectionShape.some((key, i) => camera.projectionMatrix.elements[key] !== res.projection[i])) return 0;
    const reusable = rotationLevels(f) | res.independent;
    if (e.distanceTo(res.eye) <= res.eps[1] && reusable) return 2;
    // distance to the eye path of the verdict
    const P = res.path, L2 = P.lengthSq(), ex = e.x - res.eye.x, ey = e.y - res.eye.y, ez = e.z - res.eye.z;
    const t = L2 > 0 ? Math.min(1, Math.max(0, (ex * P.x + ey * P.y + ez * P.z) / L2)) : 0;
    return Math.hypot(ex - t * P.x, ey - t * P.y, ez - t * P.z) <= res.eps[0] && (reusable & 1) ? 1 : 0;
  }
  function whyInvalid(e, f, now) {
    if (!res) return 'no-result';
    if (res.epoch !== epoch) return 'epoch';
    if (camera.near > res.nearMax) return 'near';
    if (projectionShape.some((key, i) => camera.projectionMatrix.elements[key] !== res.projection[i])) return 'projection';
    if (now - res.time > res.life) return 'expired';
    if (!(rotationLevels(f) | res.independent)) return 'turn';
    return 'path';
  }
  function bump(reason, detail = '') { epoch++; res = null; level = 0; stats.live = false; stats.invalidReason = 'reset:' + reason; stats.drops++; stats.lastDrop = reason; stats.lastDropDetail = detail; } // also mid-frame (invalidate)

  // ---------- occluder kind of each draw of the main view ----------
  // colour factors of the material's own blending, as WebGLState.setBlending issues them (null: custom)
  function colourBlend(m) {
    const b = m.blending, pm = m.premultipliedAlpha;
    if (b === T.NoBlending || (b === T.NormalBlending && !m.transparent)) return CB_NONE;
    if (b === T.NormalBlending) return pm ? CB_NORMAL_PM : CB_NORMAL;
    if (b === T.AdditiveBlending) return pm ? CB_ADD_PM : CB_ADD;
    if (b === T.SubtractiveBlending) return CB_SUB;
    if (b === T.MultiplyBlending) return CB_MUL;
    return null;
  }
  const CB_NONE = [T.AddEquation, T.OneFactor, T.ZeroFactor], CB_NORMAL = [T.AddEquation, T.SrcAlphaFactor, T.OneMinusSrcAlphaFactor],
    CB_NORMAL_PM = [T.AddEquation, T.OneFactor, T.OneMinusSrcAlphaFactor], CB_ADD = [T.AddEquation, T.SrcAlphaFactor, T.OneFactor],
    CB_ADD_PM = [T.AddEquation, T.OneFactor, T.OneFactor], CB_SUB = [T.AddEquation, T.ZeroFactor, T.OneMinusSrcColorFactor],
    CB_MUL = [T.AddEquation, T.ZeroFactor, T.SrcColorFactor];
  // alpha factors: [src, dst, constant]
  const A_SRC = [T.OneFactor, T.ZeroFactor, 0], A_SWAY = [T.ZeroFactor, T.ConstantAlphaFactor, SWAY],
    A_ZERO = [T.ZeroFactor, T.ZeroFactor, 0], A_KEEP = [T.ZeroFactor, T.OneFactor, 0], A_MAX = [T.OneFactor, T.OneFactor, 0, T.MaxEquation];
  const usesConstAlpha = f => f === T.ConstantAlphaFactor || f === T.OneMinusConstantAlphaFactor;
  function blendAlpha(m, a) {
    if (tune.noBlend) return; // experiments: the classification without its blend state
    const cb = colourBlend(m);
    if (cb) { state.setBlending(T.CustomBlending, cb[0], cb[1], cb[2], a[3] || T.AddEquation, a[0], a[1], BLACK, a[2]); return; }
    // custom colour blending keeps its own equation, factors and constant colour
    if (a === A_SWAY && (usesConstAlpha(m.blendSrc) || usesConstAlpha(m.blendDst))) a = A_ZERO; // its constant alpha is taken
    state.setBlending(T.CustomBlending, m.blendEquation, m.blendSrc, m.blendDst, a[3] || T.AddEquation, a[0], a[1], m.blendColor,
      a === A_SWAY ? a[2] : m.blendAlpha);
  }
  // has this object moved within the last `cooldown` frames (decided once per frame, at its first draw)
  function moving(o) {
    let r = o[REC];
    // first sight: on probation for `cooldown` frames (checked at each draw meanwhile), so that something that moves
    // all along (a bird, a flag) never becomes a trusted occluder whose first move would drop every verdict
    if (!r) { r = o[REC] = snap(o); r.moved = frame; r.f = frame; }
    else if (r.f !== frame) { r.f = frame; if (r.wi < 0 && !occluderSame(o, r)) { snap(o, r); r.moved = frame; r.everMoved = true; } }
    return frame - r.moved < cooldown;
  }
  function untrusted(o, m, kind) {
    if (debug) note(debug.holes[kind] || (debug.holes[kind] = {}), label(o) + ' ' + m.type.replace('Material', '') + ':' + recipeKey(m));
    stats.holeKinds[kind] = (stats.holeKinds[kind] || 0) + 1;
  }
  function project(box, view, proj, W, H, out) {
    // pixel rectangle and view-depth range of a world box; the whole screen when it reaches behind the eye
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity, z0 = Infinity, z1 = 0, behind = false;
    const mn = box.min, mx = box.max;
    for (let i = 0; i < 8; i++) {
      tmpV.set(i & 1 ? mx.x : mn.x, i & 2 ? mx.y : mn.y, i & 4 ? mx.z : mn.z, 1).applyMatrix4(view);
      const z = -tmpV.z; z0 = Math.min(z0, z); z1 = Math.max(z1, z);
      if (z <= 1e-3) { behind = true; continue; }
      tmpV.applyMatrix4(proj);
      const sx = (tmpV.x / tmpV.w * 0.5 + 0.5) * W, sy = (tmpV.y / tmpV.w * 0.5 + 0.5) * H;
      x0 = Math.min(x0, sx); x1 = Math.max(x1, sx); y0 = Math.min(y0, sy); y1 = Math.max(y1, sy);
    }
    if (behind) { x0 = 0; y0 = 0; x1 = W; y1 = H; z0 = 0; }
    out.x0 = Math.max(0, Math.floor(x0) - 1); out.y0 = Math.max(0, Math.floor(y0) - 1);
    out.x1 = Math.min(W - 1, Math.ceil(x1) + 1); out.y1 = Math.min(H - 1, Math.ceil(y1) + 1);
    out.z0 = Math.max(0, z0); out.z1 = z1; out.area = (out.x1 - out.x0 + 1) * (out.y1 - out.y0 + 1);
    return out.x1 >= out.x0 && out.y1 >= out.y0 && z1 > 0;
  }
  // a depth-only draw that is not fixed: its screen rectangle x depth range does not occlude
  function addHole(o, speed) {
    const W = target.width, H = target.height, q = DEPTH_ULP * 2 / Math.abs(camera.projectionMatrix.elements[14]);
    const h = holes[holeN] || (holes[holeN] = {});
    const box = drawBox(o, speed, tmpBox);
    if (!box) { h.x0 = 0; h.y0 = 0; h.x1 = W - 1; h.y1 = H - 1; h.z0 = 0; h.z1 = Infinity; h.area = W * H; holeN++; }
    else if (project(box, camera.matrixWorldInverse, camera.projectionMatrix, W, H, h)) {
      h.z0 = Math.max(0, h.z0 - 0.01 - 2e-4 * h.z0 - q * h.z0 * h.z0); h.z1 += 0.01 + 2e-4 * h.z1 + q * h.z1 * h.z1; holeN++;
    }
  }
  const unite = (a, b) => {
    a.x0 = Math.min(a.x0, b.x0); a.y0 = Math.min(a.y0, b.y0); a.x1 = Math.max(a.x1, b.x1); a.y1 = Math.max(a.y1, b.y1);
    a.z0 = Math.min(a.z0, b.z0); a.z1 = Math.max(a.z1, b.z1); a.area = (a.x1 - a.x0 + 1) * (a.y1 - a.y0 + 1);
  };
  // more holes than uniforms: unions are still conservative. Many: one union per screen tile of the rectangle centre;
  // then merge the pair whose union grows least.
  function mergeHoles(W, H) {
    if (holeN > MAX_HOLES * 4) {
      const tiles = new Array(MAX_HOLES).fill(-1); let n = 0;
      for (let i = 0; i < holeN; i++) {
        const h = holes[i], t = Math.min(3, ((h.x0 + h.x1) * 2 / W) | 0) + 4 * Math.min(3, ((h.y0 + h.y1) * 2 / H) | 0);
        if (tiles[t] < 0) { tiles[t] = n; const d = holes[n]; holes[n] = h; holes[i] = d; n++; } else unite(holes[tiles[t]], h);
      }
      holeN = n;
    }
    while (holeN > MAX_HOLES) {
      let bi = 0, bj = 1, best = Infinity;
      for (let i = 0; i < holeN; i++) for (let j = i + 1; j < holeN; j++) {
        const a = holes[i], b = holes[j];
        const u = (Math.max(a.x1, b.x1) - Math.min(a.x0, b.x0) + 1) * (Math.max(a.y1, b.y1) - Math.min(a.y0, b.y0) + 1) - a.area - b.area;
        if (u < best) { best = u; bi = i; bj = j; }
      }
      const b = holes[bj]; unite(holes[bi], b);
      holes[bj] = holes[holeN - 1]; holes[holeN - 1] = b; holeN--;
    }
  }

  // ---------- GL ----------
  function compile(fs) {
    const p = gl.createProgram();
    for (const [type, src] of [[gl.VERTEX_SHADER, VS], [gl.FRAGMENT_SHADER, fs]]) {
      const s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s);
      if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error('frame-occlusion shader: ' + gl.getShaderInfoLog(s));
      gl.attachShader(p, s); gl.deleteShader(s);
    }
    gl.linkProgram(p);
    if (!gl.getProgramParameter(p, gl.LINK_STATUS)) throw new Error('frame-occlusion link: ' + gl.getProgramInfoLog(p));
    const u = {}, n = gl.getProgramParameter(p, gl.ACTIVE_UNIFORMS);
    for (let i = 0; i < n; i++) { const info = gl.getActiveUniform(p, i), name = info.name.replace(/\[0\]$/, ''); u[name] = gl.getUniformLocation(p, info.name); }
    return { p, u };
  }
  function texture(w, h, internal) {
    const t = gl.createTexture(); state.bindTexture(gl.TEXTURE_2D, t, gl.TEXTURE0);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    gl.texStorage2D(gl.TEXTURE_2D, 1, internal, w, h); return t;
  }
  function framebuffer(tex) {
    const f = gl.createFramebuffer(); state.bindFramebuffer(gl.FRAMEBUFFER, f);
    gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, tex, 0);
    if (gl.checkFramebufferStatus(gl.FRAMEBUFFER) !== gl.FRAMEBUFFER_COMPLETE) throw new Error('frame-occlusion: incomplete framebuffer');
    return f;
  }
  function initGL() {
    gpu = { reduce0: compile(REDUCE0), reduce: compile(REDUCE), test: null, testLevels: 0, vao: gl.createVertexArray(),
      levels: [], W: 0, H: 0, box: null, boxRows: 0, out: null, outFb: null, vp: new T.Vector4(),
      hr: new Int32Array(MAX_HOLES * 4), hz: new Float32Array(MAX_HOLES * 2) };
    for (let i = 0; i < slotCount; i++) slots.push({ pbo: gl.createBuffer(), cap: 0, sync: null, bytes: 0, meta: null, riders: null });
  }
  function ensurePyramid(W, H) {
    if (gpu.W === W && gpu.H === H) return;
    for (const l of gpu.levels) { gl.deleteFramebuffer(l.fb); gl.deleteTexture(l.tex); }
    gpu.levels = [];
    for (let L = 0; L < MAX_LEVELS; L++) {
      const s = 2 ** (L + 1), w = Math.ceil(W / s), h = Math.ceil(H / s);
      const tex = texture(w, h, gl.RGBA32F); gpu.levels.push({ w, h, tex, fb: framebuffer(tex) });
      if ((w === 1 && h === 1) || s * 8 >= Math.max(W, H)) break;
    }
    gpu.W = W; gpu.H = H; stats.levels = gpu.levels.length; stats.width = W; stats.height = H;
    if (gpu.testLevels !== gpu.levels.length) {
      if (gpu.test) gl.deleteProgram(gpu.test.p);
      gpu.test = compile(testShader(gpu.levels.length)); gpu.testLevels = gpu.levels.length;
    }
  }
  function ensureCandidateTextures() {
    if (rows > gpu.boxRows) {
      const r = Math.max(rows, Math.min(cap / TW, Math.max(8, gpu.boxRows * 2)));
      if (gpu.box) gl.deleteTexture(gpu.box);
      if (gpu.out) { carrier?.uncarry?.(api); gl.deleteTexture(gpu.out); gl.deleteFramebuffer(gpu.outFb); }
      gpu.box = texture(TW * 2, r, gl.RGBA32F); gpu.boxRows = r;
      gpu.out = texture(TW, r, gl.RGBA8); gpu.outFb = framebuffer(gpu.out);
      dirtyLo = 0; dirtyHi = rows - 1;
    }
    if (dirtyHi >= dirtyLo) {
      state.bindTexture(gl.TEXTURE_2D, gpu.box, gl.TEXTURE0);
      gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, false); gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL, false); gl.pixelStorei(gl.UNPACK_ALIGNMENT, 4);
      gl.pixelStorei(gl.UNPACK_ROW_LENGTH, 0); gl.pixelStorei(gl.UNPACK_SKIP_ROWS, 0); gl.pixelStorei(gl.UNPACK_SKIP_PIXELS, 0);
      const lo = dirtyLo, hi = Math.min(dirtyHi, rows - 1);
      gl.texSubImage2D(gl.TEXTURE_2D, 0, 0, lo, TW * 2, hi - lo + 1, gl.RGBA, gl.FLOAT, boxData, lo * TW * 8);
      dirtyLo = Infinity; dirtyHi = -1;
    }
  }
  function pass(fb, w, h) {
    state.bindFramebuffer(gl.FRAMEBUFFER, fb); state.viewport(gpu.vp.set(0, 0, w, h)); gl.drawArrays(gl.TRIANGLES, 0, 3);
  }
  // verdicts carried for other instances (carrier option of theirs): their test output is read into this instance's
  // pixel-pack buffer behind its own, so both arrive with one readback (a second readback in the same frame waited
  // behind the compositing of the previous frame: ~9 ms against ~2 ms for the first)
  const carried = new Map(); // instance -> { inst, fb, rows, bytes, meta } waiting for this instance's next afterRender
  let pendingCarry = 0; // own tests handed to the carrier and not yet delivered
  let scratch = new Uint8Array(0), reads = 0;
  // pollAt: the point of the frame that reads (0 start, 1 before update), the mean cost of a read at each (ms), and the
  // frames since the other point was last tried
  const PA = { at: 0, pick: 0, cost: [NaN, NaN], since: 0, clock: () => performance.now(), held: false, late: false };
  let readbackRecovery = false;
  const eyeH = new T.Vector3(), fwdH = new T.Vector3();
  function frameMax() { let d = 1 / 30; for (let i = 0; i < Math.min(dtN, 8); i++) d = Math.max(d, dts[i]); return d; }
  // the verdicts in hand came from a camera at rest and still hold two frame intervals from now, with the camera where
  // it is now (a newer verdict set would say the same: what moves does not occlude, and a moved occluder drops them)
  function holding(frames = 2) {
    if (!res || !res.hold || res.epoch !== epoch) return false;
    eyeH.setFromMatrixPosition(camera.matrixWorld); forward(camera.matrixWorld, fwdH);
    return !!(rotationLevels(fwdH) & 2) && validLevel(eyeH, fwdH, nowS() + frames * frameMax()) === 2;
  }
  function accept(m, data, late = false) {
    res = { ...m, data }; stats.resolved++;
    // latency: frames from the test to the first frame that uses it (poll() runs before that frame's update()); not of a
    // read held back while the verdicts in hand held (late)
    if (!late) lat[latN++ & 15] = (autoPoll ? frame : frame + 1) - m.frame; latMax = 1; for (let i = 0; i < Math.min(latN, 16); i++) latMax = Math.max(latMax, lat[i]);
    let h = 0, hs = 0, independent = 0, hi = 0;
    for (let i = 0; i < m.count; i++) {
      const k = i * 4;
      if (data[k] >= 128) { h++; if (data[k + 2] & 16) { independent |= 1; hi++; } }
      if (data[k + 1] >= 128 && (data[k + 3] & 16)) independent |= 2;
      if (data[k] >= 128 || data[k + 1] >= 128) hs++;
    }
    res.independent = independent; stats.hiddenResults = h; stats.hiddenStill = hs; stats.rotationIndependent = hi;
  }
  const lose = list => { if (list) for (const p of list) p.inst.carryLost(); };
  // carrier: hand back what it carries (disabled, failed, disposed); passenger: take back what it handed over
  function release() {
    for (const s of slots) { lose(s.riders); s.riders = null; }
    for (const p of carried.values()) p.inst.carryLost(); carried.clear();
    carrier?.uncarry?.(api);
  }
  function poll() {
    let newest = null;
    for (const s of slots) if (s.sync) {
      stats.fencePolls++;
      if (!frameFenceReady(gl, s.sync)) { stats.fenceTimeouts++; continue; }
      gl.deleteSync(s.sync); s.sync = null;
      if (!newest || s.meta.frame > newest.meta.frame) { if (newest) { lose(newest.riders); newest.meta = newest.riders = null; } newest = s; }
      else { lose(s.riders); s.meta = s.riders = null; }
    }
    // A recovered context can receive an old completion notice while the newer one is still cached. Prefer the
    // previous frame's actual bytes in that case too; accepting the older signalled slot would reopen an age-2 gap.
    const recent = readbackRecovery && stalledFrameReadback(slots, autoPoll ? frame : frame + 1, 1);
    if (recent && (!newest || recent.meta.frame > newest.meta.frame)) {
      if (newest) { lose(newest.riders); newest.meta = newest.riders = null; }
      newest = recent; gl.deleteSync(newest.sync); newest.sync = null; stats.recoveredReads++;
    }
    if (!newest) {
      newest = stalledFrameReadback(slots, autoPoll ? frame : frame + 1, readbackRecovery ? 1 : maxFenceFrames);
      if (!newest) return;
      readbackRecovery = true; stats.recoveryMode = true;
      gl.deleteSync(newest.sync); newest.sync = null; stats.recoveredReads++;
    }
    // Once this context has deferred notifications, keep previous-frame recovery armed. A short healthy interval
    // during a long key hold does not mean the browser stopped deferring tasks; disarming reintroduced age-2 gaps.
    // Once a newer buffer is being read, older in-flight buffers cannot improve its verdicts. Retire their fences
    // and notify reflection passengers rather than leave three unusable slots permanently occupied. Commands on
    // a recycled PBO stay ordered by GL; no unfinished bytes from a discarded certificate are ever consumed.
    for (const slot of slots) if (slot !== newest && slot.meta && slot.meta.frame < newest.meta.frame) {
      if (slot.sync) gl.deleteSync(slot.sync);
      lose(slot.riders); slot.sync = slot.meta = slot.riders = null; stats.discardedPending++;
    }
    const t0 = performance.now(), m = newest.meta, riders = newest.riders || [];
    const own = m.epoch === epoch && (!res || m.frame > res.frame), extra = riders.reduce((n, p) => n + p.bytes, 0);
    if (own || extra) {
      const from = own ? 0 : newest.bytes, len = newest.bytes + extra - from;
      if (scratch.length < len) scratch = new Uint8Array(Math.max(len, cap * 8));
      gl.bindBuffer(gl.PIXEL_PACK_BUFFER, newest.pbo); gl.getBufferSubData(gl.PIXEL_PACK_BUFFER, from, scratch, 0, len); gl.bindBuffer(gl.PIXEL_PACK_BUFFER, null); reads++;
      if (own) { const data = bufs[flip ^= 1]; data.set(scratch.subarray(0, newest.bytes)); accept(m, data, PA.late); }
      for (const p of riders) p.inst.carryReceive(p.meta, scratch.subarray(p.off - from, p.off - from + p.bytes), PA.late);
      PA.late = false;
    }
    newest.meta = newest.riders = null; stats.readMs = performance.now() - t0;
  }
  function fail(error) {
    stats.errors++; stats.reason = String(error?.message || error); failed = true; enabled = false; stats.enabled = false; stats.live = false; armed = -1;
    try { release(); } catch (e) { /* the instance is off either way */ }
    console.warn('frame-occlusion disabled:', stats.reason);
  }
  const nowS = () => performance.now() / 1000;
  const inFlight = () => !!res || slots.some(s => s.meta) || pendingCarry > 0;
  const glTexture = t => t && renderer.properties.get(t).__webglTexture;

  const api = {
    stats, support, tune,
    get debug() { return debug; },
    set debug(v) { debug = v ? { holes: {}, refresh: {}, moved: {} } : null; },
    get enabled() { return enabled; },
    set enabled(v) { enabled = !!v && support.supported && !failed; stats.enabled = enabled; if (!enabled) { armed = -1; release(); } api.invalidate(); },
    /** Paused by the page's own policy (light views, where its fixed cost per frame exceeds what it culls): no tests,
     * reads or verdicts while gated, independent of enabled. */
    get gated() { return gated; },
    set gated(v) { v = !!v; if (v === gated) return; gated = v; stats.gated = v; if (v) { armed = -1; release(); } bump(v ? 'gated' : 'ungated'); },
    /** Every certified static object of an occlusion-scene-registry (cheap checks at use, its isCurrent on a rolling schedule). */
    addRegistry(reg = registry) {
      let n = 0;
      for (const [object, box] of reg.bounds) {
        if (object.isMesh ? !eligible(object) : !subtreeSafe(object)) continue;
        const id = add(object, object, box, 'reg');
        if (id >= 0) { n++; if (cands[id].active) tighten(id); }
      }
      return n;
    },
    /** Every drawable mesh under root (not under skip roots, not yet a candidate) whose surface has a conservative box. */
    addScene(root, { skip = [] } = {}) {
      const stop = new Set(skip.filter(Boolean)); let n = 0;
      root.updateWorldMatrix(true, true);
      const walk = o => {
        if (stop.has(o)) return;
        if (!idOf.has(o) && eligible(o)) {
          const box = drawBox(o, maxSpeed(o), new T.Box3());
          // instanced batches that are still empty become candidates too; they are measured once they change
          if (box || (o.isInstancedMesh && o.count === 0)) { if (add(o, o, box, 'objects') >= 0) n++; }
        }
        for (const c of o.children) walk(c);
      };
      walk(root);
      return n;
    },
    removeObject(object) { const id = idOf.get(object); if (id !== undefined) deactivate(id); },
    /** Carrier side: read another instance's finished test (its output framebuffer: rows, bytes, verdict meta) back
     * together with this instance's own test later this frame. false: this instance does not test this frame (the other
     * one reads its test itself). A newer test of the same instance replaces one not yet read. */
    carry(inst, fb, rows, bytes, meta) {
      api.uncarry(inst);
      if (!enabled || gated || disposed || failed || inst === api || armed !== frame || !cands.length) return false;
      carried.set(inst, { inst, fb, rows, bytes, meta }); return true;
    },
    uncarry(inst) { const old = carried.get(inst); if (old) { carried.delete(inst); inst.carryLost(); } },
    /** Passenger side (carrier option): the verdicts of an earlier test of this instance, read back by its carrier. */
    carryReceive(m, view, late = false) {
      pendingCarry = Math.max(0, pendingCarry - 1);
      if (!enabled || gated || disposed || m.epoch !== epoch || (res && m.frame <= res.frame)) return;
      const data = bufs[flip ^= 1]; data.set(view.subarray(0, Math.min(view.length, data.length))); accept(m, data, late);
    },
    carryLost() { pendingCarry = Math.max(0, pendingCarry - 1); },
    /** With autoPoll off: read the newest finished verdicts (if any); call it once a frame before update(), at a
     * point where the GPU process has little queued (the start of the frame, before anything is drawn). */
    poll() { if (enabled && !gated && !disposed && gpu) try { poll(); } catch (error) { fail(error); } },
    /** With autoPoll off, instead of poll(): call it at the frame's two candidate points, 0 at its very start and 1 right
     * before update() (after the frame's logic). It reads at one of them: the one where reading has been cheaper, the
     * other one being tried again every 30 frames (every 240 while it is far worse). The read waits until the GPU process
     * has worked through what is queued before it, and which point finds less queued depends on the browser: whether it
     * presents the previous frame then (headless Chrome reads every presented frame back, ~10 ms), or the tail of the
     * previous frame's commands is still being worked through (at the start). */
    /** The clock pollAt times reads with (wall time; a page that fakes performance.now() supplies the real one). */
    set costClock(f) { PA.clock = f; },
    pollAt(point) {
      if (!enabled || gated || disposed || !gpu) return;
      if (point === 0) {
        const o = PA.at ^ 1, far = PA.cost[o] > 2 * PA.cost[PA.at] + 1;
        PA.pick = ++PA.since >= (Number.isNaN(PA.cost[o]) ? 8 : far ? 240 : 30) ? o : PA.at;
        if (PA.pick !== PA.at) PA.since = 0;
        // verdicts of a camera at rest that still hold: decided at 1, where the camera of this frame is known
        PA.held = holding() && !slots.some(x => x.riders); if (PA.held || PA.pick !== 0) return;
      } else if (PA.held) {
        PA.held = false;
        if (holding() && !slots.some(x => x.riders)) { stats.holds++; PA.late = true; return; }
      } else if (PA.pick !== 1) return;
      const r0 = reads, t0 = PA.clock();
      try { poll(); } catch (error) { fail(error); return; }
      if (reads === r0) return;
      const d = PA.clock() - t0, c = PA.cost;
      c[point] = Number.isNaN(c[point]) ? d : c[point] + (d - c[point]) * (point === PA.at ? 0.1 : 0.3);
      if (c[PA.at ^ 1] < 0.85 * c[PA.at]) PA.at ^= 1;
      stats.pollAt = PA.at; stats.pollCost = [+c[0].toFixed(2), +c[1].toFixed(2)];
    },
    /** Before the main render: mainTarget is the render target it draws into (alpha channel, depth texture); drawRect:
     * [x0, y0, x1, y1] (pixels, GL origin, inclusive) when the render will cover only that part of it (scissor). */
    update(viewCamera = camera, mainTarget = null, drawRect = null) {
      const t0 = performance.now(); stats.tested = stats.culled = stats.boxCulled = 0; stats.live = false; armed = -1;
      if (!enabled || disposed || viewCamera !== camera) return stats;
      try {
        frame++;
        const now = nowS(), lastNow0 = lastNow; if (lastNow >= 0) dts[dtN++ & 7] = Math.min(0.25, Math.max(0, now - lastNow)); lastNow = now;
        eye.setFromMatrixPosition(camera.matrixWorld);
        if (haveLast) {
          const d = eye.distanceTo(lastEye);
          // a jump (teleport, scripted cut) is not a speed: forget the motion history and every verdict
          if (d > cutDistance) { dispN = 0; disp.fill(0); vel.fill(0); turn.fill(0); grow.fill(0); bump('camera cut'); }
          else { const k = dispN & 7, dt = lastNow0 >= 0 ? now - lastNow0 : 0; dispN++; disp[k] = d;
            if (dt > 1e-4) { vel[k * 3] = (eye.x - lastEye.x) / dt; vel[k * 3 + 1] = (eye.y - lastEye.y) / dt; vel[k * 3 + 2] = (eye.z - lastEye.z) / dt; }
            else vel.copyWithin(k * 3, ((k + 7) & 7) * 3, ((k + 7) & 7) * 3 + 3);
            turn[k] = Math.asin(Math.min(1, tmpC.crossVectors(forward(camera.matrixWorld, fwd), lastFwd).length()));
            if (fwd.dot(lastFwd) < 0) turn[k] = Math.PI - turn[k]; grow[k] = lastNear > 0 ? Math.max(0, camera.near / lastNear - 1) : 0; }
        }
        lastEye.copy(eye); forward(camera.matrixWorld, fwd); lastFwd.copy(fwd); lastNear = camera.near; haveLast = true;
        if (gpu && autoPoll && !gated) poll();
        // trusted occluders of recent frames that moved, changed shape or left the scene: their depth no longer holds.
        // Objects seen moving before are checked every frame, the others in turn (watchPerFrame a frame): one that
        // starts to move for the first time may occlude with its old depth for a few frames.
        watchKeep = latMax + 3; stats.watch = [watchMoved.length, watchStill.length];
        for (let i = 0; i < watchMoved.length;) if (watchOne(watchMoved, i)) i++;
        for (let n = Math.min(watchPerFrame, watchStill.length); n > 0 && watchStill.length; n--) {
          if (watchCursor >= watchStill.length) watchCursor = 0;
          if (watchOne(watchStill, watchCursor)) watchCursor++;
        }
        // registry candidates: full re-certification on a rolling schedule (cheap checks run at every use)
        if (registry && cands.length) for (let n = 0; n < verifyPerFrame; n++) {
          const id = verifyCursor++ % cands.length, c = cands[id];
          if (c.active && c.kind === 'reg' && (registry.bounds.get(c.object) !== c.box || !registry.isCurrent(c.object))) deactivate(id);
        }
        // extra objects: a changed one is measured again (at use, a hidden one is checked before it is skipped)
        if (cands.length) for (let n = 0; n < refreshPerFrame; n++) {
          const id = refreshCursor++ % cands.length, c = cands[id];
          if (c.kind === 'objects' && c.object && !sameState(c.object, c.s)) refresh(id);
        }
        level = 0; nextRect = drawRect;
        if (res) {
          stats.resultAge = frame - res.frame;
          level = validLevel(eye, fwd, now); stats.invalidReason = level ? '' : whyInvalid(eye, fwd, now); stats.live = level > 0; stats.level = level; if (!level) stats.expired++;
          entering = level ? enteringEdges(camera.matrixWorld) : 0; rotation = rotationLevels(fwd); stats.entering = entering;
        }
        if (!res) stats.invalidReason = 'no-result';
        stats.pending = 0; stats.oldestPending = 0;
        for (const s of slots) if (s.sync) { stats.pending++; stats.oldestPending = Math.max(stats.oldestPending, frame - s.meta.frame); }
        // the main render that follows classifies its draws
        target = mainTarget && mainTarget.depthTexture && mainTarget.texture ? mainTarget : null;
        holeN = 0; motSpeed = motWind = 0; stats.holeKinds = {};
        const d = stats.draws; d.fixed = d.sway = d.untrusted = d.keep = d.rect = 0;
        // gated: the bookkeeping above goes on (motion history, moved occluders, changed candidates), so that it can
        // resume at once; only the test is left out
        if (target && !gated) armed = frame;
      } catch (error) { fail(error); }
      stats.updateMs = performance.now() - t0; return stats;
    },
    /** renderer.dgyDrawClass(object, material, camera), right after three has set the draw's material state. */
    classify(o, m, viewCamera) {
      if (armed !== frame || viewCamera !== camera || renderer.getRenderTarget() !== target) return;
      const d = stats.draws;
      if (!m.colorWrite) { // alpha cannot be written: a depth-only draw that is not fixed becomes a hole
        if (m.depthWrite && (moving(o) || vertexSpeed(m) > 0)) { untrusted(o, m, 'depth only'); addHole(o, vertexSpeed(m)); d.rect++; }
        return;
      }
      if (!m.depthWrite) { blendAlpha(m, A_KEEP); d.keep++; return; } // the depth (and kind) of what is below stays
      if (m.transparent || m.transmission > 0) { untrusted(o, m, 'see-through'); blendAlpha(m, A_ZERO); d.untrusted++; return; }
      const v = vertexSpeed(m);
      if (v > fastSpeed) { untrusted(o, m, Number.isFinite(v) ? 'fast sway' : 'unknown vertices'); blendAlpha(m, A_ZERO); d.untrusted++; return; }
      if (o.userData.dynamic || moving(o)) { untrusted(o, m, 'moving'); blendAlpha(m, A_ZERO); d.untrusted++; return; }
      const r = o[REC]; r.drawn = frame;
      if (r.wi < 0) { const list = r.everMoved ? watchMoved : watchStill; r.wi = list.length; list.push(o); }
      if (v > 0) { if (speedCache.get(m).w) motWind = Math.max(motWind, v); else motSpeed = Math.max(motSpeed, v); blendAlpha(m, A_SWAY); d.sway++; return; }
      if (m.alphaToCoverage) blendAlpha(m, A_MAX); // its alpha is the coverage, below 1 at cut-out edges
      else if (colourBlend(m) !== CB_NONE) blendAlpha(m, A_SRC); // a fixed surface that blends its colour: alpha as an opaque one writes it
      d.fixed++;
    },
    /** Call right after renderer.render(scene, camera) into the main target (its depth and colour are resolved).
     * drawn: [x0, y0, x1, y1] (pixels, GL origin, inclusive) when the render covered only that part of the target
     * (scissor); the rest holds older content and does not occlude. */
    afterRender(drawn = null) {
      if (!enabled || gated || disposed || !cands.length || armed !== frame) return;
      armed = -1; valid = drawn;
      const t0 = performance.now();
      const rt = renderer.getRenderTarget();
      if (!rt || rt !== target) return;
      const dtex = glTexture(rt.depthTexture), ktex = glTexture(rt.texture);
      if (!dtex || !ktex) return;
      const vao = gl.getParameter(gl.VERTEX_ARRAY_BINDING);
      try {
        // errors left by earlier draws of the page (common under ANGLE/D3D11) are not this pass's: clear them before the
        // first check below so that only this pass's own calls can switch it off
        if (!checked) for (let i = 0; i < 16 && gl.getError() !== gl.NO_ERROR; i++);
        if (!gpu) initGL();
        const s = slots.find(x => !x.sync && !x.meta);
        if (!s) { stats.skippedNoSlot++; return; }
        // camera at rest and verdicts that hold 4 more frames: a new test would say the same (one carried for another
        // instance is read now; that one tests again once its own verdicts near their end)
        if (!carried.size && holding(4)) { stats.rests++; return; }
        const W = rt.width, H = rt.height; ensurePyramid(W, H); ensureCandidateTextures();
        stats.holes = holeN; mergeHoles(W, H);
        // life of this verdict set: readback latency + 1.5 frames of use, at the slowest recent frame interval
        // Include work already spent drawing this frame: a first heavy input frame may exceed all preceding idle
        // intervals before its verdict is even issued. Its lifetime must include that elapsed work too.
        const dtMax = Math.max(frameMax(), nowS() - lastNow);
        // the eye path: the latest velocity over the latency and half a frame more (each frame brings newer verdicts);
        // eps: off the path by velocity changes of recent frames (start, stop, turning, head bob) and 10 % speed jitter.
        // "still": a camera at rest (tiny eps); while it moves the path certificate is the only one
        let v = 0, w = 0, g = 0; for (let i = 0; i < Math.min(dispN, 8); i++) { v = Math.max(v, disp[i]); w = Math.max(w, turn[i]); g = Math.max(g, grow[i]); }
        const span = 1.25 * (latMax + tune.life), nPath = latMax + tune.nPath, tPath = nPath * dtMax, k0 = ((dispN + 7) & 7) * 3;
        if (dispN) path.set(vel[k0], vel[k0 + 1], vel[k0 + 2]).multiplyScalar(tPath); else path.set(0, 0, 0);
        let acc = 0;
        for (let j = 1; j < Math.min(dispN, 4); j++) { const a = ((dispN - j + 8) & 7) * 3, b = ((dispN - j + 7) & 7) * 3;
          acc = Math.max(acc, Math.hypot(vel[a] - vel[b], vel[a + 1] - vel[b + 1], vel[a + 2] - vel[b + 2])); }
        // (a velocity change so large that it alone needs more than 4 cm makes the path a poor guess: the tube stays narrow
        // and the verdicts expire if the eye leaves it, rather than certify almost nothing for several frames)
        // A resting camera also certifies a small possible first step. The separate, tighter still certificate keeps
        // the stationary view precise; this wider moving certificate is actually GPU-tested, never retroactively
        // granted to old verdicts after a key is pressed.
        const starting = !dispN || disp[(dispN + 7) & 7] <= 0.01;
        const eps = Math.min(epsMax, Math.max(starting ? 0.18 : 0, 0.015 + tune.epsMin + tune.epsPath * path.length() + tune.epsAcc * Math.min(0.04, acc * dtMax * nPath * (nPath + 1) / 2)));
        const epsS0 = Math.max(stillMin, span * v), epsS = epsS0 < eps ? epsS0 : -1;
        const turnM = Math.min(turnMax, Math.max(turnMin, span * w + 0.0175)), turnS = Math.min(turnM, Math.max(stillMin, span * w));
        // the path in camera space: right, up, forward
        pathC.copy(path).applyQuaternion(tmpQ.setFromRotationMatrix(camera.matrixWorld).invert()); pathC.z = -pathC.z;
        stats.eps = eps; stats.epsStill = epsS; stats.path = path.length(); stats.turn = turnM; stats.turnStill = turnS; stats.latency = latMax;
        // later near planes stay below nearMax while the verdict lives; surfaces that could cross one do not occlude
        const nearMax = camera.near * (1 + Math.max(0.01, span * g)), n0 = nearMax + Math.max(0, pathC.z) + eps + 0.01, n0S = nearMax + Math.max(epsS, 0) + 0.01;
        const P = camera.projectionMatrix.elements, fx = P[0] * W / 2, fy = P[5] * H / 2, ppx = (1 - P[8]) * W / 2, ppy = (1 - P[9]) * H / 2;
        // still: the image moves by less than 0.1 px anywhere, so nothing beyond the screen edge can come into view
        const fm = Math.max(fx, fy), rhoMax = Math.hypot(Math.max(ppx, W - ppx), Math.max(ppy, H - ppy));
        const clampStill = epsS >= 0 && epsS * (fm + rhoMax) / n0S + Math.tan(turnS) * (fm + rhoMax) ** 2 / fm < 0.1;
        // a camera at rest (under 0.1 mm and 0.1 mrad over its last 8 frames) with nothing swaying among the occluders: its
        // verdicts live tune.hold frames longer, and no read is taken while they hold (pollAt). Not with swaying
        // occluders: their motion budget would grow with the life and cost more culling than the reads it saves
        const hold = tune.hold > 0 && dispN >= 8 && epsS >= 0 && epsS <= 1e-4 && turnS <= 1e-4 && !(motSpeed > 0) && !(motWind > 0);
        const life = Math.max(starting ? 0.25 : 0, (latMax + tune.life + (hold ? tune.hold : 0)) * dtMax);
        stats.hold = hold; stats.life = life;
        const ws = windScale ? +windScale(life) : 1, wind = ws >= 0 && ws <= 1 ? ws : 1; stats.wind = wind;
        const mot = Math.max(motSpeed, motWind * wind) * life * tune.mot; stats.mot = mot;
        const radial = [rotationIndependentNearDepth(P, nearMax, path.length(), eps, mot), rotationIndependentNearDepth(P, nearMax, 0, Math.max(0, epsS), mot)];
        const VR = valid || [0, 0, W - 1, H - 1]; // the part of the target this render drew (the rest does not occlude)
        // all GL state through three's WebGLState so its caches stay correct
        gl.bindVertexArray(gpu.vao);
        state.setScissorTest(false); state.setBlending(T.NoBlending); state.setCullFace(T.CullFaceNone); state.setPolygonOffset(false);
        state.buffers.depth.setTest(false); state.buffers.depth.setMask(false); state.buffers.color.setMask(true); state.buffers.stencil.setTest(false);
        state.disable(gl.SAMPLE_ALPHA_TO_COVERAGE);
        // experiments: GPU time of the pyramid and of the test, each pass repeated tune.rep times (stats.gpuQ: queries)
        const tq = tune.timeGpu ? gpu.tq || (gpu.tq = gl.getExtension('EXT_disjoint_timer_query_webgl2')) : null, reps = tq ? Math.max(1, tune.rep | 0) : 1;
        const q1 = tq && gl.createQuery(), q0b = tq && gl.createQuery(); if (tq) gl.beginQuery(tq.TIME_ELAPSED_EXT, q1);
        for (let rep = 0; rep < reps; rep++) {
        // pyramid
        let pr = gpu.reduce0; state.useProgram(pr.p);
        state.bindTexture(gl.TEXTURE_2D, dtex, gl.TEXTURE0); state.bindTexture(gl.TEXTURE_2D, ktex, gl.TEXTURE1);
        gl.uniform1i(pr.u.uDepth, 0); gl.uniform1i(pr.u.uKind, 1);
        gl.uniform2i(pr.u.uMax, W - 1, H - 1); gl.uniform2f(pr.u.uPz, P[10], P[14]); gl.uniform2f(pr.u.uNdc, 2 / W, 2 / H);
        gl.uniform3f(pr.u.uObl, P[2] / P[0], P[6] / P[5], P[2] * P[8] / P[0] + P[6] * P[9] / P[5]); gl.uniform3f(pr.u.uK, 0.8, K_MAX, K_FIX);
        gl.uniform4i(pr.u.uValid, VR[0], VR[1], VR[2], VR[3]);
        for (let i = 0; i < holeN; i++) {
          const h = holes[i], k = i * 4; gpu.hr[k] = h.x0; gpu.hr[k + 1] = h.y0; gpu.hr[k + 2] = h.x1; gpu.hr[k + 3] = h.y1;
          gpu.hz[i * 2] = h.z0; gpu.hz[i * 2 + 1] = Math.min(h.z1, 3e38);
        }
        gl.uniform1i(pr.u.uHoles, holeN);
        if (holeN) { gl.uniform4iv(pr.u.uHR, gpu.hr); gl.uniform2fv(pr.u.uHZ, gpu.hz); }
        pass(gpu.levels[0].fb, gpu.levels[0].w, gpu.levels[0].h);
        if (tq && rep === reps - 1) { gl.endQuery(tq.TIME_ELAPSED_EXT); gl.beginQuery(tq.TIME_ELAPSED_EXT, q0b); }
        pr = gpu.reduce; state.useProgram(pr.p); gl.uniform1i(pr.u.uSrc, 0);
        for (let L = 1; L < gpu.levels.length; L++) {
          const src = gpu.levels[L - 1], dst = gpu.levels[L];
          state.bindTexture(gl.TEXTURE_2D, src.tex, gl.TEXTURE0); gl.uniform2i(pr.u.uMax, src.w - 1, src.h - 1); pass(dst.fb, dst.w, dst.h);
        }
        }
        const q2 = tq && gl.createQuery(); if (tq) { gl.endQuery(tq.TIME_ELAPSED_EXT); gl.beginQuery(tq.TIME_ELAPSED_EXT, q2); }
        // one fragment per candidate
        state.bindTexture(gl.TEXTURE_2D, gpu.box, gl.TEXTURE0);
        const units = []; for (let L = 0; L < gpu.levels.length; L++) { state.bindTexture(gl.TEXTURE_2D, gpu.levels[L].tex, gl.TEXTURE0 + 1 + L); units.push(1 + L); }
        const test = tp => {
          state.useProgram(tp.p); gl.uniform1i(tp.u.uBox, 0);
          gl.uniform1iv(tp.u.uH, units); gl.uniform1i(tp.u.uLevels, gpu.levels.length); gl.uniform1i(tp.u.uTW, TW); gl.uniform1i(tp.u.uCount, cands.length);
          gl.uniform2i(tp.u.uScreen, W, H); gl.uniform4i(tp.u.uVR, VR[0], VR[1], VR[2], VR[3]); gl.uniformMatrix4fv(tp.u.uView, false, camera.matrixWorldInverse.elements); gl.uniformMatrix4fv(tp.u.uProj, false, P);
          gl.uniform3f(tp.u.uEye, eye.x, eye.y, eye.z); gl.uniform3f(tp.u.uD, pathC.x, pathC.y, pathC.z); gl.uniform3f(tp.u.uDw, path.x, path.y, path.z);
          // principal point and focal lengths of this projection, in pixels
          gl.uniform2f(tp.u.uPP, ppx, ppy); gl.uniform2f(tp.u.uFxy, fx, fy); gl.uniform1f(tp.u.uF, fm);
          gl.uniform2f(tp.u.uEps2, eps, epsS); gl.uniform2f(tp.u.uN02, n0, n0S);
          gl.uniform2f(tp.u.uRadial2, Math.min(1e30, radial[0]), Math.min(1e30, radial[1]));
          gl.uniform4f(tp.u.uRot, Math.cos(turnM), Math.sin(turnM), Math.cos(turnS), Math.sin(turnS)); gl.uniform1f(tp.u.uClampStill, clampStill ? 1 : 0);
          gl.uniform1f(tp.u.uClampEdge, edgeClamp ? 1 : 0); gl.uniform1i(tp.u.uRT, tune.rt); gl.uniform1f(tp.u.uEarly, tune.early ? 1 : 0);
          gl.uniform1f(tp.u.uMot, mot); gl.uniform1f(tp.u.uQ, DEPTH_ULP * 2 / Math.abs(P[14]));
        };
        if (debug) { // the same test with its numbers (float target, read back at once: diagnostics only)
          if (!gpu.dbg || gpu.dbg.levels !== gpu.levels.length || gpu.dbg.rows < gpu.boxRows) {
            if (gpu.dbg) { gl.deleteProgram(gpu.dbg.prog.p); gl.deleteTexture(gpu.dbg.tex); gl.deleteFramebuffer(gpu.dbg.fb); }
            const tex = texture(TW, gpu.boxRows, gl.RGBA32F);
            gpu.dbg = { prog: compile(testShader(gpu.levels.length, true)), levels: gpu.levels.length, rows: gpu.boxRows, tex, fb: framebuffer(tex) };
          }
          test(gpu.dbg.prog); pass(gpu.dbg.fb, TW, rows);
          const data = new Float32Array(TW * rows * 4); gl.readPixels(0, 0, TW, rows, gl.RGBA, gl.FLOAT, data);
          debug.test = { frame, count: cands.length, data };
        }
        for (let rep = 0; rep < reps; rep++) { test(gpu.test); pass(gpu.outFb, TW, rows); }
        if (tq) { gl.endQuery(tq.TIME_ELAPSED_EXT); stats.gpuQ = [q1, q2, reps, q0b]; }
        const bytes = TW * rows * 4;
        const meta = { frame, time: lastNow, life, eye: eye.clone(), fwd: fwd.clone(), path: path.clone(), q: new T.Quaternion().setFromRotationMatrix(camera.matrixWorld),
          cam: { W, H, fx, fy, ppx, ppy, vr: VR.slice() }, projection: projectionShape.map(key => P[key]), eps: [eps, epsS], sin: [Math.sin(turnM), Math.sin(turnS)], nearMax,
          count: cands.length, epoch, hold };
        if (carrier && carrier.carry(api, gpu.outFb, rows, bytes, meta)) { pendingCarry++; stats.carried = (stats.carried || 0) + 1; stats.issued++; return; }
        // own test output, then that of the instances this one carries (read from their output framebuffers)
        let total = bytes; const riders = [];
        for (const p of carried.values()) { riders.push({ inst: p.inst, meta: p.meta, off: total, bytes: p.bytes, rows: p.rows, fb: p.fb }); total += p.bytes; }
        carried.clear();
        gl.bindBuffer(gl.PIXEL_PACK_BUFFER, s.pbo);
        if (s.cap < total) { s.cap = Math.max(total, gpu.boxRows * TW * 4); gl.bufferData(gl.PIXEL_PACK_BUFFER, s.cap, gl.STREAM_READ); }
        gl.readPixels(0, 0, TW, rows, gl.RGBA, gl.UNSIGNED_BYTE, 0);
        for (const p of riders) { state.bindFramebuffer(gl.FRAMEBUFFER, p.fb); gl.readPixels(0, 0, TW, p.rows, gl.RGBA, gl.UNSIGNED_BYTE, p.off); }
        gl.bindBuffer(gl.PIXEL_PACK_BUFFER, null);
        if (!checked) { checked = true; const e = gl.getError(); if (e !== gl.NO_ERROR) throw new Error('GL error 0x' + e.toString(16)); }
        s.sync = gl.fenceSync(gl.SYNC_GPU_COMMANDS_COMPLETE, 0); s.bytes = bytes; s.meta = meta; s.riders = riders.length ? riders : null;
        stats.issued++;
      } catch (error) { fail(error); }
      finally {
        gl.bindVertexArray(vao);
        renderer.setRenderTarget(rt); // rebinds the main target, its viewport and scissor through three's state
        stats.afterMs = performance.now() - t0;
      }
    },
    /** renderer.dgyMainOccluded: skip this object in the main pass (stats.live is decided in update()). */
    isObjectOccluded(object, viewCamera) {
      if (!level || viewCamera !== camera || !enabled || gated) return false;
      const id = object[idKey];
      if (id === undefined) return false;
      const c = cands[id];
      if (c.object !== object) return false;
      if (!hiddenId(id, level)) return false;
      // a hidden candidate is checked against what was measured every `recheck` frames while it stays hidden (a change in
      // between is drawn that many frames late at most)
      if (frame - checkedAt[id] < recheck) { stats.tested++; stats.culled++; return true; }
      checkedAt[id] = frame;
      if (c.kind === 'objects') {
        // extras: a hidden one that changed since its box was measured is drawn and measured again
        if (!sameState(object, c.s)) { refresh(id); return false; }
      } else {
        if (registry.bounds.get(object) !== c.box) { deactivate(id); return false; }
        if (!sameState(object, c.s)) {
          // registry boxes of instanced trees cover every layout; anything else must still be what was certified
          if (registry.isCurrent(object)) { snap(object, c.s); tighten(id); } else deactivate(id);
          return false;
        }
      }
      stats.tested++; stats.culled++; return true;
    },
    /** Box test (water chunks, mirrors, grass cells). Unknown keys are registered and tested from the next frame on.
     * Usable outside the main render too: validity is checked against the camera's current position. */
    isOccluded(box, viewCamera = camera, key = box) {
      if (!enabled || gated || viewCamera !== camera || !finiteBox(box)) return false;
      const id = idOf.get(key);
      if (id === undefined) { add(key, null, box, 'box'); return false; }
      const c = cands[id];
      if (!sameValues(c.v, box)) { c.box = box; c.active = true; setBox(id, box); return false; }
      if (!res) return false;
      const lvl = boxLevel();
      if (!lvl || !hiddenId(id, lvl, bq.ent, bq.rot)) return false;
      stats.boxCulled++; return true;
    },
    /** Diagnostics: the main target of the last update, and a synchronous readback of pyramid level L (RGBA float). */
    get target() { return target; },
    readLevel(L = 0) {
      const l = gpu?.levels[L]; if (!l) return null;
      const data = new Float32Array(l.w * l.h * 4);
      state.bindFramebuffer(gl.FRAMEBUFFER, l.fb); gl.readPixels(0, 0, l.w, l.h, gl.RGBA, gl.FLOAT, data); state.bindFramebuffer(gl.FRAMEBUFFER, null);
      return { w: l.w, h: l.h, data };
    },
    /** Diagnostics: the latest verdict of a candidate (an object, or the key of a box). */
    verdictOf(objectOrKey) {
      const id = objectOrKey?.[idKey] ?? idOf.get(objectOrKey);
      if (id === undefined) return null;
      const c = cands[id], ok = !!res && id < res.count, rm = ok ? res.data[id * 4 + 2] : -1, rs = ok ? res.data[id * 4 + 3] : -1;
      const t = debug?.test && id < debug.test.count ? debug.test.data.subarray(id * 4, id * 4 + 4) : null;
      return { id, kind: c.kind, active: c.active, since: since[id], resFrame: res ? res.frame : -1, live: stats.live,
        level, hidden: ok && res.data[id * 4] >= 128, hiddenStill: ok && (res.data[id * 4] >= 128 || res.data[id * 4 + 1] >= 128),
        why: rm < 0 ? -1 : res.data[id * 4] >= 128 ? 0 : rm & 15, step: rm < 0 || res.data[id * 4] >= 128 ? -1 : rm >> 4,
        whyStill: rs < 0 ? -1 : res.data[id * 4 + 1] >= 128 ? 0 : rs & 15, stepStill: rs < 0 || res.data[id * 4 + 1] >= 128 ? -1 : rs >> 4,
        edges: ok ? [res.data[id * 4] >= 128 ? rm & 15 : 0, res.data[id * 4 + 1] >= 128 ? rs & 15 : 0] : null, entering,
        rotationIndependent: ok ? [res.data[id * 4] >= 128 && !!(rm & 16), res.data[id * 4 + 1] >= 128 && !!(rs & 16)] : null,
        box: c.v, dbg: t && { frame: debug.test.frame, moving: Math.floor(t[0]), still: Math.round((t[0] % 1) * 128), zb: t[1], far: t[2], R: t[3] } };
    },
    /** Without argument: drop every verdict (scene edit, camera cut). With an object: drop it and its subtree as
     * candidates, and every verdict (it may have been an occluder). */
    invalidate(object) {
      if (object) object.traverse(o => { const id = idOf.get(o); if (id !== undefined) deactivate(id); });
      bump('invalidate');
    },
    dispose() {
      if (disposed) return; release(); disposed = true; enabled = false; stats.enabled = false; armed = -1;
      for (const c of cands) if (c.object && c.object[idKey] !== undefined) delete c.object[idKey];
      if (gpu) {
        for (const l of gpu.levels) { gl.deleteFramebuffer(l.fb); gl.deleteTexture(l.tex); }
        for (const p of [gpu.reduce0, gpu.reduce, gpu.test, gpu.dbg?.prog]) if (p) gl.deleteProgram(p.p);
        if (gpu.dbg) { gl.deleteTexture(gpu.dbg.tex); gl.deleteFramebuffer(gpu.dbg.fb); }
        if (gpu.box) gl.deleteTexture(gpu.box);
        if (gpu.out) { gl.deleteTexture(gpu.out); gl.deleteFramebuffer(gpu.outFb); }
        gl.deleteVertexArray(gpu.vao);
        for (const s of slots) { if (s.sync) gl.deleteSync(s.sync); gl.deleteBuffer(s.pbo); }
      }
      cands.length = 0; idOf.clear(); for (const o of [...watchMoved, ...watchStill]) delete o[REC]; watchMoved.length = watchStill.length = 0; res = null;
    },
  };
  api.classify = api.classify.bind(api);
  return api;
}
