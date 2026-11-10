/* 다른 창에 갔다 오면 «하던 곳» 안내 (2026-11-10 천대현 «다른 창, 게임, 영상» · «(가)가 가장 현실적»)
   - 아무것도 저장·전송하지 않는다. 다녀온 횟수·시각을 세어 남기지도 않는다.
     위성 딥리서치(2026-11-10 seatwork-engagement): 이탈을 이름과 묶어 저장·전송하면 개인정보 보호법 최소 수집에 걸리고,
     감지·경고가 학습을 올린 실험도 없다. 그래서 학생 본인 화면에 «어디로 돌아오면 되는지»만 알려 준다.
   - 15초 넘게 비웠다가 돌아올 때만 화면 아래에 한 줄을 띄운다. 막지도 꾸짖지도 않는다.
   - 다른 창으로 간 것은 막을 수 없고, 창을 일부만 가린 경우는 못 알아챌 수 있다(visibilitychange 한계). */
(function(){
  var MIN = (window.WS_REFOCUS_MIN_MS != null) ? window.WS_REFOCUS_MIN_MS : 15000;
  var FIELDS = '.blank-input,.essay-input,textarea';
  var CIRC = '①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳㉑㉒㉓㉔㉕㉖㉗㉘㉙㉚';
  var last = null, leftAt = 0, box = null, txt = null, go = null, timer = 0;
  function root(){ return document.querySelector('.container') || document.body; }

  document.addEventListener('focusin', function(e){ var t = e.target; if (t && t.matches && t.matches(FIELDS)) last = t; }, true);
  document.addEventListener('click', function(e){
    var t = e.target && e.target.closest && e.target.closest('.ox-btn,.choice-btn,.pk-b');
    if (t) last = t;
  }, true);

  /* 학습지가 새 창으로 보낸 것(거리뷰·출처 모음 등 target=_blank 링크)은 딴 데 간 것이 아니다 — 누른 직후의 이탈은 세지 않는다(사회 확인 ℹ️2) */
  var linkAt = 0, viaLink = false;
  document.addEventListener('click', function(e){
    var a = e.target && e.target.closest && e.target.closest('a[target="_blank"],a[href^="http"]');
    if (a) linkAt = Date.now();
  }, true);
  function away(){ if (!leftAt){ leftAt = Date.now(); viaLink = (leftAt - linkAt) < 2000; } }
  function back(){ if (!leftAt) return; var d = Date.now() - leftAt, v = viaLink; leftAt = 0; viaLink = false; if (d >= MIN && !v) show(); }
  document.addEventListener('visibilitychange', function(){ if (document.visibilityState === 'hidden') away(); else back(); });
  /* 같은 화면에서 다른 프로그램(게임 창 등)으로 옮겨 가면 창이 가려지지 않아도 blur가 온다. 학습지 안 iframe(영상·3D)으로 간 것은 뺀다. */
  window.addEventListener('blur', function(){ setTimeout(function(){
    var a = document.activeElement; if (a && a.tagName === 'IFRAME') return;
    if (!document.hasFocus()) away();
  }, 0); });
  window.addEventListener('focus', back);

  function stageOf(node){
    var hs = root().querySelectorAll('h2'), s = null;
    for (var i = 0; i < hs.length; i++){
      if (hs[i].compareDocumentPosition(node) & Node.DOCUMENT_POSITION_FOLLOWING) s = hs[i]; else break;
    }
    return s;
  }
  function stageName(h){
    if (!h) return '';
    /* 디자인 v2는 «N단계»를 h2 앞 띠(.v2-kicker)로 옮긴다 — 띠부터 본다 */
    var k = h.previousElementSibling, kt = (k && /v2-kicker/.test(k.className)) ? k.textContent : '';
    var t = h.textContent.replace(/\s+/g, ' ').trim(), m = (kt + ' ' + t).match(/(\d+)\s*단계|STEP\s*0*(\d+)/i);
    if (m) return (m[1] || m[2]) + '단계';
    t = t.replace(/^[^0-9A-Za-z가-힣]+/, '');
    return t.length > 14 ? t.slice(0, 14) + '…' : t;
  }
  function fieldName(el){
    if (!el) return '';
    if (el.classList.contains('blank-input') && !el.classList.contains('activity-input')){
      /* 학생 눈에 보이는 번호는 칸 바로 앞 동그라미 글자다 — 옛 1학기 몇 편은 data-id와 어긋난다(메인 확인 ℹ️1) */
      var p = el.previousSibling, pc = (p && p.nodeType === 3) ? p.nodeValue.replace(/\s+$/, '').slice(-1) : '';
      if (pc && CIRC.indexOf(pc) >= 0) return pc + ' 칸';
      var n = parseInt(el.dataset.id, 10); return (n >= 1 && n <= 30) ? CIRC.charAt(n - 1) + ' 칸' : '빈칸';
    }
    if (el.classList.contains('essay-input') || el.tagName === 'TEXTAREA') return '서술 칸';
    if (el.classList.contains('activity-input')) return '활동 칸';
    if (el.closest('.ox-group')) return 'OX';
    if (el.closest('.ws-pick,.pk-card')) return '카드 고르기';
    return '';
  }
  function isEmpty(el){ return el.matches && el.matches(FIELDS) && !(el.value && el.value.trim()); }
  function fieldsIn(stage){
    /* 접힌 칸·넘김 카드 안 칸도 센다 — 안 보인다고 빼면 «다 채웠어»가 일찍 뜬다 */
    return [].slice.call(root().querySelectorAll(FIELDS)).filter(function(f){ return stageOf(f) === stage; });
  }

  /* 어디로 돌아오면 되나: 하던 칸이 비었으면 그 칸 → 그 단계의 다음 빈칸 → 단계를 다 채웠으면 «설명 같이 듣자» */
  function where(){
    var t = (last && document.contains(last)) ? last : null;
    if (!t){
      var first = [].slice.call(root().querySelectorAll(FIELDS)).filter(isEmpty)[0];
      if (!first) return { done: true, stage: null, target: null };
      return { el: first, stage: stageOf(first), first: true };
    }
    if (isEmpty(t)) return { el: t, stage: stageOf(t) };
    /* 쓰던 칸 뒤의 빈칸 먼저, 없으면 그 단계 앞쪽 빈칸(사회 확인 ℹ️1 — «하던 곳»은 쓰던 자리 다음이어야 말이 맞다) */
    var st = stageOf(t), inSt = fieldsIn(st);
    var after = inSt.filter(function(f){ return (t.compareDocumentPosition(f) & Node.DOCUMENT_POSITION_FOLLOWING) && isEmpty(f); });
    var rest = after.length ? after : inSt.filter(isEmpty);
    /* 앞쪽으로 되돌아가는 칸은 «하던 곳»이 아니라 «아직 빈 곳»이다(메인 확인 ℹ️2) */
    if (rest.length) return { el: rest[0], stage: st, gap: !after.length };
    return { done: true, stage: st, target: st };
  }

  function mk(){
    if (box) return;
    box = document.createElement('div'); box.className = 'ws-rf'; box.hidden = true;
    box.setAttribute('role', 'status'); box.setAttribute('aria-live', 'polite');
    var ic = document.createElement('span'); ic.className = 'ws-rf-i'; ic.setAttribute('aria-hidden', 'true'); ic.textContent = '📍';
    txt = document.createElement('span'); txt.className = 'ws-rf-t';
    go = document.createElement('button'); go.type = 'button'; go.className = 'ws-rf-go';
    var x = document.createElement('button'); x.type = 'button'; x.className = 'ws-rf-x'; x.setAttribute('aria-label', '닫기'); x.textContent = '✕';
    x.addEventListener('click', hide);
    box.appendChild(ic); box.appendChild(txt); box.appendChild(go); box.appendChild(x);
    document.body.appendChild(box);
    document.addEventListener('keydown', function(e){ if (e.key === 'Escape' && !box.hidden) hide(); });
  }
  function put(parts){
    txt.textContent = '';
    parts.forEach(function(p){ var e = document.createElement(p[1] ? 'b' : 'span'); e.textContent = p[0]; txt.appendChild(e); });
  }
  function hide(){ if (box) box.hidden = true; clearTimeout(timer); }
  function flash(el){
    el.classList.add('ws-rf-flash');
    setTimeout(function(){ el.classList.remove('ws-rf-flash'); }, 2000);
  }
  function show(){
    var r = where(); mk();
    var sn = stageName(r.stage), place = sn ? sn + (r.el ? ' · ' : '') : '';
    var target = r.el || r.target;
    if (r.done){
      put(sn ? [['다시 왔네. '], [sn, 1], [' 칸은 다 채웠어 — 지금은 선생님 설명을 같이 듣자.']]
             : [['다시 왔네. 빈칸은 다 채웠어 — 지금은 선생님 설명을 같이 듣자.']]);
      go.textContent = sn ? sn + ' 보기' : '';
    } else {
      put([['다시 왔네. ' + (r.first ? '첫 칸은 ' : r.gap ? '아직 빈 곳은 ' : '하던 곳은 ')], [place + fieldName(r.el), 1], ['이야.']]);
      go.textContent = '그 칸으로';
    }
    go.hidden = !target;
    go.onclick = function(){
      hide(); if (!target) return;
      target.scrollIntoView({ block: 'center', behavior: (window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches) ? 'auto' : 'smooth' });
      if (target.matches && target.matches(FIELDS)) { try { target.focus({ preventScroll: true }); } catch (e) { target.focus(); } }
      flash(target);
    };
    box.hidden = false;
    clearTimeout(timer); timer = setTimeout(hide, 20000);
  }
  window.__wsRefocusShow = show;  /* 시험용 — 수업 동작에는 쓰지 않는다 */
})();
