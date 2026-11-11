/* 카드 고르기(:::인물선택)도 점수에 넣는다 (2026-11-11 천대현 «카드 고르는 것은 맞고 틀리고 카운트가 안 되는데 카운트되도록»)
   - 9/3 처음 설계는 «평가가 아니라 판단을 흔드는 자리»라 점수·저장·제출에서 뺐다. 이 조각이 그 넷을 잇는다.
   - 다 고른 묶음만 센다. 묶음은 다 고른 뒤에만 정답을 여는데, 덜 고른 채로 채점해서 점수가 바뀌면 그걸로 답을 알아낼 수 있다.
   - 카드 덩어리 코드는 건드리지 않는다(발행본마다 판이 조금씩 다르다). 화면의 카드 상태만 읽고 쓴다.
   - 입력칸·data-id·act 번호는 그대로다. 제출 시트는 «__»로 시작하는 칸을 건너뛰므로 시트 모양도 그대로, 총점에만 카드가 더해진다. */
(function(){
  var W = [].slice.call(document.querySelectorAll('.ws-pick'));
  if (!W.length || typeof check !== 'function') return;
  function cards(w){ return [].slice.call(w.querySelectorAll('.pk-card')); }
  var N = W.reduce(function(s, w){ return s + cards(w).length; }, 0);
  function tally(){
    var ok = 0;
    W.forEach(function(w){ if (w.classList.contains('pk-done')) cards(w).forEach(function(c){ if (c.dataset.pick === c.dataset.ans) ok++; }); });
    return ok;
  }
  function el(id){ return document.getElementById(id); }
  function num(id){ var e = el(id); return e ? (parseInt(e.textContent, 10) || 0) : 0; }

  /* 점수 줄: 빈칸 · OX · 카드 · 총 */
  var sc = el('score'), box = sc && sc.closest('.score');
  var hasTotals = (typeof TB !== 'undefined' && typeof TOX !== 'undefined' && typeof GT !== 'undefined');
  if (box && hasTotals){
    box.innerHTML = '빈칸: <span id="score">0</span>/' + TB + ' · OX: <span id="ox-score">0</span>/' + TOX +
      ' · 카드: <span id="pk-score">0</span>/' + N +
      ' · 총: <span id="total-score">0</span>/' + (GT + N) + ' (<span id="pct">0</span>%)';
  }
  function paint(full){
    if (!el('pk-score') || !hasTotals) return;
    var ok = full ? N : tally(), t = full ? GT + N : num('score') + num('ox-score') + ok;
    el('pk-score').textContent = ok;
    el('total-score').textContent = t;
    el('pct').textContent = (GT + N) ? Math.round(t / (GT + N) * 100) : 0;
  }

  /* 카드 고른 상태를 저장본에 싣고 되살린다 — 묶음 순서와 카드 이름이 같을 때만 */
  function sig(w){ return cards(w).map(function(c){ var n = c.querySelector('.pk-name'); return n ? n.textContent.trim() : ''; }).join('|'); }
  function picks(){ return W.map(function(w){ return { s: sig(w), v: cards(w).map(function(c){ return c.dataset.pick || ''; }) }; }); }
  function anyPick(){ return W.some(function(w){ return cards(w).some(function(c){ return c.dataset.pick; }); }); }
  function quiet(fn){
    /* 묶음은 다 고르면 결과 상자로 화면을 끌어내린다 — 되살릴 때는 화면을 움직이지 않는다 */
    var P = Element.prototype, s = P.scrollIntoView; P.scrollIntoView = function(){};
    try { fn(); } finally { P.scrollIntoView = s; }
  }
  function choose(w, c, v){
    if (!v || w.classList.contains('pk-done') || c.dataset.pick === v) return;
    var b = [].slice.call(c.querySelectorAll('.pk-b')).filter(function(x){ return x.dataset.v === v; })[0];
    if (b) b.click();
  }
  function apply(saved){
    if (!saved || !saved.length) return;
    quiet(function(){
      W.forEach(function(w, i){
        var r = saved[i]; if (!r || r.s !== sig(w)) return;
        cards(w).forEach(function(c, j){ choose(w, c, r.v[j]); });
      });
    });
  }
  function stored(){
    try {
      var k = _wsKey(); if (!k) return null;
      var raw = localStorage.getItem(k); return raw ? JSON.parse(raw) : null;
    } catch (e) { return null; }
  }
  function restore(){
    if (typeof _restoreHeld !== 'undefined' && _restoreHeld) return;   /* 다른 사람 저장본이면 되살리지 않는다(9/4 신원 대조와 같다) */
    var o = stored(); if (o && o.data && o.data.__pk) apply(o.data.__pk);
  }

  /* 초기화: 카드도 처음 상태로 */
  function clear(){
    W.forEach(function(w){
      w.classList.remove('pk-done');
      cards(w).forEach(function(c){
        delete c.dataset.pick;
        c.classList.remove('pk-set', 'pk-happy', 'pk-sad', 'pk-ok', 'pk-no');
        [].forEach.call(c.querySelectorAll('.pk-b'), function(b){ b.classList.remove('on'); });
        var y = c.querySelector('.pk-why'); if (y) y.hidden = true;
        var x = c.querySelector('.pk-win.pk-has-photo');
        if (x){
          /* 다 고르면 지도가 사진으로 뒤집힌다 — 지도로 되돌리고, 뒤집기 손잡이는 새로 다 고를 때 다시 붙도록 떼어 낸다 */
          var m = x.querySelector('.pk-map'), p = x.querySelector('.pk-photo'), t = x.querySelector('.pk-wtag');
          if (m) m.hidden = false; if (p) p.hidden = true;
          if (t){ t.hidden = true; var ti = t.querySelector('i'); if (ti) ti.textContent = '누르면 지도'; }
          x.classList.remove('pk-flipping');
          x.parentNode.replaceChild(x.cloneNode(true), x);
        }
      });
      var r = w.querySelector('.pk-result'); if (r){ r.hidden = true; r.innerHTML = ''; }
      var k = w.querySelector('.pk-count'); if (k) k.textContent = '0 / ' + cards(w).length;
    });
  }
  /* 초기화한 뒤 다 고르기 전에는 «맞힌 카드 이유 열기»가 열리지 않게 — 그 손잡이는 카드에 남아 있다 */
  document.addEventListener('click', function(e){
    var c = e.target && e.target.closest && e.target.closest('.ws-pick .pk-card'); if (!c) return;
    if (c.closest('.ws-pick').classList.contains('pk-done') || e.target.closest('.pk-b')) return;
    if (c.dataset.tap) e.stopPropagation();
  }, true);
  /* 카드를 고르면 빈칸처럼 자동 저장 */
  document.addEventListener('click', function(e){
    if (e.target && e.target.closest && e.target.closest('.ws-pick .pk-b') && typeof autosave === 'function') autosave();
  });

  var _check = check;
  check = function(){ var r = _check.apply(this, arguments); paint(false); return r; };
  if (typeof reset === 'function'){
    var _reset = reset;
    reset = function(){ var r = _reset.apply(this, arguments); clear(); var s = el('pk-score'); if (s) s.textContent = 0; return r; };
  }
  if (typeof reveal === 'function'){
    var _reveal = reveal;
    reveal = function(){
      var r = _reveal.apply(this, arguments);
      quiet(function(){ W.forEach(function(w){ cards(w).forEach(function(c){ choose(w, c, c.dataset.ans); }); }); });
      paint(true); return r;
    };
  }
  if (typeof _anyAnswer === 'function'){
    var _any = _anyAnswer;
    _anyAnswer = function(){ return _any.apply(this, arguments) || anyPick(); };
  }
  if (typeof _persist === 'function'){
    var _p = _persist;
    _persist = function(){
      var k = null, before = null;
      try { k = _wsKey(); before = k ? localStorage.getItem(k) : null; } catch (e) {}
      var r = _p.apply(this, arguments);
      /* 원래 저장이 실제로 썼을 때만 덧붙인다 — 보류 중에 남의 저장본에 카드를 얹지 않는다 */
      try {
        if (!k) return r;
        var raw = localStorage.getItem(k); if (!raw || raw === before) return r;
        var o = JSON.parse(raw); o.data = o.data || {};
        if (anyPick()) o.data.__pk = picks(); else delete o.data.__pk;
        localStorage.setItem(k, JSON.stringify(o));
      } catch (e) {}
      return r;
    };
  }
  if (typeof loadProgress === 'function'){
    var _l = loadProgress;
    loadProgress = function(){ var r = _l.apply(this, arguments); restore(); return r; };
  }
  if (typeof collectAnswers === 'function'){
    var _ca = collectAnswers;
    collectAnswers = function(){ var a = _ca.apply(this, arguments); a.__cards = { ok: tally(), n: N }; return a; };
  }
  restore();   /* 처음 열 때 되살리기는 본 스크립트가 이미 끝냈다 — 카드만 이어서 */
})();
