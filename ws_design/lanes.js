/* :::영향줄 — 나라(줄) × 시기(칸) 위에 큰 사건을 먼저 놓고, 누르면 그 나라 안의 전개와 주고받은 영향이 열린다.
   2026-11-16 천대현 «굵직한 사건(나라→사건)을 먼저, 나라 안 전개는 부수적으로 · 영향을 주고받은 사건이 더 분명하게».
   worksheet-gen(:::영향줄 블록)과 Ⅴ단원 흐름 지도(«한눈에» 장면)가 같은 그리기를 쓴다.
   D = {lanes:[{n,c}], cols:[{n,y}], ev:[{n,l,c0,c1,y,st:[[해,글]],go}], inf:[{a,b,k,w,p,lx,ly}]}
   k(영향 종류) = 생각 | 전쟁 | 도움 | 경제 */
(function(){
  var NS = 'http://www.w3.org/2000/svg';
  var KIND = {'생각':'생각·소식이 건너감','전쟁':'전쟁·침략','도움':'다른 나라의 편들기','경제':'기술·원료·돈이 오감'};
  function el(t, a, p){ var e = document.createElementNS(NS, t); for (var k in a) e.setAttribute(k, a[k]); if (p) p.appendChild(e); return e; }
  function esc(s){ return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;'); }
  function strip(s){ return String(s).replace(/<[^>]+>/g,''); }
  window.WSLanes = function(root, D, opt){
    opt = opt || {};
    var LW = 78, CW = opt.colW || (D.cols.length >= 6 ? 108 : 124), RH = 74, H0 = 40, P = 8, EH = 44;   // 칸 여섯이면 좁혀 학습지 폭(682)에 맞춘다
    var nc = D.cols.length, nl = D.lanes.length;
    var W = LW + nc*CW + P, H = H0 + nl*RH + P;
    var box = root.querySelector('.ln-svgbox'), card = root.querySelector('.ln-card');
    var scr = root.querySelector('.ln-scroll'), swp = root.querySelector('.ln-swipe');
    if (scr && !scr.parentNode.classList.contains('ln-wrap')){
      var wrap = document.createElement('div'); wrap.className = 'ln-wrap'; scr.parentNode.insertBefore(wrap, scr); wrap.appendChild(scr);
      if (swp) wrap.parentNode.insertBefore(swp, wrap);
      var edge = function(){ wrap.classList.toggle('ln-more-r', scr.scrollLeft + scr.clientWidth < scr.scrollWidth - 4); };
      scr.addEventListener('scroll', edge, {passive:true}); window.addEventListener('resize', edge); setTimeout(edge, 0);
    }
    // 나라 이름 칸은 따로 그려 왼쪽에 붙여 둔다(폰에서 그림을 옆으로 밀어도 나라 이름이 남는다)
    box.style.minWidth = W+'px';   // 폰에서도 글자가 줄지 않게(그림만 옆으로 민다)
    var lsvg = el('svg', {viewBox:'0 0 '+LW+' '+H, 'class':'ln-lsvg', 'aria-hidden':'true', style:'width:'+(LW/W*100)+'%'}, box);
    var svg = el('svg', {viewBox:LW+' 0 '+(W-LW)+' '+H, 'class':'ln-msvg', style:'width:'+((W-LW)/W*100)+'%', role:'img', 'aria-label': strip(opt.label || '나라별 큰 사건과 영향')}, box);
    var defs = el('defs', {}, svg);
    Object.keys(KIND).forEach(function(k, i){
      var m = el('marker', {id: root.id+'-m'+i, viewBox:'0 0 10 10', refX:'9', refY:'5', markerWidth:'10', markerHeight:'10', markerUnits:'userSpaceOnUse', orient:'auto-start-reverse'}, defs);
      el('path', {d:'M0,0 L10,5 L0,10 z', 'class':'ln-k'+i}, m);
    });
    var gBg = el('g', {}, svg), gEd = el('g', {}, svg), gEv = el('g', {}, svg), gLb = el('g', {}, svg);
    // 칸 머리
    D.cols.forEach(function(c, i){
      var x = LW + i*CW;
      el('rect', {x:x+2, y:4, width:CW-4, height:H0-10, rx:6, 'class':'ln-colhd'}, gBg);
      var t = el('text', {x:x+CW/2, y:19, 'text-anchor':'middle', 'class':'ln-coln'}, gBg); t.textContent = c.n;
      if (c.y){ var t2 = el('text', {x:x+CW/2, y:31, 'text-anchor':'middle', 'class':'ln-coly'}, gBg); t2.textContent = c.y; }
      if (i) el('line', {x1:x, y1:H0-4, x2:x, y2:H-P, 'class':'ln-vgrid'}, gBg);
    });
    // 줄
    D.lanes.forEach(function(l, r){
      var y = H0 + r*RH;
      el('rect', {x:LW, y:y, width:W-LW, height:RH, 'class': r%2 ? 'ln-band ln-odd' : 'ln-band'}, gBg);
      el('rect', {x:0, y:y, width:LW, height:RH, 'class': r%2 ? 'ln-band ln-odd' : 'ln-band'}, lsvg);
      el('rect', {x:4, y:y+RH/2-9, width:5, height:18, rx:2, fill:l.c}, lsvg);
      // 다섯 자 넘는 이름은 두 줄로 — 띄어쓰기에서, 없으면 가운뎃점 뒤에서 꺾는다
      var nm = String(l.n), cut = nm.indexOf(' '), a1, a2;
      if (cut < 0 && nm.indexOf('·') > 0){ cut = nm.indexOf('·') + 1; a1 = nm.slice(0, cut); a2 = nm.slice(cut); }
      else if (cut > 0){ a1 = nm.slice(0, cut); a2 = nm.slice(cut + 1); }
      if (nm.length > 5 && a1){
        var a = el('text', {x:14, y:y+RH/2-3, 'class':'ln-lane'}, lsvg); a.textContent = a1;
        var b = el('text', {x:14, y:y+RH/2+13, 'class':'ln-lane'}, lsvg); b.textContent = a2;
      } else { var t = el('text', {x:14, y:y+RH/2+4, 'class':'ln-lane'}, lsvg); t.textContent = l.n; }
    });
    el('rect', {x:0, y:0, width:LW, height:H0, 'class':'ln-band'}, lsvg);
    // 사건 칸
    var box2 = D.ev.map(function(e){
      var x = LW + e.c0*CW + 5, w = (e.c1 - e.c0 + 1)*CW - 10, y = H0 + e.l*RH + (RH - EH)/2, h = EH;
      return {x:x, y:y, w:w, h:h, cx:x+w/2, cy:y+h/2};
    });
    var evEls = D.ev.map(function(e, i){
      var b = box2[i], ln = D.lanes[e.l];
      var g = el('g', {'class':'ln-ev', tabindex:'0', role:'button', 'aria-label': strip(ln.n+' '+e.n+' '+(e.y||'')), 'data-i':i}, gEv);
      el('rect', {x:b.x, y:b.y, width:b.w, height:b.h, rx:8, 'class':'ln-evbg'}, g);
      el('rect', {x:b.x, y:b.y, width:5, height:b.h, rx:2, fill:ln.c}, g);
      var t = el('text', {x:b.x+12, y:b.y+18, 'class':'ln-evn'}, g); t.textContent = e.n;
      if (e.y){ var t2 = el('text', {x:b.x+12, y:b.y+33, 'class':'ln-evy'}, g); t2.textContent = e.y; }
      return g;
    });
    // 영향 화살표 — 오른쪽으로 가면 가로 곡선, 같은 때면 세로 곡선
    var kinds = Object.keys(KIND);
    var edEls = D.inf.map(function(f, i){
      var s = box2[f.a], t = box2[f.b], ki = Math.max(0, kinds.indexOf(f.k)), d, mx, my, vert = false;
      var gap = t.x - (s.x + s.w), lo = Math.max(s.x, t.x), hi = Math.min(s.x+s.w, t.x+t.w);
      if (gap >= 60 || (gap > -6 && D.ev[f.a].l === D.ev[f.b].l)){
        // 칸 하나 이상 떨어져 있으면 가로 곡선
        var sx = s.x + s.w, sy = s.cy + (f.sy||0), ex = t.x - 1, ey = t.cy + (f.ey||0), dx = Math.max(26, (ex - sx)*0.5);
        d = 'M'+sx+','+sy+' C'+(sx+dx)+','+sy+' '+(ex-dx)+','+ey+' '+ex+','+ey;
        mx = (sx+ex)/2; my = (sy+ey)/2;
      } else {
        // 같은 때이거나 바로 옆 칸이면 줄 사이 틈으로 세로 곡선 — 받는 칸의 가장 가까운 자리로 들어간다
        var x0 = hi > lo ? (lo+hi)/2 + (f.sx||0) : Math.min(Math.max(s.cx, s.x+18), s.x+s.w-18);
        if (hi > lo){
          // 겹치는 칸 범위 안에서, 가운데 줄의 다른 사건 칸을 가로지르지 않는 x를 가운데부터 찾는다
          var yA = Math.min(s.y, t.y), yB = Math.max(s.y + s.h, t.y + t.h);
          var cross = function(x){ return box2.some(function(q, k){ return k !== f.a && k !== f.b && q.y > yA && q.y + q.h < yB && x > q.x - 6 && x < q.x + q.w + 6; }); };
          if (cross(x0)) for (var dd = 10; dd < (hi - lo)/2; dd += 10){ if (!cross(x0 - dd) && x0 - dd > lo + 12){ x0 -= dd; break; } if (!cross(x0 + dd) && x0 + dd < hi - 12){ x0 += dd; break; } }
        }
        var x1 = hi > lo ? x0 + (f.ex||0) : Math.min(Math.max(x0, t.x+18), t.x+t.w-18);
        var down = t.y > s.y, y0 = down ? s.y + s.h : s.y, y1 = down ? t.y - 1 : t.y + t.h + 1, dy = (y1 - y0)*0.5;
        d = 'M'+x0+','+y0+' C'+x0+','+(y0+dy)+' '+x1+','+(y1-dy)+' '+x1+','+y1;
        mx = (x0+x1)/2; my = (y0+y1)/2; vert = true;
      }
      var g = el('g', {'class':'ln-ed ln-k'+ki, 'data-i':i}, gEd);
      el('path', {d:d, 'class':'ln-edp', 'marker-end':'url(#'+root.id+'-m'+ki+')'}, g);
      var lg = el('g', {'class':'ln-edl ln-k'+ki, 'data-i':i}, gLb);
      // 세로 화살표는 이름표를 선 오른쪽에 붙인다(선을 가리지 않게)
      var lt = el('text', {x:mx+(f.lx||0)+(vert ? 7 : 0), y:my+(f.ly||0)+4, 'text-anchor': vert ? 'start' : 'middle', 'class':'ln-edt'}, lg); lt.textContent = strip(f.w);
      return [g, lg];
    });
    // 이름표 겹침 피하기 — 사건 칸과 앞서 놓인 이름표를 피해 옆·위·아래로 비킨다.
    //   웹 글꼴이 늦게 오면 글자 폭이 바뀌므로 글꼴이 다 온 뒤 한 번 더 놓는다.
    edEls.forEach(function(p){ var tx = p[1].querySelector('text'); tx.dataset.x0 = tx.getAttribute('x'); tx.dataset.y0 = tx.getAttribute('y'); });
    function placeLabels(){
      var placed = box2.map(function(b){ return {x:b.x, y:b.y, w:b.w, h:b.h}; });
      function hit(bb){ return placed.some(function(q){ return bb.x < q.x+q.w+4 && q.x < bb.x+bb.w+4 && bb.y < q.y+q.h+1 && q.y < bb.y+bb.h+1; }); }
      edEls.forEach(function(p){
        var tx = p[1].querySelector('text'), b, x0 = +tx.dataset.x0, y0 = +tx.dataset.y0;
        tx.setAttribute('x', x0); tx.setAttribute('y', y0);
        try { b = tx.getBBox(); } catch(e){ return; }
        if (!b.width) return;
        var tries = [[0,0],[0,-12],[0,12],[-b.width/2-10,0],[b.width/2+10,0],[0,-24],[0,24],[-b.width-14,0],[b.width+14,0]];
        for (var k = 0; k < tries.length; k++){
          var bb = {x:b.x+tries[k][0], y:b.y+tries[k][1], w:b.width, h:b.height};
          if (bb.x < LW || bb.x + bb.w > W || bb.y < H0) continue;
          if (!hit(bb)){ tx.setAttribute('x', x0+tries[k][0]); tx.setAttribute('y', y0+tries[k][1]); placed.push(bb); return; }
        }
        placed.push({x:b.x, y:b.y, w:b.width, h:b.height});
      });
    }
    placeLabels();
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(placeLabels);
    root._placeLabels = placeLabels;   // 숨어 있다가 보이게 된 경우 다시 놓을 때
    // 범례
    var lgd = root.querySelector('.ln-legend');
    if (lgd) lgd.innerHTML = kinds.filter(function(k){ return D.inf.some(function(f){ return f.k === k; }); })
      .map(function(k){ return '<span class="ln-k'+kinds.indexOf(k)+'"><i></i>'+esc(KIND[k])+'</span>'; }).join('');
    var sel = -1;
    function name(i){ var e = D.ev[i]; return D.lanes[e.l].n+' · '+e.n; }
    function show(i){
      sel = (sel === i ? -1 : i);
      evEls.forEach(function(g, k){ g.classList.toggle('ln-sel', k === sel); g.classList.toggle('ln-dim', sel >= 0 && k !== sel && !D.inf.some(function(f){ return (f.a===sel&&f.b===k)||(f.b===sel&&f.a===k); })); });
      edEls.forEach(function(p, k){ var on = sel < 0 || D.inf[k].a === sel || D.inf[k].b === sel; p[0].classList.toggle('ln-dim', !on); p[1].classList.toggle('ln-dim', !on); });
      if (sel < 0){ card.innerHTML = '<p class="ln-hint">'+(opt.hint || '사건 칸을 누르면 그 나라 안에서 일이 어떻게 흘러갔는지, 어떤 영향을 주고받았는지가 여기 열린다.')+'</p>'; return; }
      var e = D.ev[sel], h = '<div class="ln-ct" style="--lc:'+D.lanes[e.l].c+'"><b>'+esc(D.lanes[e.l].n)+'</b> · '+e.n+(e.y ? ' <span>'+esc(e.y)+'</span>' : '')+'</div>';
      var inn = D.inf.filter(function(f){ return f.b === sel; }), out = D.inf.filter(function(f){ return f.a === sel; });
      if (inn.length) h += '<div class="ln-io"><div class="ln-ioh">← 받은 영향</div>'+inn.map(function(f){ return '<button type="button" class="ln-go ln-k'+kinds.indexOf(f.k)+'" data-i="'+f.a+'"><i></i><b>'+esc(name(f.a))+'</b> — '+f.w+(f.p ? ' <small>'+esc(f.p)+'</small>' : '')+'</button>'; }).join('')+'<p class="ln-note">영향만으로 일이 일어난 것은 아니다. 아래 차례에서 '+esc(D.lanes[e.l].n)+' 안의 사정도 함께 보자.</p></div>';
      if (e.st && e.st.length) h += '<div class="ln-sth">'+esc(D.lanes[e.l].n)+' 안에서는</div><ol class="ln-steps">'+e.st.map(function(s){ return '<li>'+(s[0] ? '<em>'+esc(s[0])+'</em> ' : '')+s[1]+'</li>'; }).join('')+'</ol>';
      if (out.length) h += '<div class="ln-io"><div class="ln-ioh">준 영향 →</div>'+out.map(function(f){ return '<button type="button" class="ln-go ln-k'+kinds.indexOf(f.k)+'" data-i="'+f.b+'"><i></i><b>'+esc(name(f.b))+'</b> — '+f.w+(f.p ? ' <small>'+esc(f.p)+'</small>' : '')+'</button>'; }).join('')+'</div>';
      if (!inn.length && !out.length) h += '<p class="ln-none">교과서는 이 사건이 다른 나라와 주고받은 영향을 따로 적지 않았다.</p>';
      if (e.go && opt.goLabel) h += '<p class="ln-more"><a href="'+esc(e.go)+'"'+(opt.goTarget ? ' target="'+opt.goTarget+'" rel="noopener"' : '')+'>'+esc(opt.goLabel)+'</a></p>';
      card.innerHTML = h;
      card.querySelectorAll('.ln-go').forEach(function(b){ b.addEventListener('click', function(){ sel = -1; show(+b.dataset.i); }); });
      var sc = root.querySelector('.ln-scroll'), ge = evEls[sel];
      if (sc && ge && sc.scrollWidth > sc.clientWidth + 4){
        var r1 = sc.getBoundingClientRect(), r2 = ge.getBoundingClientRect();
        if (r2.left < r1.left + 70 || r2.right > r1.right) sc.scrollBy({left: r2.left - r1.left - 90, behavior: 'smooth'});
      }
      // 카드가 화면 아래쪽에서 열리면 카드 머리가 보이게 올린다(폰)
      var cr = card.getBoundingClientRect(); if (cr.top > window.innerHeight*0.6) window.scrollBy({top: cr.top - window.innerHeight*0.2, behavior: 'smooth'});
      if (opt.onShow) opt.onShow(sel, card);
    }
    evEls.forEach(function(g, i){
      g.addEventListener('click', function(){ show(i); });
      g.addEventListener('keydown', function(ev){ if (ev.key === 'Enter' || ev.key === ' '){ ev.preventDefault(); show(i); } });
    });
    show(-1);   // 처음엔 아무것도 고르지 않은 상태(안내 한 줄·화살표 모두 보임)
    return {show: function(i){ sel = -1; show(i); }};
  };
})();
