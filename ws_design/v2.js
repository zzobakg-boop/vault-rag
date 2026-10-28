(function(){
var C=document.querySelector('.container'); if(!C) return;
// 1) 블록 목소리 분류
[].forEach.call(C.querySelectorAll('blockquote'),function(b){
  var t=b.textContent.trim();
  if(t.indexOf('🎙️')===0){b.classList.add('v2-voice');b.innerHTML=b.innerHTML.replace('🎙️','').replace(/^\s+/,'');var w=document.createElement('span');w.className='v2-who';w.textContent='선생님 입담';b.insertBefore(w,b.firstChild);}
  else if(t.indexOf('📕')===0)b.classList.add('v2-task');
  else if(t.indexOf('💡')===0)b.classList.add('v2-key');
  else if(/^(🔍|🧭|✍️)/.test(t))b.classList.add('v2-ask');
});
[].forEach.call(C.querySelectorAll('p'),function(p){var t=p.textContent.trim();if(/^💬/.test(t)){p.classList.add('v2-q');p.innerHTML=p.innerHTML.replace('💬','').replace(/^\s+/,'');}});
// 2) h2마다 묶어 카드로 (활동 section.ws-do는 그대로 카드)
var kids=[].slice.call(C.children), secs=[], cur=null;
kids.forEach(function(el){
  if(el.tagName==='H2'){cur=document.createElement('section');cur.className='v2-sec';C.insertBefore(cur,el);secs.push(cur);}
  else if(el.matches&&el.matches('section.ws-do')){el.classList.add('v2-sec');secs.push(el);cur=null;return;}
  if(cur&&el.tagName!=='BR')cur.appendChild(el);
});
// 3) 단계 머리: «📖 1단계: 제목 — 부제» → 킥커 + 제목 + 부제
secs.forEach(function(s,k){
  s.id='v2s'+k; var h=s.querySelector('h2'); if(!h)return;
  var m=h.textContent.match(/^📖\s*(\d)단계:\s*(⭐\s*)?(.+?)(\s+—\s+(.+))?$/);
  if(m){s.classList.add('step');var kk=document.createElement('div');kk.className='v2-kicker';kk.innerHTML='<b>STEP '+m[1]+'</b>'+(m[2]?'⭐ 핵심':'');s.insertBefore(kk,h);
    h.innerHTML=m[3]+(m[5]?'<span class="v2-sub">'+m[5]+'</span>':'');s.dataset.lab=m[1]+'단계';s.dataset.n=m[1];}
  else{s.dataset.lab=h.textContent.replace(/^[^\w가-힣]+/,'').split('—')[0].trim();s.dataset.n=h.textContent.trim().slice(0,2);}
});
// 4) 진도 레일
var R=document.createElement('nav');R.className='v2-rail';R.setAttribute('aria-label','학습지 차례');
R.innerHTML='<div class="v2-rh"><h4>오늘의 길</h4><button type="button" class="v2-b v2-pos" aria-label="오늘의 길 위치 바꾸기"></button><button type="button" class="v2-b v2-fold" aria-expanded="true"></button></div>';
var H=document.documentElement;function sg(k){try{return localStorage.getItem(k)}catch(e){return null}}function ss(k,v){try{localStorage.setItem(k,v)}catch(e){}}
function paint(){var top=H.classList.contains('v2-top'),fd=H.classList.contains('v2-folded');
  R.querySelector('.v2-pos').textContent=top?'⇤ 왼쪽에':'⇡ 위로';R.querySelector('.v2-pos').title=top?'오늘의 길을 왼쪽에 두기':'오늘의 길을 위로 올리기';
  var f=R.querySelector('.v2-fold');f.textContent=fd?'펴기 ▸':'◂ 접기';f.setAttribute('aria-expanded',fd?'false':'true');}
if(sg('v2-top')==='1')H.classList.add('v2-top');if(sg('v2-fold')==='1')H.classList.add('v2-folded');
R.addEventListener('click',function(e){var b=e.target.closest('.v2-b');if(!b)return;
  if(b.classList.contains('v2-pos')){H.classList.toggle('v2-top');ss('v2-top',H.classList.contains('v2-top')?'1':'0');}
  else{H.classList.toggle('v2-folded');ss('v2-fold',H.classList.contains('v2-folded')?'1':'0');}
  paint();});
setTimeout(paint,0);
secs.forEach(function(s){var a=document.createElement('a');a.href='#'+s.id;a.dataset.s=s.id;
  var n=s.dataset.n;a.innerHTML='<span class="n">'+(/^\d$/.test(n)?n:n)+'</span><span class="t">'+s.dataset.lab+'</span><span class="c"></span>';R.appendChild(a);});
var meter=document.createElement('div');meter.className='v2-meter';meter.innerHTML='<i></i>';R.appendChild(meter);
var mtx=document.createElement('div');mtx.className='v2-mtx';R.appendChild(mtx);
C.insertBefore(R,C.firstChild);
function tally(){var all=0,fill=0;
  secs.forEach(function(s){var ins=s.querySelectorAll('input.blank-input,textarea.activity-input');var f=0;[].forEach.call(ins,function(i){if(i.value.trim())f++;});
    all+=ins.length;fill+=f;var a=R.querySelector('a[data-s="'+s.id+'"]');if(!a)return;a.querySelector('.c').textContent=ins.length?f+'/'+ins.length:'';a.classList.toggle('done',ins.length>0&&f===ins.length);});
  meter.firstChild.style.width=(all?fill/all*100:0)+'%';mtx.textContent='채운 칸 '+fill+' / '+all;}
document.addEventListener('input',tally);tally();
if('IntersectionObserver' in window){var io=new IntersectionObserver(function(es){es.forEach(function(e){if(e.isIntersecting){[].forEach.call(R.querySelectorAll('a'),function(a){a.classList.toggle('on',a.dataset.s===e.target.id);if(a.dataset.s===e.target.id&&R.scrollWidth>R.clientWidth)R.scrollLeft=a.offsetLeft-20;});}});},{rootMargin:'-30% 0px -65% 0px'});secs.forEach(function(s){io.observe(s);});}
})();
(function(){var cb=document.querySelector('.control-bar');function f(){if(cb)document.documentElement.style.setProperty('--cbh',(cb.offsetHeight+(innerWidth<=640?0:8))+'px');}f();addEventListener('resize',f);addEventListener('load',f);setTimeout(f,800);})();
