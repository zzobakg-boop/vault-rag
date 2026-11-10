// 홀로그램 도시 — 교과서 150~153쪽(도심·부도심·주거 및 공업 지역·개발 제한 구역, 접근성→지가→경관)을 3D 모식도로.
// 실제 도시가 아니라 교과서 그림을 옮긴 모식도다. 진짜 자료(사진·수치)는 정보 창에서 보여 준다.
// 보기 셋: 경관(price=0) · 지가(땅이 지가만큼 솟음) · 경관 변화(지하철이 놓이면 → 지가↑ → 건물↑ → 부도심)
import * as T from 'three';
import { OrbitControls } from './three/OrbitControls.js';

const SUB = { x: 4.9, z: -4.4 };             // 부도심 자리(도심에서 약 6.6) — 지하철 2호선이 닿는 곳
const SUB_ANG = Math.atan2(SUB.z, SUB.x);
const IND = [0.55 * Math.PI, 0.86 * Math.PI];   // 공업 지역 부채꼴(각도)
const GB = [9.3, 11.6];                      // 개발 제한 구역 띠
const NEWT = { x: -8.8, z: -8.4 };            // 띠 밖 새 아파트 단지(교과서 151쪽 오른쪽 아래 그림)

function rng(seed) { return () => { seed |= 0; seed = seed + 0x6D2B79F5 | 0; let t = Math.imul(seed ^ seed >>> 15, 1 | seed); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
const inInd = (x, z) => { const a = Math.atan2(z, x), r = Math.hypot(x, z); return a > IND[0] && a < IND[1] && r > 5.2 && r < 8.8; };

// 지가(0~1 남짓). t = 부도심으로 가는 지하철이 놓인 정도(0~1)
export function landPrice(x, z, t = 1) {
  const r = Math.hypot(x, z);
  let L = Math.exp(-r / 2.5);
  const ds = Math.hypot(x - SUB.x, z - SUB.z);
  L += 0.55 * t * Math.exp(-(ds * ds) / 2.2);
  L += 0.05 * Math.exp(-Math.abs(r - 4.25) / 0.35);           // 순환 도로를 따라 조금 높다
  const dn = Math.hypot(x - NEWT.x, z - NEWT.z); L += 0.07 * Math.exp(-(dn * dn) / 3);
  if (r > GB[0] && r < GB[1]) L *= 0.3;
  return L;
}

const VS = `
varying vec3 vN; varying vec3 vW; varying vec3 vL; varying vec3 vC;
void main(){
  vec4 lp = vec4(position,1.0); vec3 n = normal; vC = vec3(1.0);
  #ifdef USE_INSTANCING
    lp = instanceMatrix * lp; n = mat3(instanceMatrix) * n;
  #endif
  #ifdef USE_INSTANCING_COLOR
    vC = instanceColor;
  #endif
  vL = position; vL.y -= 0.5; vec4 w = modelMatrix * lp; vW = w.xyz;
  vN = normalize(mat3(viewMatrix) * mat3(modelMatrix) * n);
  gl_Position = projectionMatrix * viewMatrix * w;
}`;
const FS = `
uniform float uOp; uniform float uTime; uniform float uEdge;
varying vec3 vN; varying vec3 vW; varying vec3 vL; varying vec3 vC;
void main(){
  float rim = pow(1.0 - abs(vN.z), 2.0);
  vec3 a = 0.5 - abs(vL);                  // 상자 안 좌표 — 모서리에서 두 축이 0에 가깝다
  float lo = min(a.x, min(a.y, a.z)); float hi = max(a.x, max(a.y, a.z));
  float mid = a.x + a.y + a.z - lo - hi;
  float w = fwidth(mid) * 1.6;
  float edge = uEdge * (1.0 - smoothstep(0.0, w, mid));
  float scan = 0.9 + 0.1 * sin(vW.y * 16.0 - uTime * 1.6);
  vec3 body = vC * (0.22 + 0.5 * rim) * scan;
  vec3 col = mix(body, vC * 1.15 + 0.12, edge);
  gl_FragColor = vec4(col, mix(0.34 + 0.32 * rim, 0.95, edge) * uOp);
}`;
const holoMat = (edge = 1) => new T.ShaderMaterial({
  vertexShader: VS, fragmentShader: FS, transparent: true, depthWrite: false,
  uniforms: { uOp: { value: 1 }, uTime: { value: 0 }, uEdge: { value: edge } }, extensions: { derivatives: true }
});

export function mountHolo(root, data) {
  const stage = root.querySelector('.hg-stage');
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  let renderer;
  try { renderer = new T.WebGLRenderer({ antialias: true, alpha: true }); }
  catch (e) { root.dispatchEvent(new CustomEvent('hg-fail')); return null; }
  renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 1.6));
  stage.prepend(renderer.domElement);
  const scene = new T.Scene();
  const cam = new T.PerspectiveCamera(36, 1, 0.1, 200);
  cam.position.set(15.5, 14.7, 17.5);   // 학습지 본문 폭(768px)에서 «도심» 핀이 위로 잘려 시제품보다 1.2 올려 본다(2026-11-10)
  const ctl = new OrbitControls(cam, renderer.domElement);
  ctl.target.set(0, 2.6, 0); ctl.enableDamping = true; ctl.enableZoom = false; ctl.enablePan = false;
  ctl.minPolarAngle = 0.25; ctl.maxPolarAngle = 1.38; ctl.minDistance = 9; ctl.maxDistance = 42;
  ctl.autoRotate = !reduce; ctl.autoRotateSpeed = 0.35;
  ctl.addEventListener('start', () => { ctl.autoRotate = false; });
  const R = rng(20261110), C = (h) => new T.Color(h);
  const COL = { cbd: C('#6fe7ff'), sub: C('#b5a3ff'), res: C('#ffd27a'), ind: C('#ff9b54'), gb: C('#6fe39c'), new: C('#ffe3a8') };

  // ── 땅: 지가 지형(평소엔 납작, 지가 보기에서 솟는다) ──
  const groundU = { uRaise: { value: 0 }, uHeat: { value: 0 }, uT: { value: 1 }, uTime: { value: 0 } };
  const gGeo = new T.PlaneGeometry(30, 30, 180, 180); gGeo.rotateX(-Math.PI / 2);
  const pos = gGeo.attributes.position, lp0 = new Float32Array(pos.count), lpSub = new Float32Array(pos.count);
  for (let i = 0; i < pos.count; i++) { const x = pos.getX(i), z = pos.getZ(i); lp0[i] = landPrice(x, z, 0); lpSub[i] = landPrice(x, z, 1) - lp0[i]; }
  gGeo.setAttribute('aL0', new T.BufferAttribute(lp0, 1)); gGeo.setAttribute('aLs', new T.BufferAttribute(lpSub, 1));
  const ground = new T.Mesh(gGeo, new T.ShaderMaterial({
    uniforms: groundU, transparent: true, depthWrite: false, extensions: { derivatives: true },
    vertexShader: `uniform float uRaise; uniform float uT; attribute float aL0; attribute float aLs; varying float vL; varying vec3 vW;
      void main(){ vL = aL0 + aLs*uT; vec3 p = position; p.y += uRaise * vL * 6.5; vW = p; gl_Position = projectionMatrix*modelViewMatrix*vec4(p,1.0);} `,
    fragmentShader: `uniform float uRaise; uniform float uHeat; varying float vL; varying vec3 vW;
      vec3 ramp(float t){ t=clamp(t,0.,1.); vec3 a=vec3(.07,.23,.48), b=vec3(.12,.65,.84), c=vec3(.5,.94,1.), d=vec3(1.,.97,.76);
        return t<.33? mix(a,b,t/.33) : t<.66? mix(b,c,(t-.33)/.33) : mix(c,d,(t-.66)/.34); }
      void main(){ float r = length(vW.xz); if (r > 14.5) discard;
        vec2 g = abs(fract(vW.xz) - .5) / fwidth(vW.xz); float line = 1. - min(min(g.x, g.y), 1.);
        float fade = 1. - smoothstep(11.5, 14.5, r);
        vec3 base = vec3(.06,.32,.42);
        float zone = 0.;
        vec3 tint = r < 4. ? vec3(.43,.9,1.) : (r > 9.3 && r < 11.6) ? vec3(.43,.89,.61) : r < 9.3 ? vec3(1.,.82,.48) : vec3(.3,.5,.6);
        vec3 col = mix(base * (.35 + line * 1.3) + tint * (r > 9.3 && r < 11.6 ? .22 : .07), ramp(sqrt(vL)) * (.45 + line * .9) * (1. - .55 * (1. - uRaise)), uHeat);
        gl_FragColor = vec4(col, (.55 + line * .45) * fade * (.6 + .4 * uHeat)); }`
  }));
  scene.add(ground);

  // ── 건물(인스턴스) ──
  const box = new T.BoxGeometry(1, 1, 1); box.translate(0, 0.5, 0);
  const items = []; // {x,z,w,d,h,rot,col,zone,h0}
  const add = (o) => items.push(o);
  // 도심
  for (let x = -3.6; x <= 3.6; x += 0.66) for (let z = -3.6; z <= 3.6; z += 0.66) {
    const jx = x + (R() - .5) * .16, jz = z + (R() - .5) * .16, r = Math.hypot(jx, jz);
    if (r > 3.7 || R() > 0.86) continue;
    add({ x: jx, z: jz, w: .36 + R() * .16, d: .36 + R() * .16, h: 1.1 + 8.6 * Math.exp(-r / 1.75) * (.55 + .45 * R()), col: COL.cbd, zone: 'cbd' });
  }
  // 부도심(지하철이 놓이기 전 h0 → 놓인 뒤 h)
  for (let x = SUB.x - 1.7; x <= SUB.x + 1.7; x += 0.62) for (let z = SUB.z - 1.7; z <= SUB.z + 1.7; z += 0.62) {
    const jx = x + (R() - .5) * .14, jz = z + (R() - .5) * .14, ds = Math.hypot(jx - SUB.x, jz - SUB.z);
    if (ds > 1.75 || R() > 0.84) continue;
    add({ x: jx, z: jz, w: .36 + R() * .14, d: .36 + R() * .14, h: 0.9 + 4.9 * Math.exp(-ds / 0.85) * (.55 + .45 * R()), h0: .2 + R() * .22, col: COL.sub, zone: 'sub' });
  }
  // 주거 및 공업 지역
  for (let x = -9; x <= 9; x += 0.7) for (let z = -9; z <= 9; z += 0.7) {
    const r = Math.hypot(x, z); if (r < 4.6 || r > 8.9) continue;
    if (Math.hypot(x - SUB.x, z - SUB.z) < 2.1) continue;
    const jx = x + (R() - .5) * .2, jz = z + (R() - .5) * .2;
    if (inInd(jx, jz)) { if (R() < .42) add({ x: jx, z: jz, w: .8 + R() * .4, d: .5 + R() * .3, h: .32 + R() * .2, col: COL.ind, zone: 'ind', rot: Math.atan2(jz, jx) }); continue; }
    const block = (Math.floor(x / 2.1) + Math.floor(z / 2.1)) & 1;   // 아파트 단지와 단독 주택 동네가 덩어리로 갈린다
    if (block && R() < .5) add({ x: jx, z: jz, w: .78, d: .2, h: .85 + R() * .6, col: COL.res, zone: 'res', rot: Math.atan2(jz, jx) + Math.PI / 2 });
    else if (R() < .5) add({ x: jx, z: jz, w: .24, d: .24, h: .18 + R() * .2, col: COL.res, zone: 'res' });
  }
  // 띠 밖 새 아파트 단지
  for (let i = 0; i < 12; i++) add({ x: NEWT.x + (R() - .5) * 2.8, z: NEWT.z + (R() - .5) * 1.2, w: .5, d: .2, h: 1.5 + R() * .7, col: COL.new, zone: 'new', rot: .2 });
  // 개발 제한 구역의 비닐하우스(낮은 상자로)
  for (let i = 0; i < 46; i++) {
    const a = R() * Math.PI * 2, r = GB[0] + .3 + R() * (GB[1] - GB[0] - .6);
    if (Math.sin(a * 3) < .2) continue;
    const x = Math.cos(a) * r, z = Math.sin(a) * r;
    for (let k = 0; k < 3; k++) add({ x: x + Math.cos(a + 1.57) * k * .2, z: z + Math.sin(a + 1.57) * k * .2, w: .55, d: .14, h: .12, col: COL.gb, zone: 'gb', rot: a });
  }
  const mat = holoMat(1);
  const bldg = new T.InstancedMesh(box, mat, items.length);
  const M = new T.Matrix4(), Q = new T.Quaternion(), Y = new T.Vector3(0, 1, 0);
  const setInst = (i, t) => {
    const o = items[i]; const h = o.h0 != null ? o.h0 + (o.h - o.h0) * t : o.h;
    Q.setFromAxisAngle(Y, o.rot || 0); M.compose(new T.Vector3(o.x, 0, o.z), Q, new T.Vector3(o.w, h, o.d)); bldg.setMatrixAt(i, M);
  };
  items.forEach((o, i) => { setInst(i, 1); bldg.setColorAt(i, o.col); });
  scene.add(bldg);
  // 나무(개발 제한 구역) — 원뿔
  const trees = [];
  for (let i = 0; i < 260; i++) { const a = R() * Math.PI * 2, r = GB[0] + R() * (GB[1] - GB[0]); trees.push([Math.cos(a) * r, Math.sin(a) * r, .35 + R() * .4]); }
  const cone = new T.ConeGeometry(.2, 1, 5); cone.translate(0, .5, 0);
  const treeM = holoMat(0); const treeI = new T.InstancedMesh(cone, treeM, trees.length);
  trees.forEach(([x, z, h], i) => { M.compose(new T.Vector3(x, 0, z), Q.identity(), new T.Vector3(1, h, 1)); treeI.setMatrixAt(i, M); treeI.setColorAt(i, COL.gb); });
  scene.add(treeI);
  // 공장 굴뚝
  const chim = items.filter(o => o.zone === 'ind' && R() < .5);
  const cyl = new T.CylinderGeometry(.05, .07, 1, 6); cyl.translate(0, .5, 0);
  const chimI = new T.InstancedMesh(cyl, holoMat(0), chim.length);
  chim.forEach((o, i) => { M.compose(new T.Vector3(o.x + .2, 0, o.z), Q.identity(), new T.Vector3(1, 1.3 + R() * .5, 1)); chimI.setMatrixAt(i, M); chimI.setColorAt(i, COL.ind); });
  scene.add(chimI);

  // ── 도로·지하철 ──
  const lineMat = (c, o) => new T.LineBasicMaterial({ color: c, transparent: true, opacity: o, blending: T.AdditiveBlending, depthWrite: false });
  const ring = (r, c, o) => { const p = []; for (let i = 0; i <= 96; i++) { const a = i / 96 * Math.PI * 2; p.push(new T.Vector3(Math.cos(a) * r, .02, Math.sin(a) * r)); } scene.add(new T.Line(new T.BufferGeometry().setFromPoints(p), lineMat(c, o))); };
  ring(4.25, 0x9ff3ff, .55); ring(9.05, 0x9ff3ff, .35);
  for (let k = 0; k < 6; k++) { const a = k / 6 * Math.PI * 2 + .3; scene.add(new T.Line(new T.BufferGeometry().setFromPoints([new T.Vector3(Math.cos(a) * .6, .02, Math.sin(a) * .6), new T.Vector3(Math.cos(a) * 13, .02, Math.sin(a) * 13)]), lineMat(0x9ff3ff, .28))); }
  // 지하철: 도심을 지나는 1호선(늘 있음)과 부도심으로 가는 2호선(경관 변화에서 그려진다)
  function ribbon(pts, wdt, color, op, y) {
    const v = [], seg = 60, P = [];
    for (let i = 0; i < pts.length - 1; i++) for (let k = 0; k < seg / (pts.length - 1); k++) { const f = k / (seg / (pts.length - 1)); P.push([pts[i][0] + (pts[i + 1][0] - pts[i][0]) * f, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * f]); }
    P.push(pts[pts.length - 1]);
    for (let i = 0; i < P.length - 1; i++) {
      const [x1, z1] = P[i], [x2, z2] = P[i + 1], dx = x2 - x1, dz = z2 - z1, L = Math.hypot(dx, dz) || 1, nx = -dz / L * wdt / 2, nz = dx / L * wdt / 2;
      v.push(x1 + nx, y, z1 + nz, x1 - nx, y, z1 - nz, x2 + nx, y, z2 + nz, x2 + nx, y, z2 + nz, x1 - nx, y, z1 - nz, x2 - nx, y, z2 - nz);
    }
    const g = new T.BufferGeometry(); g.setAttribute('position', new T.Float32BufferAttribute(v, 3));
    const m = new T.Mesh(g, new T.MeshBasicMaterial({ color, transparent: true, opacity: op, depthWrite: false, side: T.DoubleSide }));
    m.userData.segs = P.length - 1; scene.add(m); return m;
  }
  const sub1 = ribbon([[-12.5, 3.2], [0, 0], [12.5, -2.3]], .16, 0xffe27a, .85, .05);
  const sub2 = ribbon([[0, 0], [SUB.x, SUB.z], [SUB.x * 1.8, SUB.z * 1.8]], .16, 0xd9ccff, .95, .055);
  const l2geo = { setDrawRange: (a, n) => sub2.geometry.setDrawRange(0, n) };
  const stn = new T.Mesh(new T.CylinderGeometry(.22, .22, .08, 16), new T.MeshBasicMaterial({ color: 0xd9ccff, transparent: true, opacity: .9 }));
  stn.position.set(SUB.x, .05, SUB.z); scene.add(stn);
  const stn0 = stn.clone(); stn0.material = stn.material.clone(); stn0.material.color.set(0xffe27a); stn0.position.set(0, .05, 0); scene.add(stn0);

  // ── 단면선(지가 보기) ──
  const tr = []; for (let i = 0; i <= 60; i++) { const r = i / 60 * 12.5; tr.push(new T.Vector3(Math.cos(SUB_ANG) * r, 0, Math.sin(SUB_ANG) * r)); }
  const trGeo = new T.BufferGeometry().setFromPoints(tr); const trLine = new T.Line(trGeo, lineMat(0xffffff, 0)); scene.add(trLine);
  const updTransect = (raise, t) => { const p = trGeo.attributes.position; for (let i = 0; i < p.count; i++) { const x = p.getX(i), z = p.getZ(i); p.setY(i, raise * landPrice(x, z, t) * 6.5 + .06); } p.needsUpdate = true; };

  // ── 상태·애니메이션 ──
  const st = { mode: 'scape', raise: 0, raiseTo: 0, heat: 0, heatTo: 0, bop: 1, bopTo: 1, t: 1, tTo: 1 };
  let shift = 0, shiftTo = 0, fly = null;
  const VIEWS = { home: [new T.Vector3(15.5, 14.7, 17.5), new T.Vector3(0, 2.6, 0)],
    sub: [new T.Vector3(SUB.x * 2.55 + 3.2, 5.2, SUB.z * 2.55 + 2.6), new T.Vector3(SUB.x * .45, 2.2, SUB.z * .45)] };
  function flyTo(name) { const [p, t] = VIEWS[name]; if (reduce) { cam.position.copy(p); ctl.target.copy(t); ctl.update(); return; }
    fly = { p0: cam.position.clone(), t0: ctl.target.clone(), p, t, k: 0 }; }
  ctl.addEventListener('start', () => { fly = null; });
  const applyT = (t) => { items.forEach((o, i) => { if (o.h0 != null) setInst(i, t); }); bldg.instanceMatrix.needsUpdate = true;
    groundU.uT.value = t; l2geo.setDrawRange(0, Math.round(sub2.userData.segs * Math.min(1, t * 1.6)) * 6); sub2.material.opacity = .25 + .7 * t; stn.scale.setScalar(.3 + .7 * t); };
  function setMode(m) {
    st.mode = m; root.dataset.mode = m;
    st.raiseTo = m === 'price' ? 1 : 0; st.heatTo = m === 'scape' ? 0 : 1; st.bopTo = m === 'price' ? .16 : 1;
    flyTo(m === 'change' ? 'sub' : 'home');
    if (m !== 'change') st.tTo = 1;
    trLine.material.opacity = m === 'scape' ? 0 : .9;
    if (reduce) { st.raise = st.raiseTo; st.heat = st.heatTo; st.bop = st.bopTo; st.t = st.tTo; applyT(st.t); }
    kick();
  }
  function setT(v) { st.tTo = v; if (reduce) { st.t = v; applyT(v); } kick(); }

  // ── 핀 ──
  const pinWrap = root.querySelector('.hg-pins');
  const pins = (data.zones || []).map(z => {
    const b = document.createElement('button'); b.className = 'hg-pin'; b.type = 'button';
    b.style.setProperty('--pc', z.color); b.innerHTML = `<span class="hg-q">?</span>${z.name}`;
    b.setAttribute('aria-expanded', 'false'); b.addEventListener('click', () => root.dispatchEvent(new CustomEvent('hg-zone', { detail: z.id })));
    pinWrap.appendChild(b); return { z, b, v: new T.Vector3(...z.at) };
  });
  const tmp = new T.Vector3();
  function placePins() {
    const w = stage.clientWidth, h = stage.clientHeight;
    for (const p of pins) {
      tmp.copy(p.v); if (st.raise > .01) tmp.y += st.raise * landPrice(p.v.x, p.v.z, st.t) * 6.5 * (p.z.ride || 0);
      tmp.project(cam); const vis = tmp.z < 1 && Math.abs(tmp.x) < 1.05 && Math.abs(tmp.y) < 1.05;
      const on = vis && st.mode === 'scape'; p.b.style.opacity = on ? 1 : 0; p.b.style.pointerEvents = on ? 'auto' : 'none';
      p.b.style.transform = `translate(${(tmp.x * .5 + .5) * w}px,${(-tmp.y * .5 + .5) * h}px) translate(-50%,-100%)`;
    }
  }

  // ── 크기·그리기 ──
  function view() { const w = stage.clientWidth, h = stage.clientHeight; if (shift > .5) cam.setViewOffset(w, h, shift, 0, w, h); else cam.clearViewOffset(); cam.updateProjectionMatrix(); }
  function resize() { const w = stage.clientWidth, h = stage.clientHeight; renderer.setSize(w, h, false); cam.aspect = w / h;
    cam.fov = w < 520 ? 48 : 41; view(); kick(); }
  new ResizeObserver(resize).observe(stage);
  let running = false, visible = true, last = 0;
  new IntersectionObserver(es => { visible = es[0].isIntersecting; if (visible) kick(); }).observe(stage);
  const ease = (a, b, k) => Math.abs(b - a) < 1e-3 ? b : a + (b - a) * k;
  function frame(now) {
    const dt = Math.min(.05, (now - last) / 1000 || .016); last = now;
    const k = 1 - Math.pow(.002, dt);
    st.raise = ease(st.raise, st.raiseTo, k); st.heat = ease(st.heat, st.heatTo, k); st.bop = ease(st.bop, st.bopTo, k);
    const sPrev = shift; shift = ease(shift, shiftTo, k); if (shift !== sPrev) view();
    if (fly) { fly.k = Math.min(1, fly.k + dt / 1.1); const e = fly.k < .5 ? 2 * fly.k * fly.k : 1 - Math.pow(-2 * fly.k + 2, 2) / 2;
      cam.position.lerpVectors(fly.p0, fly.p, e); ctl.target.lerpVectors(fly.t0, fly.t, e); if (fly.k >= 1) fly = null; }
    const tPrev = st.t; st.t = ease(st.t, st.tTo, k); if (st.t !== tPrev) applyT(st.t);
    groundU.uRaise.value = st.raise; groundU.uHeat.value = st.heat; mat.uniforms.uOp.value = st.bop; treeI.material.uniforms.uOp.value = st.bop; chimI.material.uniforms.uOp.value = st.bop;
    const time = reduce ? 0 : now / 1000; [mat, treeI.material, chimI.material].forEach(m => m.uniforms.uTime.value = time);
    updTransect(st.raise, st.t);
    const moving = ctl.update();
    renderer.render(scene, cam); placePins();
    const settled = st.raise === st.raiseTo && st.heat === st.heatTo && st.bop === st.bopTo && st.t === st.tTo && shift === shiftTo && !fly;
    if (visible && (!settled || moving || ctl.autoRotate || !reduce && st.mode !== 'scape' && false)) requestAnimationFrame(frame); else running = false;
  }
  function kick() { if (!running) { running = true; last = performance.now(); requestAnimationFrame(frame); } }
  ctl.addEventListener('change', kick);
  resize(); applyT(1); setMode('scape');

  // 확대·축소 단추(휠로는 쪽 넘기기를 막지 않는다)
  const zoom = (f) => { const d = cam.position.clone().sub(ctl.target); const L = T.MathUtils.clamp(d.length() * f, ctl.minDistance, ctl.maxDistance); cam.position.copy(ctl.target).add(d.setLength(L)); kick(); };
  // 단면(도심 → 부도심 → 주거 → 개발 제한 구역) 표본: 거리·지가·그 근처 가장 높은 건물
  function profile(t) {
    const out = [];
    for (let i = 0; i <= 50; i++) {
      const r = i / 50 * 12.5, x = Math.cos(SUB_ANG) * r, z = Math.sin(SUB_ANG) * r;
      let h = 0; for (const o of items) { if (Math.hypot(o.x - x, o.z - z) < .62) { const hh = o.h0 != null ? o.h0 + (o.h - o.h0) * t : o.h; if (hh > h) h = hh; } }
      out.push({ r, L: landPrice(x, z, t), h });
    }
    return out;
  }
  const setShift = (px) => { shiftTo = px; if (reduce) { shift = px; view(); } kick(); };
  return { setMode, setT, zoom, profile, setShift, landPrice: (x, z, t) => landPrice(x, z, t), SUB_ANG, stopSpin: () => { ctl.autoRotate = false; }, renderer };
}
