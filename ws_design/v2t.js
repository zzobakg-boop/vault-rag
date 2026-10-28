/* v2 사회 교재형 층(design_layer: 사회교재) — 원고의 글자·입력칸은 건드리지 않고 장치만 덧붙인다(글자 마디 단위로만 감싼다). 설정은 worksheet-gen이 frontmatter lens·seeing에서 만든 #v2t-cfg */
(function(){
var cfg={};try{cfg=JSON.parse(document.getElementById('v2t-cfg').textContent)}catch(e){}
var TH={'지역':['--t-region','어디에 무엇이 모여 있고, 어디가 왜 다를까?','M8 1.5a4.5 4.5 0 0 0-4.5 4.5c0 3.4 4.5 8.5 4.5 8.5s4.5-5.1 4.5-8.5A4.5 4.5 0 0 0 8 1.5zm0 6.2a1.7 1.7 0 1 1 0-3.4 1.7 1.7 0 0 1 0 3.4z'],
'이동':['--t-move','사람·물건·생각이 어디서 어디로 옮겨 갈까?','M2 8h9.2L8.6 5.4 9.8 4.2 14.6 9l-4.8 4.8-1.2-1.2 2.6-2.6H2z'],
'세계화':['--t-glob','먼 곳의 일이 우리와 어떻게 이어질까?','M8 1.5a6.5 6.5 0 1 0 0 13 6.5 6.5 0 0 0 0-13zm4.9 6h-2.4a10 10 0 0 0-.9-4 5 5 0 0 1 3.3 4zM8 3c.7.9 1.3 2.5 1.4 4.5H6.6C6.7 5.5 7.3 3.9 8 3zM6.4 3.5a10 10 0 0 0-.9 4H3.1a5 5 0 0 1 3.3-4zM3.1 8.5h2.4a10 10 0 0 0 .9 4 5 5 0 0 1-3.3-4zM8 13c-.7-.9-1.3-2.5-1.4-4.5h2.8C9.3 10.5 8.7 12.1 8 13zm1.6-.5a10 10 0 0 0 .9-4h2.4a5 5 0 0 1-3.3 4z'],
'자연과 사람':['--t-nat','자연환경과 사람의 삶은 서로 어떻게 영향을 줄까?','M13.5 2.5S6 2 3.6 6.6c-1.5 2.9-.4 5.6.5 6.4L2.5 14.6l.9.9 1.6-1.6c.9.7 3.5 1.7 6.3.2C15.7 11.8 13.5 2.5 13.5 2.5zM5.6 11.6l4.6-4.6-.7-.7-4.6 4.6z'],
'경관':['--t-land','눈에 보이는 풍경에 무엇이 새겨져 있을까?','M1.5 13.5 6 6.5l3 4 2-2.5 3.5 5.5zM11.5 5.5a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3z']};
function chip(n){var t=TH[n];if(!t)return null;var s=document.createElement('span');s.className='v2t-chip';s.style.setProperty('--c','var('+t[0]+')');
s.innerHTML='<svg viewBox="0 0 16 16" aria-hidden="true"><path fill="currentColor" d="'+t[2]+'"/></svg>';s.appendChild(document.createTextNode(n));return s}
var secs=[].slice.call(document.querySelectorAll('.v2-sec'));
function secBy(re){return secs.filter(function(x){var h=x.querySelector('h2');return h&&re.test((x.dataset.lab||'')+' '+h.textContent)})[0]}
/* 1) 단계·활동마다 렌즈 — STEP 줄 안 작은 글자 */
function esc(t){return t.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')}
var used=[];(cfg.lens||[]).forEach(function(r){var x=secBy(new RegExp(esc(r[0])));if(!x)return;var h=x.querySelector('h2');
var kk=x.querySelector('.v2-kicker')||x.querySelector('.ws-do-tag');var w=document.createElement('span');w.className='v2t-klens';r[1].forEach(function(n){var t=TH[n];if(!t)return;if(used.indexOf(n)<0)used.push(n);var s=document.createElement('span');s.innerHTML='<svg viewBox="0 0 16 16" aria-hidden="true"><path fill="currentColor" d="'+t[2]+'"/></svg>';s.appendChild(document.createTextNode(n));w.appendChild(s)});if(kk){if(kk.classList.contains('v2-kicker'))kk.appendChild(w);else{kk.parentNode.insertBefore(w,kk.nextSibling);w.style.marginLeft='8px'}}});
/* 2) 학습 목표 아래 «이 차시를 읽는 렌즈» 한 줄 접기 */
var goal=secBy(/학습 목표/);if(goal){if(used.length){var lg=document.createElement('details');lg.className='v2t-legend';lg.innerHTML='<summary>이 차시를 읽는 렌즈 <b>'+used.join(' · ')+'</b><i>눌러서 렌즈별 질문 보기</i></summary><ul></ul>';used.forEach(function(n){var li=document.createElement('li');li.appendChild(chip(n));li.appendChild(document.createTextNode(TH[n][1]));lg.querySelector('ul').appendChild(li)});goal.appendChild(lg)}}
/* 5) 장 끝 상자 이름 */
function tag(el,t){if(!el)return;el.dataset.v2tTag='1';var dt=el.querySelector('.ws-do-tag');if(dt){dt.textContent=t;return}var s=document.createElement('div');s.className='v2t-tag';s.textContent=t;el.insertBefore(s,el.firstChild)}
(cfg.boxes||[]).forEach(function(r){var x=secBy(new RegExp(esc(r[0])));if(x){tag(x,r[1]);if(r[2])x.classList.add(r[2])}});
/* 활동 상자: 찬반 카드가 있으면 «논쟁 속으로», 나머지는 «직접 해 보기» */
[].slice.call(document.querySelectorAll('.ws-do')).forEach(function(x){var hh=x.querySelector('h2');if(x.dataset.v2tTag||!hh||!/활동/.test(hh.textContent))return;var deb=[].slice.call(x.querySelectorAll('.pk-b,button')).some(function(b){return /찬성/.test(b.textContent)});tag(x,deb?'논쟁 속으로':'직접 해 보기');if(deb)x.classList.add('v2t-debate')});
if(cfg.seeing){var sw=[].slice.call(document.querySelectorAll('.ws-sw')).filter(function(e){var h=e.querySelector('.ws-sw-head');return h&&h.textContent.indexOf(cfg.seeing)>=0})[0];
if(sw){sw.classList.add('v2t-seeing');tag(sw,'사진으로 읽기');var hk=document.querySelector('.hero-hook');if(hk&&cfg.seeingGo){var g=document.createElement('span');g.className='v2t-hero-go';g.textContent=cfg.seeingGo;hk.appendChild(g)}}}
/* 제목 앞 이모지: 첫 글자 마디만 잘라 작은 span에(글자·입력칸 불변) */
[].slice.call(document.querySelectorAll('.v2-sec h2')).forEach(function(h){var n=h.firstChild;if(!n||n.nodeType!==3)return;var m=n.data.match(/^\s*([\u2600-\u27BF\uD83C-\uDBFF\uDC00-\uDFFF\uFE0F]+)\s*/);if(!m)return;var r=n.splitText(m[0].length);var s=document.createElement('span');s.className='v2t-ico';s.textContent=m[1];h.insertBefore(s,r);h.removeChild(n)});
})();
