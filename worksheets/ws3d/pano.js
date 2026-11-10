// 360° 둘러보기 — 등장방형(2:1) 사진을 구 안쪽에 입혀 돌려 본다. three.js는 누를 때만 불러온다.
// 쓰는 곳: 사진 카드 아래 «🌐 360° 둘러보기» 단추 → 학습지 안 창(확대 창과 같은 결). 외부 서비스에 기대지 않는다.
import * as T from 'three';
import { OrbitControls } from './three/OrbitControls.js';

export function openPano(host, item) {
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  let r;
  try { r = new T.WebGLRenderer({ antialias: true }); } catch (e) { return null; }
  r.setPixelRatio(Math.min(devicePixelRatio || 1, 1.6));
  host.prepend(r.domElement);
  const scene = new T.Scene(), cam = new T.PerspectiveCamera(72, 1, .1, 100);
  cam.position.set(0, 0, .01);
  const ctl = new OrbitControls(cam, r.domElement);
  ctl.enableZoom = false; ctl.enablePan = false; ctl.rotateSpeed = -.35; ctl.enableDamping = true;
  ctl.autoRotate = !reduce; ctl.autoRotateSpeed = .4;
  ctl.addEventListener('start', () => { ctl.autoRotate = false; });
  const geo = new T.SphereGeometry(10, 64, 32); geo.scale(-1, 1, 1);
  const mesh = new T.Mesh(geo, new T.MeshBasicMaterial({ color: 0x111111 }));
  scene.add(mesh);
  // 처음 볼 방향: u = 사진 가로 위치(도, 0~360·가운데 180). 기본 카메라는 u=270을 본다
  mesh.rotation.y = ((item.u ?? 180) - 270) * Math.PI / 180;
  new T.TextureLoader().load(item.src, tex => { tex.colorSpace = T.SRGBColorSpace; mesh.material = new T.MeshBasicMaterial({ map: tex }); host.classList.add('pn-ready'); kick(); },
    undefined, () => host.classList.add('pn-err'));
  const fit = () => { const w = host.clientWidth, h = host.clientHeight; r.setSize(w, h, false); cam.aspect = w / h; cam.updateProjectionMatrix(); kick(); };
  const ro = new ResizeObserver(fit); ro.observe(host);
  const zoom = f => { cam.fov = T.MathUtils.clamp(cam.fov * f, 35, 95); cam.updateProjectionMatrix(); kick(); };
  let run = false, alive = true;
  function frame() { if (!alive) return; const moving = ctl.update(); r.render(scene, cam); if (moving || ctl.autoRotate) requestAnimationFrame(frame); else run = false; }
  function kick() { if (!run && alive) { run = true; requestAnimationFrame(frame); } }
  ctl.addEventListener('change', kick); fit();
  return { zoom, close() { alive = false; ro.disconnect(); ctl.dispose(); r.dispose(); geo.dispose(); r.domElement.remove(); } };
}
