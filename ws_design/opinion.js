/* 의견 카드(:::인물선택카드 [공감|비공감] 의견) — 2026-11-18 천대현 사회 9-1~2 검토판
   «앞에는 누구인지, 뒤집으면 사례, 앞 표지에서 공감/비공감, 고르면 교사용 교과서 보충».
   - 정답이 없는 고르기다. 점수·저장·제출에 넣지 않는다(pickscore.js는 .ws-pick만 센다). 입력칸 0 — data-id 불변.
   - 단추는 카드를 한 번 뒤집어 그 사람의 말을 읽은 뒤에 켜진다(읽지 않고 고르는 것을 막는다).
   - 고르면 카드가 앞면으로 돌아와 고른 쪽 도장이 붙고, 아래에 교사용 교과서 예시 댓글 두 쪽이 열린다(고른 쪽 표시). 다시 고를 수 있다. */
(function(){
[].slice.call(document.querySelectorAll('.ws-opin')).forEach(function(w){
  var cs=[].slice.call(w.querySelectorAll('.op-card')), N=cs.length;
  if(!N) return;
  var cnt=w.querySelector('.op-count'), res=w.querySelector('.op-result');
  var labs=[].slice.call(cs[0].querySelectorAll('.op-b')).map(function(b){ return {v:b.dataset.v, html:b.innerHTML}; });
  function paint(){
    var k=cs.filter(function(c){ return c.dataset.pick; }).length;
    cnt.textContent=k+' / '+N;
    if(k<N){ res.hidden=true; return; }
    res.hidden=false;
    res.innerHTML='<b>'+labs.map(function(l){ return l.html+' '+cs.filter(function(c){ return c.dataset.pick===l.v; }).length+'명'; }).join(' · ')+
      '</b> — 카드마다 열린 예시 댓글에서 내가 고르지 않은 쪽 생각도 읽어 보자. 한 사람의 말에도 두 쪽 생각이 있어.';
  }
  /* 뒷면 말 속 가린 낱말(«⑧») — 그 빈칸을 맞게 채우면 낱말을 드러낸다. 맞음 판정은 채점(check)과 같은 규칙 */
  function nz(t){ return (t||'').replace(/\s+/g,'').replace(/[·,.()（）\[\]]/g,'').toLowerCase(); }
  /* 🔴 입력칸 번호 속성을 셀렉터 글자(따옴표 꼴)로 쓰지 않는다 — HTML을 정규식으로 읽는 검사기가 입력칸으로 센다(개념 잇기 때와 같은 함정). 주석에도 그 꼴을 쓰지 않는다 */
  function blankOf(n){ return [].slice.call(document.querySelectorAll('input.blank-input')).filter(function(x){ return x.dataset.id===n; })[0]; }
  function unmask(c){
    [].slice.call(c.querySelectorAll('.op-mask[data-b]')).forEach(function(m){
      var inp=blankOf(m.dataset.b); if(!inp) return;
      var a=nz(inp.dataset.answer), u=nz(inp.value);
      if(u&&(u===a||(a.indexOf(u)>=0&&u.length>=a.length*0.6))){ m.textContent=inp.dataset.answer; m.classList.add('op-open'); m.removeAttribute('data-b'); m.removeAttribute('title'); }
    });
  }
  cs.forEach(function(c){
    [].slice.call(c.querySelectorAll('.op-mask[data-b]')).forEach(function(m){
      var inp=blankOf(m.dataset.b);
      if(inp) inp.addEventListener('input',function(){ unmask(c); });
    });
  });
  window.addEventListener('load',function(){ cs.forEach(unmask); });
  cs.forEach(function(c){
    var f=c.querySelector('.op-flip'), bs=[].slice.call(c.querySelectorAll('.op-b')), note=c.querySelector('.op-note'),
        more=c.querySelector('.op-more'), st=c.querySelector('.op-stamp'), nm=(c.querySelector('.op-name')||{}).textContent||'';
    nm=nm.trim();
    function face(back){
      if(back) unmask(c);
      c.classList.toggle('op-flipped',back);
      f.setAttribute('aria-label',nm+' 카드 — '+(back?'눌러서 앞면으로':'눌러서 뒤집기'));
      if(back&&!c.dataset.read){
        c.dataset.read='1';
        bs.forEach(function(b){ b.disabled=false; });
        if(!c.dataset.pick) note.textContent='읽었으면 골라 보자 · 카드를 다시 누르면 앞면';
      }
    }
    f.addEventListener('click',function(e){
      if(e.target.closest&&e.target.closest('.lm-n,a,button')) return;   /* 개념 잇기 낱말 단추는 그쪽 일 */
      face(!c.classList.contains('op-flipped'));
    });
    f.addEventListener('keydown',function(e){
      if(e.target!==f) return;
      if(e.key==='Enter'||e.key===' '){ e.preventDefault(); face(!c.classList.contains('op-flipped')); }
    });
    bs.forEach(function(b,bi){
      b.addEventListener('click',function(){
        var v=b.dataset.v;
        c.dataset.pick=v; c.classList.add('op-set');
        bs.forEach(function(x){ x.classList.toggle('on',x===b); x.setAttribute('aria-pressed',x===b?'true':'false'); });
        st.innerHTML=b.innerHTML; st.hidden=false;
        face(false);   /* 앞면으로 돌아와 도장을 보인다 */
        more.hidden=false;
        [].slice.call(more.querySelectorAll('p[data-v]')).forEach(function(p){ p.classList.toggle('op-mine',p.dataset.v===v); });
        note.hidden=true;
        paint();
      });
    });
  });
  /* 카드 높이 맞추기 — 앞뒤 면 가운데 긴 쪽이 카드마다 달라(뒷면 말 길이) 줄이 들쭉날쭉했다. 가장 큰 카드에 맞춘다 */
  var ins=cs.map(function(c){ return c.querySelector('.op-inner'); });
  function even(){
    ins.forEach(function(x){ x.style.minHeight=''; });
    var m=Math.max.apply(null,ins.map(function(x){ return x.offsetHeight; }));
    if(m>0) ins.forEach(function(x){ x.style.minHeight=m+'px'; });
  }
  even();
  window.addEventListener('load',even); window.addEventListener('resize',even);
  [].slice.call(w.querySelectorAll('.op-win img')).forEach(function(im){ if(!im.complete) im.addEventListener('load',even); });
  if(document.fonts&&document.fonts.ready) document.fonts.ready.then(even);
  /* 폰: 옆으로 넘기는 줄의 ◀ ▶ (데스크톱은 네 장이 한 줄이라 단추를 숨긴다) */
  var g=w.querySelector('.op-grid'), pos=w.querySelector('.op-pos'), RM=window.matchMedia&&matchMedia('(prefers-reduced-motion: reduce)').matches;
  function at(){ var k=0,d=1e9; cs.forEach(function(c,i){ var v=Math.abs(c.offsetLeft-g.offsetLeft-g.scrollLeft); if(v<d){ d=v; k=i; } }); return k; }
  function go(k){ k=Math.max(0,Math.min(N-1,k)); g.scrollTo({left:cs[k].offsetLeft-g.offsetLeft,behavior:RM?'auto':'smooth'}); }
  g.addEventListener('scroll',function(){ pos.textContent=(at()+1)+' / '+N; },{passive:true});
  w.querySelector('.op-prev').onclick=function(){ go(at()-1); };
  w.querySelector('.op-next').onclick=function(){ go(at()+1); };
});
})();
