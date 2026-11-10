/* 2026-11-10 천대현(사회② Ⅷ «샘플판에 적용했던 사항들을 8단원 묶음판 전체에»): 개념 관계 선.
   낱말을 누르면 이 학습지 안에서 이어지는 개념·사례가 선으로 나타난다. 원고·입력칸·data-id는 건드리지 않고 화면 글자만 단추로 감싼다.
   선 규칙(색만이 아니라 모양으로도): 한 갈래 실선+빈 삼각형 · 예 둥근 점선+속 찬 원 · 견줘 보기 쇄선+양끝 막대 · 다른 차시 가는 실선+여백 칩.
   고르기 카드에 닿는 선은 카드를 다 고른 뒤에만 열린다. 1280px 아래이거나 본문 오른쪽에 이름표 칸이 없으면 선 대신 아래에서 올라오는 목록(11/10 역사 학생 눈). 시험판 = 8-5~6 검토판 v7(11/9). */
(function(){
'use strict';
var C=document.querySelector('.container'); if(!C) return;
var H=document.documentElement, NS='http://www.w3.org/2000/svg';
var WIDE=window.matchMedia('(min-width:1280px)'), RM=window.matchMedia('(prefers-reduced-motion:reduce)');
var COL={sub:'#4f46e5',ex:'#0f7b6c',cmp:'#b45309',xref:'#64748b'};
var KIND={sub:'한 갈래',ex:'예',cmp:'견줘 보기',xref:'다른 차시'};

/* 자료는 원고 md의 :::개념 잇기 블록 → worksheet-gen이 JSON 자료 칸(id lm-data)으로 넣는다.
   nodes{id:{name, sec(단계 이름), near(앞뒤 문맥), word(단추로 감쌀 글자) | pick(고르기 카드 이름) | fold(접기 제목 일부)+word |
   fig(그림 캡션 글자)+first | chip(이 학습지 밖 칩 글) | intro(제목 아래 첫 입담) | alts[{sel,near,word}]}}
   lines[{t: sub 한 갈래·ex 예·cmp 견줘 보기·xref 다른 차시, a, b, w(연결어), lock(이 고르기 카드가 끝나야 보임)}] */
var DATA=null; try{ DATA=JSON.parse((document.getElementById('lm-data')||{}).textContent||'null'); }catch(e){ DATA=null; }
if(!DATA||!DATA.nodes||!DATA.lines) return;
var NODES=DATA.nodes, LINES=DATA.lines;

/* ---------- 1) 화면 글자 찾기 ---------- */
var SKIP='script,style,button,select,option,textarea,.hero-section,.gl-pop,.gl-layer,.lm-legend,.lm-layer,.lm-sheet,.lm-cg';
function secOf(lab){
  var s=[].slice.call(document.querySelectorAll('.v2-sec')).filter(function(x){return x.dataset.lab===lab;})[0];
  if(s) return {root:s};
  var hs=[].slice.call(C.querySelectorAll('h2')),i=-1;   /* v2 층이 없을 때: h2 사이 */
  hs.some(function(h,k){ if(h.textContent.indexOf(lab)>=0){i=k;return true;} return false; });
  return i<0?null:{root:C,b:[hs[i],hs[i+1]||null]};
}
function inB(n,b){
  if(!b) return true;
  if(b[0]&&!(b[0].compareDocumentPosition(n)&Node.DOCUMENT_POSITION_FOLLOWING)) return false;
  if(b[1]&&!(b[1].compareDocumentPosition(n)&Node.DOCUMENT_POSITION_PRECEDING)) return false;
  return true;
}
function findText(sc,word,near){
  var w=document.createTreeWalker(sc.root,NodeFilter.SHOW_TEXT,{acceptNode:function(n){
    var p=n.parentElement; if(!p||p.closest(SKIP)) return NodeFilter.FILTER_REJECT;
    return inB(n,sc.b)?NodeFilter.FILTER_ACCEPT:NodeFilter.FILTER_SKIP; }}),n;
  while((n=w.nextNode())){
    var d=n.data,s0=0;
    if(near){ s0=d.indexOf(near); if(s0<0) continue; }
    var k=d.indexOf(word,s0); if(k<0||(near&&k>s0+near.length)) continue;
    return {n:n,k:k};
  }
  return null;
}
function wrap(hit,word,name){
  var t=hit.n.splitText(hit.k); t.splitText(word.length);
  var b=document.createElement('button'); b.type='button'; b.className='lm-n'; b.disabled=true;
  b.setAttribute('aria-pressed','false'); b.dataset.lmName=name;
  b.appendChild(document.createTextNode(word));
  var mk=document.createElement('span'); mk.className='lm-mk'; mk.setAttribute('aria-hidden','true'); b.appendChild(mk);
  t.parentNode.replaceChild(b,t); return b;
}
var N={}, missing=[];
Object.keys(NODES).forEach(function(id){
  var d=NODES[id], o={id:id,d:d,name:d.name,ok:false};
  N[id]=o;
  if(d.chip){ o.ok=true; o.chip=true; return; }
  var sc=d.sec?secOf(d.sec):{root:C}, hit=null;
  if(!sc){ missing.push(id); return; }
  if(d.intro){   /* 제목 바로 아래 첫 입담 */
    var q=[].slice.call(C.querySelectorAll('blockquote')).filter(function(x){return !x.closest('.v2-sec')&&(x.classList.contains('v2-voice')||x.textContent.trim().indexOf('🎙️')===0);})[0];
    if(q) hit=findText({root:q},d.word,d.near);
  }else if(d.pick){
    var card=[].slice.call(sc.root.querySelectorAll('.ws-pick .pk-card')).filter(function(c){ if(!inB(c,sc.b)) return false; var nm=c.querySelector('.pk-name'); return nm&&nm.textContent.trim()===d.pick; })[0];
    if(card){ o.card=card; hit=findText({root:card.querySelector('.pk-name')},d.pick); }
  }else if(d.fold){
    var f=[].slice.call(sc.root.querySelectorAll('details.ws-fold')).filter(function(x){ var s=x.querySelector('summary'); return inB(x,sc.b)&&s&&s.textContent.indexOf(d.fold)>=0; })[0];
    if(f){ o.foldEl=f; hit=findText({root:f.querySelector('.ws-fold-body')||f},d.word); }
  }else if(d.fig){
    var fg=[].slice.call(sc.root.querySelectorAll('figure')).filter(function(x){ var c=x.querySelector('figcaption'); return inB(x,sc.b)&&c&&c.textContent.indexOf(d.fig)>=0; })[0];
    if(fg&&d.first){ var f0=[].slice.call(sc.root.querySelectorAll('figure')).filter(function(x){return inB(x,sc.b);})[0]; if(f0!==fg) fg=null; }
    if(fg){ o.fig=fg; o.img=fg.querySelector('img'); hit=findText({root:fg.querySelector('figcaption')},d.fig); }
  }else if(d.alts){
    d.alts.some(function(a){
      if(a.sel){ [].slice.call(sc.root.querySelectorAll(a.sel)).some(function(r){ if(!inB(r,sc.b)) return false; hit=findText({root:r},a.word,a.near); return !!hit; }); }
      else hit=findText(sc,a.word,a.near);
      if(hit){ o.word=a.word; return true; } return false; });
  }else hit=findText(sc,d.word,d.near);
  if(!hit||(d.fig&&!o.img)){ missing.push(id); return; }
  o.btn=wrap(hit,o.word||d.word||d.pick||d.fig,d.name);
  o.anchor=o.img||o.btn;
  o.ok=true;
});
LINES.forEach(function(L,i){ L.i=i; L.ok=N[L.a].ok&&N[L.b].ok; });
var skipped=LINES.filter(function(L){return !L.ok;});
if(missing.length) console.warn('[개념선] 화면에서 못 찾아 건너뜀 — 노드:',missing.join(', '),'/ 선:',skipped.map(function(L){return L.a+'→'+L.b;}).join(', ')||'없음');
var live=LINES.filter(function(L){return L.ok;});
if(!live.length) return;
window.__lm={nodes:N,lines:LINES,missing:missing};

/* ---------- 2) 범례 «선 읽는 법» — 학습 목표 절 끝 ---------- */
function swatch(t,w){
  w=w||44; var y=7,x2=w-6,s='<svg class="lm-sw" viewBox="0 0 '+w+' 14" width="'+w+'" height="14" aria-hidden="true">';
  var cls={sub:'t-sub',ex:'t-ex',cmp:'t-cmp',xref:'t-xref'}[t];
  s+='<line class="lm-line '+cls+'" x1="'+(t==='cmp'?4:3)+'" y1="'+y+'" x2="'+(t==='sub'?x2-8:x2)+'" y2="'+y+'"/>';
  if(t==='sub') s+='<path d="M'+(x2-9)+' 2.5L'+(x2+1)+' 7L'+(x2-9)+' 11.5Z" fill="#fff" stroke="'+COL.sub+'" stroke-width="1.6" stroke-linejoin="round"/>';
  if(t==='ex') s+='<circle cx="'+x2+'" cy="7" r="4" fill="'+COL.ex+'"/>';
  if(t==='cmp') s+='<rect x="2" y="1" width="2.5" height="12" rx="1" fill="'+COL.cmp+'"/><rect x="'+(x2-1)+'" y="1" width="2.5" height="12" rx="1" fill="'+COL.cmp+'"/>';
  if(t==='xref') s+='<rect x="'+(x2-4)+'" y="3" width="9" height="8" rx="2" fill="#f8fafc" stroke="'+COL.xref+'" stroke-width="1.3"/>';
  return s+'</svg>';
}
var goal=secOf('학습 목표');
if(goal&&goal.root!==C){
  var lg=document.createElement('aside'); lg.className='lm-legend'; lg.setAttribute('aria-label','선 읽는 법');
  lg.innerHTML='<div class="lm-lg-h">선 읽는 법</div><p class="lm-lg-p">작은 고리 표시<span class="lm-mk" aria-hidden="true"></span>가 붙은 낱말을 누르면, 이 학습지 안에서 이어지는 개념과 사례가 선으로 나타난다.</p>'+
   '<ul class="lm-lg-ul">'+
   '<li>'+swatch('sub')+'<b>한 갈래</b><span>~는 …의 한 갈래</span></li>'+
   '<li>'+swatch('ex')+'<b>예</b><span>~는 …의 예</span></li>'+
   '<li>'+swatch('cmp')+'<b>견줘 보기</b><span>둘을 견주면 보인다</span></li>'+
   '<li>'+swatch('xref')+'<b>다른 차시</b><span>앞에서 배운 것</span></li></ul>'+
   '<p class="lm-lg-narrow">폰처럼 좁은 화면에서는 선 대신 아래에서 목록이 올라온다.</p>';
  goal.root.appendChild(lg);
}

/* ---------- 3) 선 레이어·선 끄기·아래 판 ---------- */
var layer=document.createElement('div'); layer.className='lm-layer';
var svg=document.createElementNS(NS,'svg'); svg.setAttribute('class','lm-svg'); svg.setAttribute('aria-hidden','true');
svg.innerHTML='<defs>'+
 '<marker id="lm-m-tri" viewBox="0 0 12 12" refX="11" refY="6" markerWidth="13" markerHeight="13" markerUnits="userSpaceOnUse" orient="auto-start-reverse"><path d="M1.2 1.5L11 6L1.2 10.5Z" fill="#fff" stroke="'+COL.sub+'" stroke-width="1.7" stroke-linejoin="round"/></marker>'+
 '<marker id="lm-m-dot" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="10" markerHeight="10" markerUnits="userSpaceOnUse"><circle cx="5" cy="5" r="4.2" fill="'+COL.ex+'" stroke="#fff" stroke-width="1"/></marker>'+
 '<marker id="lm-m-bar" viewBox="0 0 4 14" refX="2" refY="7" markerWidth="4" markerHeight="14" markerUnits="userSpaceOnUse" orient="auto"><rect x=".75" y="0" width="2.5" height="14" rx="1" fill="'+COL.cmp+'"/></marker>'+
 '</defs><g class="lm-g"></g>';
layer.appendChild(svg); document.body.appendChild(layer);
var G=svg.querySelector('.lm-g');
var off=document.createElement('button'); off.type='button'; off.className='lm-off'; off.hidden=true; off.textContent='선 끄기';
document.body.appendChild(off);
var sheet=document.createElement('div'); sheet.className='lm-sheet'; sheet.hidden=true; sheet.setAttribute('role','dialog'); sheet.setAttribute('aria-label','이어지는 개념과 사례');
document.body.appendChild(sheet);
var liveR=document.createElement('div'); liveR.className='lm-live'; liveR.setAttribute('aria-live','polite'); document.body.appendChild(liveR);

var active=null, fresh=false, printing=false, tags={}, groups={};
/* 보이는가 — 닫힌 접기 안은 Chrome이 content-visibility로 숨겨 사각형이 남으니 따로 본다 */
function rendered(el){
  if(!el||!el.getClientRects().length) return false;
  for(var d=el.closest('details');d;d=d.parentElement&&d.parentElement.closest('details')){
    if(!d.open){ var sm=d.querySelector(':scope>summary'); if(!(sm&&sm.contains(el))) return false; } }
  if(el.checkVisibility&&!el.checkVisibility()) return false;
  return true;
}
function unlocked(o){ return !o.card||o.card.classList.contains('pk-ok')||o.card.classList.contains('pk-no'); }
function lineOK(L){
  if(!L.ok) return false;
  if(L.lock&&[].concat(L.lock).some(function(k){ return !unlocked(N[k]); })) return false;
  var A=N[L.a],B=N[L.b];
  if(!A.chip&&!rendered(A.anchor)) return false;
  if(!B.chip&&!rendered(B.anchor)) return false;
  return true;
}
function linesOf(id){ return live.filter(function(L){ return (L.a===id||L.b===id)&&lineOK(L); }); }
function refresh(){   /* 노드마다 지금 이어진 선이 있을 때만 단추를 연다 */
  Object.keys(N).forEach(function(id){ var o=N[id]; if(!o.btn) return;
    var n=linesOf(id).length; o.btn.disabled=!n;
    if(n) o.btn.setAttribute('aria-label',o.name+' — 이어지는 것 '+n+'개 보기'); else o.btn.removeAttribute('aria-label'); });
  if(active&&!linesOf(active).length) setActive(null);
}
function secLab(o){ var el=o.anchor; var s=el&&el.closest('.v2-sec'); return s?(s.dataset.lab||''):'맨 위'; }
function other(L){ return L.a===active?L.b:L.a; }

function setActive(id,focusBack){
  if(active&&N[active].btn){ N[active].btn.setAttribute('aria-pressed','false'); }
  active=id; fresh=!!id;
  if(!id){ clearAll(); off.hidden=true; sheet.hidden=true; liveR.textContent='';
    if(focusBack&&focusBack.focus) focusBack.focus(); return; }
  N[id].btn.setAttribute('aria-pressed','true');
  var ls=linesOf(id);
  liveR.textContent=N[id].name+'에서 이어지는 것 '+ls.length+'개: '+ls.map(function(L){return KIND[L.t]+' — '+L.w+' ('+N[other(L)].name+')';}).join(' · ');
  layout();
  if(!lineMode()) keepVisibleAboveSheet(N[id].anchor);
}
/* 강조 — toggle(이름, 참거짓)은 이미 그 상태면 아무것도 안 바꾼다(고르기 카드 감시자에 되먹임이 안 생긴다) */
function marks(on,peers){
  Object.keys(N).forEach(function(id){ var o=N[id], a=id===on, p=!a&&!!peers[id];
    if(o.btn){ o.btn.classList.toggle('lm-on',a); o.btn.classList.toggle('lm-peer',p); }
    if(o.fig){ o.fig.classList.toggle('lm-fig-on',a); o.fig.classList.toggle('lm-fig-peer',p); } });
}
function clearAll(){
  G.innerHTML=''; Object.keys(tags).forEach(function(k){ tags[k].remove(); }); tags={};
  Object.keys(groups).forEach(function(k){ groups[k].remove(); }); groups={};
  marks(null,{}); sheet._k='';
  svg.setAttribute('height','0');
}

/* ---------- 4) 그리기 ---------- */
function R(el){ var r=el.getBoundingClientRect(),sx=window.scrollX||0,sy=window.scrollY||0;
  return {l:r.left+sx,r:r.right+sx,t:r.top+sy,b:r.bottom+sy,w:r.width,h:r.height,cx:(r.left+r.right)/2+sx,cy:(r.top+r.bottom)/2+sy}; }
/* 줄 재기 — 낱말이 놓인 줄의 글자 위·아래 끝과, 앞뒤 줄 사이 틈의 한가운데(Range 글자 사각형으로) */
function blockOf(el){ for(var b=el.parentElement;b&&b!==document.body;b=b.parentElement){ var d=getComputedStyle(b).display; if(d!=='inline'&&d!=='inline-block'&&d!=='contents') return b; } return el.parentElement; }
function boxes(blk){
  var out=[], w=document.createTreeWalker(blk,NodeFilter.SHOW_TEXT,null), n, rg=document.createRange();
  while((n=w.nextNode())){ if(!n.data.trim()) continue; var pe=n.parentElement; if(pe&&pe.closest('script,style,.lm-layer,.lm-cg')) continue;
    rg.selectNodeContents(n); [].forEach.call(rg.getClientRects(),function(r){ if(r.width>0&&r.height>0) out.push(r); }); }
  [].forEach.call(blk.querySelectorAll('input,textarea,select,.gl-badge'),function(e){ var r=e.getBoundingClientRect(); if(r.width&&r.height&&r.height<70) out.push(r); });
  return out;
}
function metrics(o){
  var sx=window.scrollX||0, sy=window.scrollY||0, rg=document.createRange(); rg.selectNodeContents(o.btn.firstChild);
  var g=rg.getBoundingClientRect(), cy=(g.top+g.bottom)/2, bs=boxes(blockOf(o.btn));
  var same=bs.filter(function(r){return r.top<=cy&&r.bottom>=cy;});
  var lb=g.bottom, lt=g.top, lr=g.right;
  same.forEach(function(r){ lb=Math.max(lb,r.bottom); lt=Math.min(lt,r.top); lr=Math.max(lr,r.right); });
  var nx=bs.filter(function(r){return r.top>=lb-1;}).map(function(r){return r.top;});
  var pv=bs.filter(function(r){return r.bottom<=lt+1;}).map(function(r){return r.bottom;});
  var gb=nx.length?(lb+Math.min.apply(null,nx))/2:lb+6, ga=pv.length?(lt+Math.max.apply(null,pv))/2:lt-6;
  return {x:(g.left+g.right)/2+sx, top:g.top+sy, bot:g.bottom+sy, gb:gb+sy, ga:ga+sy, lr:lr+sx, cy:cy+sy};
}
/* 끝점: 글자는 줄 아래 틈으로(위에서 들어올 땐 위 틈), 그림·고르기 카드 이름은 위쪽으로 드나든다 */
/* 넘김(.pk-swipe) 카드 줄에서 옆으로 밀려나 안 보이는 카드면 그 줄을 돌려준다(-1 왼쪽 / 1 오른쪽) */
function swipeOff(o){
  var sw=o.card&&o.card.closest('.pk-swipe'); if(!sw) return null;
  var a=o.anchor.getBoundingClientRect(), b=sw.getBoundingClientRect(), cx=(a.left+a.right)/2;
  return cx<b.left+4?{sw:sw,side:-1}:(cx>b.right-4?{sw:sw,side:1}:null);
}
function port(o){ var r=R(o.anchor);
  if(o.img) return {x:r.cx,p:r.t-1,g:r.t-10,r:r,fig:1};
  var so=swipeOff(o);
  if(so){ var q=R(so.sw); return {x:so.side>0?q.r-14:q.l+14,p:q.t-1,g:q.t-6,r:q,top:1,off:so.side}; }
  var m=metrics(o);
  if(o.card) return {x:m.x,p:m.top-1,g:m.top-5,r:r,m:m,top:1};
  return {x:m.x,p:Math.min(m.bot+1,m.gb-2),g:m.gb,r:r,m:m};
}
function poly(pts,rad){   /* 꺾은선의 모서리를 둥글게 */
  var d='M'+pts[0][0]+' '+pts[0][1];
  for(var i=1;i<pts.length;i++){
    var p=pts[i];
    if(i<pts.length-1){ var a=pts[i-1],c=pts[i+1];
      var l1=Math.hypot(p[0]-a[0],p[1]-a[1]),l2=Math.hypot(c[0]-p[0],c[1]-p[1]),r=Math.min(rad,l1/2,l2/2);
      if(r<0.5){ d+='L'+p[0]+' '+p[1]; continue; }
      var x1=p[0]+(a[0]-p[0])*r/l1,y1=p[1]+(a[1]-p[1])*r/l1,x2=p[0]+(c[0]-p[0])*r/l2,y2=p[1]+(c[1]-p[1])*r/l2;
      d+='L'+x1+' '+y1+'Q'+p[0]+' '+p[1]+' '+x2+' '+y2;
    }else d+='L'+p[0]+' '+p[1];
  }
  return d;
}
function bez(p0,p1,p2,p3,t){ var u=1-t; return [u*u*u*p0[0]+3*u*u*t*p1[0]+3*u*t*t*p2[0]+t*t*t*p3[0], u*u*u*p0[1]+3*u*u*t*p1[1]+3*u*t*t*p2[1]+t*t*t*p3[1]]; }
function addPath(L,d){
  var cls={sub:'t-sub',ex:'t-ex',cmp:'t-cmp',xref:'t-xref'}[L.t];
  var cw={sub:6.5,ex:7,cmp:6.5,xref:5}[L.t];
  var c=document.createElementNS(NS,'path'); c.setAttribute('class','lm-case'); c.setAttribute('d',d); c.setAttribute('stroke-width',cw);
  var p=document.createElementNS(NS,'path'); p.setAttribute('class','lm-line '+cls); p.setAttribute('d',d);
  if(L.t==='sub') p.setAttribute('marker-end','url(#lm-m-tri)');
  if(L.t==='ex') p.setAttribute('marker-end','url(#lm-m-dot)');
  if(L.t==='cmp'){ p.setAttribute('marker-start','url(#lm-m-bar)'); p.setAttribute('marker-end','url(#lm-m-bar)'); }
  p.dataset.lmLine=L.i; c.dataset.lmLine=L.i;
  G.insertBefore(c,G.firstChild); G.appendChild(p);
  if(fresh&&!RM.matches){ p.classList.add('lm-anim'); c.classList.add('lm-anim'); }
}
function tag(L,hint,maxW){   /* 연결어 꼬리표 — 대상이 화면 밖이면 «↓ 4단계» 같은 위치를 앞에 */
  var b=tags[L.i];
  if(!b){ b=document.createElement('button'); b.type='button'; b.className='lm-tag'; b.style.setProperty('--c',COL[L.t]);
    b.addEventListener('click',function(){ goTo(N[other(L)]); });
    tags[L.i]=b; layer.appendChild(b); }
  var o=N[other(L)];
  /* 같은 연결어가 둘 이상 켜지면(선진국 ← 영국·독일) 끝에 상대 이름을 붙여 가른다 */
  var dup=linesOf(active).filter(function(x){return x.w===L.w;}).length>1, txt=L.w+(dup?' — '+o.name:'');
  if(b._k!==hint+'|'+txt){ b._k=hint+'|'+txt; b.textContent='';
    if(hint){ var s=document.createElement('span'); s.className='lm-where'; s.textContent=hint; b.appendChild(s); }
    b.appendChild(document.createTextNode(txt));
    b.setAttribute('aria-label',KIND[L.t]+': '+L.w+' — '+o.name+' 보러 가기'); }
  b.style.maxWidth=maxW+'px'; b.style.left='0px'; b.style.top='0px';
  return b;
}
function hintFor(o,y,sy,vh){ var v=y<sy+70?'↑ '+secLab(o):(y>sy+vh-80?'↓ '+secLab(o):''); if(v) return v; var so=swipeOff(o); return so?(so.side>0?'▶ 넘겨서':'◀ 넘겨서'):''; }
function mkGroup(L,inline){
  var o=N[L.b], g=groups[L.i];
  if(!g){ g=document.createElement('div'); g.className='lm-cg';
    var t=document.createElement('span'); t.className='lm-tag'; t.style.setProperty('--c',COL[L.t]); t.textContent=L.w;
    var ch=document.createElement('div'); ch.className='lm-chip'; ch.innerHTML='<b></b><span></span>';
    ch.querySelector('b').textContent=o.name; ch.querySelector('span').textContent=o.d.chip;
    g.appendChild(t); g.appendChild(ch); groups[L.i]=g; }
  if(inline){ var blk=N[L.a].anchor.closest('p,li,blockquote,figure,.ws-tb')||N[L.a].anchor.parentNode;
    if(!g.classList.contains('lm-inline')||g.previousElementSibling!==blk){ g.classList.add('lm-inline'); g.style.cssText=''; blk.insertAdjacentElement('afterend',g); } }
  else if(g.parentNode!==layer){ g.classList.remove('lm-inline'); layer.appendChild(g); }
  return g;
}
/* 화면 아래 끝에 걸린 꼬리표는 아래에서부터 위로 쌓는다(아래로 밀면 화면 밖으로 잘린다) */
function stackBottom(items,floor){
  var low=items.filter(function(it){return !it.inline&&it.want+it.h>=floor-1;}).sort(function(a,b){return b.want-a.want;});
  var cols={};
  low.forEach(function(it){ var k=Math.round(it.x/40), f=cols[k]===undefined?floor:cols[k]; it.want=Math.min(it.want,f-it.h); cols[k]=it.want-6; });
}
/* 자리 잡기: 원하는 높이에 두되 앞서 놓인 것·말풍선과 겹치면 아래로 */
function settle(items,obst){
  items.sort(function(a,b){return a.want-b.want;});
  var placed=obst.slice();
  items.forEach(function(it){
    var top=it.want, moved=true, n=0;
    while(moved&&n++<40){ moved=false;
      for(var i=0;i<placed.length;i++){ var q=placed[i];
        if(it.x<q.r&&it.x+it.w>q.l&&top<q.b+6&&top+it.h>q.t-6){ top=q.b+6; moved=true; } } }
    it.top=top; placed.push({l:it.x,r:it.x+it.w,t:top,b:top+it.h});
  });
}
function gutterOK(){   /* 본문 상자 오른쪽에 이름표 칸(230px)이 있어야 선을 그린다 — 없으면 이름표가 본문 글을 덮는다 */
  var r=0; [].forEach.call(document.querySelectorAll('.v2-sec'),function(c){ var b=c.getBoundingClientRect(); if(b.width) r=Math.max(r,b.right); });
  if(!r) r=C.getBoundingClientRect().right;
  return (H.clientWidth-r)>=230;
}
function lineMode(){ return WIDE.matches&&gutterOK(); }
function layout(){
  refresh();
  if(!active) return;
  var ls=linesOf(active);
  if(!ls.length){ setActive(null); return; }
  var peers={}; ls.forEach(function(L){ peers[other(L)]=1; });
  marks(active,peers);
  if(printing||!lineMode()){ G.innerHTML=''; Object.keys(tags).forEach(function(k){tags[k].remove();}); tags={};
    Object.keys(groups).forEach(function(k){groups[k].remove();}); groups={};
    off.hidden=true;
    var key=active+':'+ls.map(function(L){return L.i;}).join(',');
    if(!printing&&(sheet.hidden||sheet._k!==key)){ buildSheet(ls); sheet._k=key; }
    if(printing) sheet.hidden=true;
    fresh=false; return; }
  sheet.hidden=true; sheet._k=''; off.hidden=false;
  drawWide(ls); fresh=false;
}
function drawWide(ls){
  var vw=H.clientWidth, vh=window.innerHeight, sx=window.scrollX||0, sy=window.scrollY||0;
  var cards=[].slice.call(document.querySelectorAll('.v2-sec')), boxR=0, boxL=1e9;
  cards.forEach(function(c){ var r=c.getBoundingClientRect(); if(r.width){ boxR=Math.max(boxR,r.right); boxL=Math.min(boxL,r.left); } });
  if(!boxR){ var cr=C.getBoundingClientRect(); boxR=cr.right; boxL=cr.left; }
  var gutter=(vw-boxR)>=230;
  boxR+=sx; boxL+=sx;
  /* 높이를 먼저 0으로 — 안 그러면 접기를 닫아 문서가 줄어도 선 판이 옛 길이를 붙잡는다 */
  svg.setAttribute('height','0'); svg.setAttribute('width',vw);
  svg.setAttribute('height',Math.max(H.scrollHeight,document.body.scrollHeight));
  G.innerHTML='';
  var used={}, mp=port(N[active]);
  /* 나눔: 칩 / 가까움(한 화면 안) / 멂(여백 길) */
  var chip=[], near=[], far=[];
  ls.forEach(function(L){ var o=N[other(L)];
    if(o.chip){ chip.push(L); return; }
    var op=port(o), top=Math.min(mp.r.t,op.r.t), bot=Math.max(mp.r.b,op.r.b);
    L._op=op; L._dy=Math.abs(op.r.cy-mp.r.cy);
    ((bot-top)<=vh*0.8?near:far).push(L); });
  far.sort(function(a,b){return a._dy-b._dy;});   /* 가까운 대상이 안쪽 길 — 선끼리 덜 엇갈린다 */
  var lanes=far.length+chip.length, step=11;
  var lane0=gutter?boxR+9:boxR-27;
  var itemX=lane0+Math.max(0,lanes-1)*step+12;
  var itemW=Math.max(140,Math.min(250,vw+sx-itemX-12));
  var gItems=[], bItems=[];
  /* 칩(다른 차시 상자): 넓으면 여백에, 좁으면 그 문단 아래에 */
  chip.forEach(function(L,k){
    var g=mkGroup(L,!gutter); used['g'+L.i]=1;
    if(gutter){ g.style.width=itemW+'px'; g.style.left=itemX+'px'; g.style.top='0px';
      gItems.push({L:L,el:g,x:itemX,w:itemW,h:g.offsetHeight,want:mp.g-(g.firstChild.offsetHeight+5)-14,chip:1,lane:lane0+(far.length+k)*step}); }
    else bItems.push({L:L,el:g,inline:1});
  });
  /* 먼 선: 아래 틈 → 본문 상자 오른쪽 여백 → 세로 → 대상 */
  far.forEach(function(L,k){
    var lx=lane0+k*step, op=L._op, A=L.a===active?mp:op, B=L.a===active?op:mp, o=N[other(L)];
    addPath(L,poly([[A.x,A.p],[A.x,A.g],[lx,A.g],[lx,B.g],[B.x,B.g],[B.x,B.p]],9));
    var hint=hintFor(o,op.g,sy,vh); used['t'+L.i]=1;
    if(gutter){ var el=tag(L,hint,itemW), h=el.offsetHeight, w=el.offsetWidth;
      var c=Math.max(sy+70,Math.min(op.g,sy+vh-80));
      gItems.push({L:L,el:el,x:itemX,w:w,h:h,want:c-h/2}); }
    else { var e2=tag(L,hint,300), h2=e2.offsetHeight, w2=e2.offsetWidth;
      var y=op.fig?op.g-h2-4:op.g+5; y=Math.max(sy+60,Math.min(y,sy+vh-80-h2));
      bItems.push({L:L,el:e2,x:Math.max(boxL+8,lx-10-w2),w:w2,h:h2,want:y}); }
  });
  /* 가까운 선 — 같은 문단 안 글자끼리는 줄 사이 틈으로 가는 둥근 괄호선(위로 넘는 호는 윗줄·접기 제목을 가로지른다),
     그림이 끼거나 줄이 멀면 부드러운 곡선. 꼬리표는 줄 끝 빈자리에 두고 옅은 끌줄로 잇는다 */
  near.forEach(function(L){
    var op=L._op, A=L.a===active?mp:op, B=L.a===active?op:mp, d, ly, lx0, o=N[other(L)];
    var txt=A.m&&B.m&&!A.top&&!B.top, dyl=txt?Math.abs(A.m.cy-B.m.cy):1e9;
    if(txt&&dyl<4){ ly=Math.max(A.g,B.g);
      d=poly([[A.x,A.p],[A.x,ly],[B.x,ly],[B.x,B.p]],6); lx0=Math.max(A.x,B.x); }
    else if(txt&&dyl<110){ var up=A.m.cy<B.m.cy, U=up?A:B, D=up?B:A; ly=U.g;
      var pu=[U.x,U.p], pd=[D.x,D.m.top-1];
      var pts=[pu,[U.x,ly],[D.x,ly],pd]; if(!up) pts.reverse();
      d=poly(pts,6); lx0=Math.max(A.x,B.x); }
    else{ var down=A.r.cy<B.r.cy;
      var y0=down?(A.fig?A.r.b+1:A.p):(A.fig||A.top?A.p:A.m.top-1), y3=down?(B.fig||B.top?B.p:B.m.top-1):(B.fig?B.r.b+1:B.p);
      var k=Math.max(24,Math.min(160,Math.abs(y3-y0)*0.45))*(down?1:-1);
      var q0=[A.x,y0],q1=[A.x,y0+k],q2=[B.x,y3-k],q3=[B.x,y3], lp=bez(q0,q1,q2,q3,L.a===active?0.75:0.25);
      d='M'+q0+'C'+q1+' '+q2+' '+q3; ly=lp[1]; lx0=lp[0]; }
    addPath(L,d); used['t'+L.i]=1;
    var el=tag(L,hintFor(o,ly,sy,vh),250), w=el.offsetWidth, h=el.offsetHeight;
    var freeX=Math.max(A.m?A.m.lr:A.r.r,B.m?B.m.lr:B.r.r)+14, lim=boxR-(gutter?16:10), x, lead=true;   /* 카드 안 줄 끝 빈자리에 다 들어갈 때만, 아니면 여백 칸 */
    if(freeX+w<=lim&&!A.top&&!B.top) x=freeX;   /* 고르기 카드에 닿는 선의 꼬리표는 카드 사진을 가리지 않게 여백 칸으로 */
    else if(gutter){ x=itemX; }
    else { x=Math.max(boxL+8,lim-w); lead=false; }
    var y=Math.max(sy+60,Math.min(ly-h/2,sy+vh-80-h));
    if(lead&&x>lx0+8){ var ld=document.createElementNS(NS,'path'); ld.setAttribute('class','lm-lead'); ld.setAttribute('stroke',COL[L.t]);
      ld.setAttribute('d','M'+(lx0+6)+' '+ly+'H'+x); G.appendChild(ld); }
    (x===itemX&&gutter?gItems:bItems).push({L:L,el:el,x:x,w:w,h:h,want:y,fixed:x!==itemX});
  });
  /* 보충 말풍선(gl-pop)은 피한다 */
  var obst=[].slice.call(document.querySelectorAll('.gl-layer .gl-pop')).filter(function(p){return !p.hidden&&rendered(p);}).map(function(p){var r=R(p);return {l:r.l,r:r.r,t:r.t,b:r.b};});
  stackBottom(gItems,sy+vh-80); stackBottom(bItems,sy+vh-80);
  settle(gItems,obst);
  gItems.forEach(function(it){ it.el.style.left=it.x+'px'; it.el.style.top=it.top+'px';
    if(it.chip){   /* 칩으로 들어가는 선 */
      var cy=it.top+it.el.lastChild.offsetTop+14;
      var pts=Math.abs(cy-mp.g)<2?[[mp.x,mp.p],[mp.x,mp.g],[it.x,mp.g]]:[[mp.x,mp.p],[mp.x,mp.g],[it.lane,mp.g],[it.lane,cy],[it.x,cy]];
      addPath(it.L,poly(pts,9)); } });
  settle(bItems.filter(function(it){return !it.inline;}),[]);
  bItems.forEach(function(it){
    if(it.inline){ var cr=R(it.el.lastChild), lx=lane0+(far.length+chip.indexOf(it.L))*step, cy=cr.t+14;
      addPath(it.L,poly([[mp.x,mp.p],[mp.x,mp.g],[lx,mp.g],[lx,cy],[cr.r,cy]],9)); return; }
    it.el.style.left=it.x+'px'; it.el.style.top=it.top+'px'; });
  Object.keys(tags).forEach(function(k){ if(!used['t'+k]){ tags[k].remove(); delete tags[k]; } });
  Object.keys(groups).forEach(function(k){ if(!used['g'+k]){ groups[k].remove(); delete groups[k]; } });
  if(fresh&&!RM.matches) Object.keys(tags).map(function(k){return tags[k];}).concat(Object.keys(groups).map(function(k){return groups[k];})).forEach(function(e){ e.classList.remove('lm-anim'); void e.offsetWidth; e.classList.add('lm-anim'); });
}

/* ---------- 5) 좁은 화면: 아래 판 ---------- */
function buildSheet(ls){
  var me=N[active];
  sheet.innerHTML='<div class="lm-sh-h"><b></b><button type="button" class="lm-sh-x" aria-label="닫기">×</button></div>';
  sheet.querySelector('b').textContent='이어지는 것 · '+me.name;
  sheet.querySelector('.lm-sh-x').addEventListener('click',function(){ setActive(null,me.btn); });
  ls.forEach(function(L){
    var o=N[other(L)], row=document.createElement('div'); row.className='lm-row';
    var dir=L.t==='cmp'?'↔ ':(L.a===active?'→ ':'← ');
    row.innerHTML=swatch(L.t)+'<div><span class="lm-to"></span><span class="lm-w"></span></div>';
    row.querySelector('.lm-to').textContent=KIND[L.t]+' '+dir+o.name;
    row.querySelector('.lm-w').textContent=L.w;
    if(o.chip){ var cd=document.createElement('span'); cd.className='lm-cd'; cd.textContent=o.d.chip; row.children[1].appendChild(cd); row.appendChild(document.createElement('span')); }
    else{ var g=document.createElement('button'); g.type='button'; g.className='lm-go'; g.style.setProperty('--c',COL[L.t]); g.textContent='보러 가기';
      g.setAttribute('aria-label',o.name+' 보러 가기'); g.addEventListener('click',function(){ goTo(o); }); row.appendChild(g); }
    sheet.appendChild(row);
  });
  sheet.hidden=false;
}
function sheetH(){ return sheet.hidden?0:sheet.getBoundingClientRect().height; }
function keepVisibleAboveSheet(el){
  var r=el.getBoundingClientRect(), room=window.innerHeight-sheetH()-12;
  if(r.bottom>room||r.top<8) window.scrollBy({top:r.top-Math.max(16,(room-r.height)/2),behavior:RM.matches?'auto':'smooth'});
}
function goTo(o){
  if(o.chip||!o.anchor) return;
  var sw=o.card&&o.card.closest('.pk-swipe');
  if(sw&&swipeOff(o)){ sw.scrollTo({left:o.card.offsetLeft-sw.offsetLeft,behavior:RM.matches?'auto':'smooth'}); setTimeout(function(){ goTo(o); },RM.matches?60:420); return; }
  var el=o.anchor, r=el.getBoundingClientRect(), room=window.innerHeight-sheetH();
  window.scrollBy({top:r.top-Math.max(16,(room-r.height)/2),behavior:RM.matches?'auto':'smooth'});
  var cls=RM.matches?'lm-flash-still':'lm-flash';
  el.classList.remove('lm-flash','lm-flash-still'); void el.offsetWidth; el.classList.add(cls);
  setTimeout(function(){ el.classList.remove(cls); },2000);
}

/* ---------- 6) 누르기·다시 그리기 ---------- */
Object.keys(N).forEach(function(id){ var o=N[id]; if(!o.btn) return;
  o.btn.addEventListener('click',function(e){ e.stopPropagation(); if(o.btn.disabled) return; setActive(active===id?null:id); }); });
off.addEventListener('click',function(){ var b=active&&N[active].btn; setActive(null,b); });
document.addEventListener('keydown',function(e){ if(e.key==='Escape'&&active){ var b=N[active].btn; setActive(null,b); } });
var raf=0; function schedule(){ if(raf) return; raf=requestAnimationFrame(function(){ raf=0; layout(); }); }
window.addEventListener('resize',schedule);
window.addEventListener('scroll',function(){ if(active&&lineMode()) schedule(); },{passive:true});
document.addEventListener('scroll',function(e){ if(e.target!==document&&e.target.closest&&e.target.closest('.pk-swipe')) schedule(); },{capture:true,passive:true});
document.addEventListener('toggle',schedule,true);
document.addEventListener('load',schedule,true);
window.addEventListener('load',schedule);
if(window.ResizeObserver) new ResizeObserver(schedule).observe(document.body);
if(window.MutationObserver){
  new MutationObserver(schedule).observe(H,{attributes:true,attributeFilter:['class']});
  [].slice.call(document.querySelectorAll('.ws-pick')).forEach(function(w){ new MutationObserver(function(rs){
    if(rs.some(function(r){ return !(r.target.classList&&r.target.classList.contains('lm-n')); })) schedule(); })
    .observe(w,{attributes:true,subtree:true,attributeFilter:['class']}); });
}
if(document.fonts&&document.fonts.ready) document.fonts.ready.then(schedule);
if(WIDE.addEventListener) WIDE.addEventListener('change',schedule);
window.addEventListener('beforeprint',function(){ printing=true; layout(); });
window.addEventListener('afterprint',function(){ printing=false; layout(); });
refresh();
})();
