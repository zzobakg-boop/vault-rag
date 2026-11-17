/* 2026-11-17 천대현 5-1 검토판 댓글 «그림을 클릭해서 확대하면 미술관 큐레이터처럼 그 부분이 표시되고 설명이 들어가게 —
   그림 아래 해설이 버려지는 텍스트가 되지 않고 분량도 줄게». 원고 «:::그림 해설 images/….webp» 블록이 있는 차시에만 실린다.
   확대 창(zoom.js)이 열리면 그 그림 위에 번호 표시를 얹고, 번호를 누르면 창 아래 칸에 설명이 뜬다(이전·다음으로 차례대로).
   번호 자리는 그림 너비·높이에 대한 %라 확대·이동·폰에서도 제자리에 붙는다. 인쇄에는 그림 아래 번호 목록이 나온다. */
(function(){
var D=null; try{ D=JSON.parse((document.getElementById('pin-data')||{}).textContent||'null'); }catch(e){ D=null; }
if(!D) return;
var CIRC='①②③④⑤⑥⑦⑧⑨⑩';
function num(n){ return CIRC.charAt(n-1)||('('+n+')'); }
function esc(t){ return String(t).replace(/[&<>"]/g,function(c){ return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]; }); }

/* 본문 그림: «눌러서 번호 N곳» 안내 한 줄 + 인쇄용 목록 */
[].forEach.call(document.querySelectorAll('a.ws-fig-zoom'),function(a){
  var P=D[a.getAttribute('href')]; if(!P) return;
  var fig=a.closest('figure')||a.parentNode; fig.classList.add('ws-pin-fig');
  var hint=document.createElement('button'); hint.type='button'; hint.className='ws-pin-hint';
  hint.innerHTML='🔍 그림을 누르면 번호 '+P.length+'곳 해설';
  hint.addEventListener('click',function(){ a.click(); });
  a.insertAdjacentElement('afterend',hint);
  var ol=document.createElement('ol'); ol.className='ws-pin-print';
  ol.innerHTML=P.map(function(p){ return '<li><b>'+num(p.n)+' '+esc(p.t)+'</b> — '+esc(p.d)+'</li>'; }).join('');
  fig.appendChild(ol);
  /* 인쇄에선 확대 창이 없으니 그림 위에 작은 번호를 찍어 목록과 잇는다 */
  var pr=document.createElement('span'); pr.className='ws-pin-printmarks'; pr.setAttribute('aria-hidden','true');
  pr.innerHTML=P.map(function(p){ return '<i style="left:'+p.x+'%;top:'+p.y+'%">'+p.n+'</i>'; }).join('');
  a.appendChild(pr); a.classList.add('ws-pin-a');
});

var cur=null, layer=null, panel=null, obs=null, ro=null, i=-1;
function box(){ return document.querySelector('.ws-zoom'); }
function place(){   /* 번호 층 = 확대 창 그림의 변형 전 자리·크기, 변형은 그림과 같이 */
  var b=box(); if(!b||!layer) return;
  var im=b.querySelector('.ws-zoom-stage img');
  layer.style.left=im.offsetLeft+'px'; layer.style.top=im.offsetTop+'px';
  layer.style.width=im.offsetWidth+'px'; layer.style.height=im.offsetHeight+'px';
  var tf=im.style.transform||''; layer.style.transform=tf;
  var m=/scale\(([\d.]+)\)/.exec(tf); layer.style.setProperty('--ws-pin-s', m?m[1]:1);
}
function show(k){
  i=k; var p=cur[k];
  [].forEach.call(layer.children,function(b,j){ b.classList.toggle('on',j===k); b.setAttribute('aria-pressed',j===k?'true':'false'); });
  panel.hidden=false;
  panel.querySelector('.ws-pin-t').innerHTML='<b>'+num(p.n)+' '+esc(p.t)+'</b>';
  panel.querySelector('.ws-pin-d').textContent=p.d;
  panel.querySelector('[data-p="prev"]').disabled=k===0;
  panel.querySelector('[data-p="next"]').disabled=k===cur.length-1;
  requestAnimationFrame(place);
}
function teardown(){
  if(layer) layer.remove(); if(panel) panel.remove(); if(obs) obs.disconnect(); if(ro) ro.disconnect();
  layer=panel=obs=ro=cur=null; i=-1;
}
function setup(P){
  teardown(); var b=box(); if(!b) return; cur=P;
  var stage=b.querySelector('.ws-zoom-stage'), im=stage.querySelector('img');
  stage.style.position='relative';
  layer=document.createElement('div'); layer.className='ws-pin-layer';
  P.forEach(function(p,k){
    var bt=document.createElement('button'); bt.type='button'; bt.className='ws-pin';
    bt.style.left=p.x+'%'; bt.style.top=p.y+'%'; bt.textContent=p.n;
    bt.setAttribute('aria-label',p.n+'번 '+p.t); bt.setAttribute('aria-pressed','false');
    bt.addEventListener('click',function(){ show(k); });
    layer.appendChild(bt);
  });
  /* 번호를 누를 때 그림 끌기(zoom.js 포인터 잡기)가 먼저 가로채지 않게 */
  layer.addEventListener('pointerdown',function(e){ if(e.target.closest('.ws-pin')) e.stopPropagation(); });
  stage.appendChild(layer);
  panel=document.createElement('div'); panel.className='ws-pin-panel'; panel.hidden=true;
  panel.setAttribute('aria-live','polite');
  panel.innerHTML='<div class="ws-pin-t"></div><p class="ws-pin-d"></p>'+
    '<div class="ws-pin-nav"><button type="button" data-p="prev">◀ 이전</button><button type="button" data-p="next">다음 ▶</button>'+
    '<button type="button" data-p="hide">설명 닫기</button></div>';
  panel.addEventListener('click',function(e){ var q=e.target.closest('[data-p]'); if(!q) return;
    var a=q.getAttribute('data-p');
    if(a==='prev'&&i>0) show(i-1); else if(a==='next'&&i<cur.length-1) show(i+1);
    else if(a==='hide'){ panel.hidden=true; i=-1; [].forEach.call(layer.children,function(x){ x.classList.remove('on'); x.setAttribute('aria-pressed','false'); }); }
    requestAnimationFrame(place);
  });
  b.insertBefore(panel,b.querySelector('.ws-zoom-bar'));
  obs=new MutationObserver(function(ms){
    ms.forEach(function(m){ if(m.target===b&&b.hidden) teardown(); });
    if(layer) place();
  });
  obs.observe(im,{attributes:true,attributeFilter:['style','src']});
  obs.observe(b,{attributes:true,attributeFilter:['hidden']});
  /* 설명 칸이 열리고 닫히면 그림 칸 크기가 바뀐다 — 그림 크기가 바뀔 때마다 번호 층을 다시 맞춘다 */
  if(window.ResizeObserver){ ro=new ResizeObserver(function(){ if(layer) place(); }); ro.observe(im); ro.observe(stage); }
  if(im.complete) place(); im.addEventListener('load',place,{once:true});
  var tip=b.querySelector('.ws-zoom-tip'); if(tip&&!tip.dataset.pinOld){ tip.dataset.pinOld=tip.textContent; }
  if(tip) tip.textContent='번호를 누르면 설명이 나와요 · 두 손가락이나 휠로 키우고 끌어서 옮겨요';
}
window.addEventListener('resize',function(){ if(layer) place(); });
/* zoom.js가 문서 click에서 창을 연 뒤에 돈다(나중에 붙인 듣개) */
document.addEventListener('click',function(e){
  if(!e.target.closest) return;
  var a=e.target.closest('a.ws-fig-zoom'); var b=box();
  if(a&&D[a.getAttribute('href')]&&b&&!b.hidden){ setup(D[a.getAttribute('href')]); return; }
  if(a&&b&&!b.hidden){ teardown(); var tip=b.querySelector('.ws-zoom-tip'); if(tip&&tip.dataset.pinOld) tip.textContent=tip.dataset.pinOld; }
});
})();
