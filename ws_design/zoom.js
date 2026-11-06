/* 2026-11-06 천대현(사회② 8-1~2 검토판 댓글 «확대 축소는 안되나?») — 그림을 학습지 안에서 크게 보기.
   .ws-fig-zoom 링크를 누르면 새 탭 대신 화면 위 확대 창이 열린다. 휠·두 손가락으로 키우고 끌어서 옮긴다.
   Ctrl/⌘/Shift/가운데 단추 누르기는 예전처럼 새 탭. 스크립트가 안 돌면 링크가 그대로 새 탭으로 연다. */
(function(){
  var box, stage, img, s = 1, x = 0, y = 0, pts = {}, last = null, pinch = null, lastTap = 0, opener = null, lastType = '';
  function build(){
    box = document.createElement('div');
    box.className = 'ws-zoom'; box.hidden = true;
    box.setAttribute('role', 'dialog'); box.setAttribute('aria-modal', 'true'); box.setAttribute('aria-label', '그림 크게 보기');
    box.innerHTML = '<div class="ws-zoom-stage"><img alt=""></div>' +
      '<div class="ws-zoom-bar">' +
      '<button type="button" data-z="out" aria-label="작게">−</button>' +
      '<button type="button" data-z="in" aria-label="크게">+</button>' +
      '<button type="button" data-z="reset">원래대로</button>' +
      '<a class="ws-zoom-tab" target="_blank" rel="noopener">새 탭</a>' +
      '<button type="button" data-z="close" aria-label="닫기">✕ 닫기</button></div>' +
      '<p class="ws-zoom-tip">두 손가락이나 마우스 휠로 키우고, 끌어서 옮겨요</p>';
    document.body.appendChild(box);
    stage = box.querySelector('.ws-zoom-stage'); img = stage.querySelector('img');
    box.querySelector('.ws-zoom-bar').addEventListener('click', function(e){
      var b = e.target.closest('[data-z]'); if (!b) return;
      var z = b.getAttribute('data-z');
      if (z === 'close') close();
      else if (z === 'reset') set(1, 0, 0);
      else zoomAt(z === 'in' ? 1.5 : 1 / 1.5, stage.clientWidth / 2, stage.clientHeight / 2);
    });
    stage.addEventListener('wheel', function(e){
      e.preventDefault();
      var r = stage.getBoundingClientRect();
      zoomAt(Math.exp(-e.deltaY * 0.0025), e.clientX - r.left, e.clientY - r.top);
    }, {passive: false});
    stage.addEventListener('pointerdown', down);
    stage.addEventListener('pointermove', move);
    ['pointerup', 'pointercancel', 'pointerleave'].forEach(function(t){ stage.addEventListener(t, up); });
    stage.addEventListener('dblclick', function(e){
      if (lastType === 'touch') return;
      var r = stage.getBoundingClientRect();
      if (s > 1.01) set(1, 0, 0); else zoomAt(2.5, e.clientX - r.left, e.clientY - r.top);
    });
    document.addEventListener('keydown', function(e){
      if (box.hidden) return;
      if (e.key === 'Escape') close();
      else if (e.key === '+' || e.key === '=') zoomAt(1.5, stage.clientWidth / 2, stage.clientHeight / 2);
      else if (e.key === '-') zoomAt(1 / 1.5, stage.clientWidth / 2, stage.clientHeight / 2);
    });
  }
  function set(ns, nx, ny){
    s = Math.min(8, Math.max(1, ns));
    if (s === 1) { nx = 0; ny = 0; }
    var w = stage.clientWidth, h = stage.clientHeight,
        mx = Math.max(0, (img.offsetWidth * s - w) / 2), my = Math.max(0, (img.offsetHeight * s - h) / 2);
    x = Math.min(mx, Math.max(-mx, nx)); y = Math.min(my, Math.max(-my, ny));
    img.style.transform = 'translate(' + x + 'px,' + y + 'px) scale(' + s + ')';
    stage.style.cursor = s > 1 ? 'grab' : 'zoom-in';
  }
  function zoomAt(f, cx, cy){
    var ns = Math.min(8, Math.max(1, s * f)), k = ns / s;
    var ox = cx - stage.clientWidth / 2, oy = cy - stage.clientHeight / 2;
    set(ns, ox - (ox - x) * k, oy - (oy - y) * k);
  }
  function down(e){
    lastType = e.pointerType;
    stage.setPointerCapture && stage.setPointerCapture(e.pointerId);
    pts[e.pointerId] = {x: e.clientX, y: e.clientY};
    var ids = Object.keys(pts);
    if (ids.length === 2) {
      var a = pts[ids[0]], b = pts[ids[1]];
      pinch = {d: Math.hypot(a.x - b.x, a.y - b.y), s: s};
      last = null;
    } else if (ids.length === 1) {
      last = {x: e.clientX, y: e.clientY};
      var now = Date.now();
      if (e.pointerType === 'touch' && now - lastTap < 300) {
        var r = stage.getBoundingClientRect();
        if (s > 1.01) set(1, 0, 0); else zoomAt(2.5, e.clientX - r.left, e.clientY - r.top);
        lastTap = 0;
      } else lastTap = now;
    }
  }
  function move(e){
    if (!pts[e.pointerId]) return;
    pts[e.pointerId] = {x: e.clientX, y: e.clientY};
    var ids = Object.keys(pts);
    if (ids.length === 2 && pinch) {
      var a = pts[ids[0]], b = pts[ids[1]], r = stage.getBoundingClientRect();
      var d = Math.hypot(a.x - b.x, a.y - b.y);
      zoomAt(pinch.s * d / pinch.d / s, (a.x + b.x) / 2 - r.left, (a.y + b.y) / 2 - r.top);
    } else if (ids.length === 1 && last && s > 1) {
      set(s, x + e.clientX - last.x, y + e.clientY - last.y);
      last = {x: e.clientX, y: e.clientY};
      stage.style.cursor = 'grabbing';
    }
  }
  function up(e){
    delete pts[e.pointerId];
    if (Object.keys(pts).length < 2) pinch = null;
    if (!Object.keys(pts).length) { last = null; if (s > 1) stage.style.cursor = 'grab'; }
  }
  /* 링크로 감싸지 않은 정지 그림(교과서 상자·입담·나란히 놓은 그림)도 같은 창으로 연다.
     눌러서 뒤집거나 고르는 블록 안 그림은 건드리지 않는다. */
  var STILL = 'figure.ws-tb-fig img, figure.ipd-fig img, .ws-figrow-item img';
  function open(a){
    if (!box) build();
    var isImg = a.tagName === 'IMG';
    var src = isImg ? (a.currentSrc || a.src) : a.getAttribute('href'), im = isImg ? a : a.querySelector('img');
    img.src = src; img.alt = im ? im.alt : '';
    box.querySelector('.ws-zoom-tab').href = src;
    opener = a; box.hidden = false;
    document.documentElement.classList.add('ws-zoom-open');
    set(1, 0, 0);
    box.querySelector('[data-z="close"]').focus();
  }
  function close(){
    box.hidden = true; pts = {}; pinch = null; last = null;
    document.documentElement.classList.remove('ws-zoom-open');
    if (opener) opener.focus();
  }
  document.addEventListener('click', function(e){
    if (!e.target.closest || e.ctrlKey || e.metaKey || e.shiftKey || e.button !== 0) return;
    var a = e.target.closest('a.ws-fig-zoom');
    if (!a && e.target.matches && e.target.matches(STILL) && !e.target.closest('a, button, label')) a = e.target;
    if (!a) return;
    e.preventDefault(); open(a);
  });
})();
