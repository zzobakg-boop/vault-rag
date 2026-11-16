/* 보충 말풍선 안 소리(gloss.js 짝) — 2026-11-16 천대현 5-1 «'라 마르세예즈'를 들을 수 있도록 노래 음원을 말풍선으로».
   원고 :::개념 잇기의 보충 줄 끝에 «| 소리 | images/….mp3 | 설명»이 있는 차시에만 실린다(gloss.js 뒤에 돈다).
   스스로 재생하지 않는다 — 학생이 재생 단추를 누른다. 말풍선이 닫히면 소리도 멈춘다. */
(function(){
var GL=null; try{ GL=JSON.parse((document.getElementById('gl-data')||{}).textContent||'null'); }catch(e){ GL=null; }
if(!GL||!GL.forEach) return;
GL.forEach(function(g){
  if(!g.audio) return;
  var pop=document.getElementById(g.id); if(!pop) return;
  var box=document.createElement('div'); box.className='gl-aud';
  var a=document.createElement('audio'); a.controls=true; a.preload='none'; a.src=g.audio;
  a.setAttribute('aria-label',(g.word||'')+' 듣기');
  box.appendChild(a);
  if(g.audio_cap){ var c=document.createElement('div'); c.className='gl-aud-cap'; c.textContent=g.audio_cap; box.appendChild(c); }
  var body=pop.querySelector('.gl-body'); (body||pop).insertAdjacentElement('afterend',box);
  function hush(){ if(pop.hidden||pop.style.display==='none') a.pause(); }
  if(window.MutationObserver) new MutationObserver(hush).observe(pop,{attributes:true,attributeFilter:['hidden','style']});
});
})();
