/* 2026-11-10 사회② Ⅷ: 보충 말풍선 — 교사용 교과서의 파란 주석처럼. 방식 1 낱말 누르기 · 방식 2 채점해서 맞힌 빈칸만.
   넓은 화면(1280px~)은 본문 상자 오른쪽 여백, 좁으면 그 문단 아래. 인쇄는 열린 것만 문단 아래 글로. 시험판 = 8-5~6 검토판 v3(11/9) */
(function(){
/* 자료는 원고 md의 :::개념 잇기 블록 «보충»·«이어 보기» 줄 → JSON 자료 칸(id gl-data).
   [{id, kind: blank(맞힌 빈칸만 열림)·word(낱말 누르기), blank(빈칸 번호), word, near, fold, label, text}]
   보충 문장은 교과서·교사용 주석을 옮기지 않고 우리 말로 쓰며, 뒤 빈칸 답 낱말은 넣지 않는다 */
var GL=null; try{ GL=JSON.parse((document.getElementById('gl-data')||{}).textContent||'null'); }catch(e){ GL=null; }
if(!GL||!GL.length) return;
var H=document.documentElement, C=document.querySelector('.container'); if(!C) return;
var WIDE=window.matchMedia('(min-width:1280px)'), RM=window.matchMedia('(prefers-reduced-motion:reduce)');
var printing=false, items=[];
var NS='http://www.w3.org/2000/svg';
var layer=document.createElement('div'); layer.className='gl-layer';
var svg=document.createElementNS(NS,'svg'); svg.setAttribute('class','gl-svg'); svg.setAttribute('aria-hidden','true');
layer.appendChild(svg); document.body.appendChild(layer);

function mkPop(g){
  var p=document.createElement('aside'); p.className='gl-pop'; p.id=g.id; p.hidden=true;
  p.setAttribute('role','note'); p.setAttribute('aria-label',(g.label||'보충')+': '+g.word); if(g.label) p.classList.add('gl-link');
  p.innerHTML='<div class="gl-head">'+(g.label||'보충')+'<span class="gl-word"></span></div><div class="gl-body"></div><button type="button" class="gl-x" aria-label="보충 닫기">×</button>';
  p.querySelector('.gl-word').textContent=g.word; p.querySelector('.gl-body').textContent=g.text.split(' // ').join('\n');
  return p;
}
function animate(el){ if(RM.matches) return; el.classList.remove('gl-anim'); void el.offsetWidth; el.classList.add('gl-anim'); }

GL.forEach(function(g){
  var it={g:g,open:false,locked:false,trig:null,block:null,pop:mkPop(g),path:null,dot:null,fresh:false};
  if(g.kind==='blank'){
    var inp=[].slice.call(document.querySelectorAll('.blank-input')).filter(function(e){ return e.dataset.id===String(g.blank); })[0]; if(!inp) return;   /* 선택자 문자열로 쓰지 않는다 — 정규식으로 입력칸을 세는 도구가 하나로 친다 */
    var b=document.createElement('button'); b.type='button'; b.className='gl-badge'; b.hidden=true; b.textContent='+';
    b.setAttribute('aria-controls',g.id); b.setAttribute('aria-expanded','false'); b.setAttribute('aria-label',g.word+' 보충 보기');
    inp.insertAdjacentElement('afterend',b);
    it.trig=b; it.input=inp; it.locked=true;
    inp.addEventListener('input',function(){ if(!it.locked){ lock(it); } });
  }else{
    var root=C;
    if(g.fold){ var fold=[].slice.call(document.querySelectorAll('details.ws-fold')).filter(function(d){var s=d.querySelector('summary');return s&&s.textContent.indexOf(g.fold)>=0;})[0];
      if(!fold) return; root=fold.querySelector('.ws-fold-body')||fold; }
    var w=document.createTreeWalker(root,NodeFilter.SHOW_TEXT),n,hit=null;
    while((n=w.nextNode())){ var s0=g.near?n.data.indexOf(g.near):0; if(s0<0) continue; var k=n.data.indexOf(g.word,s0); if(k>=0){hit=n.splitText(k); hit.splitText(g.word.length); break;} }
    if(!hit) return;
    var t=document.createElement('button'); t.type='button'; t.className='gl-t';
    t.setAttribute('aria-controls',g.id); t.setAttribute('aria-expanded','false');
    t.appendChild(document.createTextNode(g.word));
    var mk=document.createElement('span'); mk.className='gl-mk'; mk.setAttribute('aria-hidden','true'); mk.textContent='+'; t.appendChild(mk);
    hit.parentNode.replaceChild(t,hit);
    it.trig=t; it.mk=mk;
  }
  it.block=it.trig.closest('p,li')||it.trig.parentNode;
  it.trig.addEventListener('click',function(){ setOpen(it,!it.open); });
  it.pop.querySelector('.gl-x').addEventListener('click',function(){ setOpen(it,false); it.trig.focus(); });
  items.push(it);
});
if(!items.length) return;

function setOpen(it,on){
  if(on&&it.locked) return;
  it.open=on; it.pop.hidden=!on; it.fresh=on;
  it.trig.setAttribute('aria-expanded',on?'true':'false');
  if(it.mk) it.mk.textContent=on?'−':'+';
  if(on) animate(it.pop);
  layout();
}
function lock(it){ it.locked=true; it.trig.hidden=true; setOpen(it,false); }
function unlock(it){ var was=it.locked; it.locked=false; it.trig.hidden=false; if(was) animate(it.trig); }

/* 방식 2: 채점하기 뒤에 맞힌 칸만 연다. 초기화·답 고치기면 다시 잠근다 */
var _check=window.check, _reset=window.reset;
if(typeof _check==='function') window.check=function(){ var r=_check.apply(this,arguments);
  items.forEach(function(it){ if(!it.input) return;
    if(it.input.classList.contains('correct')){ unlock(it); setOpen(it,true); } else { lock(it); } });
  return r; };
if(typeof _reset==='function') window.reset=function(){ var r=_reset.apply(this,arguments); items.forEach(function(it){ if(it.input) lock(it); }); return r; };

function wideOK(){ return !printing && WIDE.matches; }
function layout(){
  H.classList.toggle('gl-wide',wideOK());
  var vw=H.clientWidth, sx=window.scrollX||0, sy=window.scrollY||0, placed=[], use=[];
  items.forEach(function(it){
    var card=it.trig.closest('.v2-sec')||C, cr=card.getBoundingClientRect();
    var space=vw-cr.right;
    it.mode=(wideOK()&&space>=250)?'side':'inline';
    if(it.mode==='inline'){
      if(!it.pop.classList.contains('gl-inline')||it.pop.previousElementSibling!==it.block){ it.block.insertAdjacentElement('afterend',it.pop); }
      it.pop.classList.add('gl-inline'); it.pop.style.cssText='';
    }else{
      if(it.pop.parentNode!==layer) layer.appendChild(it.pop);
      it.pop.classList.remove('gl-inline');
      var r=it.trig.getBoundingClientRect(), visible=it.open&&(r.width||r.height);
      it.pop.style.display=visible?'':'none';
      if(visible){
        var lineY=r.bottom+3;
        if(it.input){ var ir=it.input.getBoundingClientRect(); lineY=Math.max(ir.bottom,r.bottom)+3; }
        var left=cr.right+18, width=Math.min(270,vw-left-14);
        use.push({it:it,x0:r.right+1,y0:lineY,xk:cr.right-12,left:left,width:width,want:lineY-17});
      }
    }
  });
  /* 겹치지 않게 위에서부터 */
  use.sort(function(a,b){return a.want-b.want;});
  var floor=-1e9;
  use.forEach(function(u){
    var top=Math.max(u.want,floor);
    u.it.pop.style.left=(u.left+sx)+'px'; u.it.pop.style.top=(top+sy)+'px'; u.it.pop.style.width=u.width+'px';
    floor=top+u.it.pop.offsetHeight+12; u.top=top;
  });
  /* 선: 낱말 끝 → 그 줄 아래 틈 → 상자 가장자리 → 말풍선 머리 */
  /* v3: 먼저 0으로 — 인쇄 화면에서 잰 폭을 붙잡고 있으면 화면으로 돌아와 가로 스크롤이 생긴다(v2 결함) */
  svg.setAttribute('width',0); svg.setAttribute('height',0);
  var dw=vw, dh=document.documentElement.scrollHeight;
  svg.setAttribute('width',dw); svg.setAttribute('height',dh);
  items.forEach(function(it){ if(it.path){ it.path.remove(); it.dot.remove(); it.path=it.dot=null; } });
  use.forEach(function(u){
    var x0=u.x0+sx, y0=u.y0+sy, xk=u.xk+sx, xb=u.left+sx, yb=u.top+sy+17, d;
    if(Math.abs(yb-y0)<1) d='M'+x0+' '+y0+'H'+xb;
    else d='M'+x0+' '+y0+'H'+xk+'C'+(xk+16)+' '+y0+' '+(xb-16)+' '+yb+' '+xb+' '+yb;
    var p=document.createElementNS(NS,'path'); p.setAttribute('class','gl-path'); p.setAttribute('d',d);
    var c=document.createElementNS(NS,'circle'); c.setAttribute('class','gl-dot'); c.setAttribute('cx',x0); c.setAttribute('cy',y0); c.setAttribute('r','2.4');
    svg.appendChild(p); svg.appendChild(c); u.it.path=p; u.it.dot=c;
    if(u.it.fresh) animate(p);
  });
  items.forEach(function(it){ it.fresh=false; });
}
var raf=0; function schedule(){ if(raf) return; raf=requestAnimationFrame(function(){ raf=0; layout(); }); }
window.addEventListener('resize',schedule);
document.addEventListener('toggle',schedule,true);
if(window.ResizeObserver) new ResizeObserver(schedule).observe(document.body);
if(document.fonts&&document.fonts.ready) document.fonts.ready.then(schedule);
window.addEventListener('load',schedule);
/* 인쇄: 열린 말풍선만 그 문단 아래 글로 */
window.addEventListener('beforeprint',function(){ printing=true; layout(); });
window.addEventListener('afterprint',function(){ printing=false; layout(); });
layout();
})();
