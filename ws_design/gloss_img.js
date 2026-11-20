/* 보충 말풍선 안 사진(gloss.js 짝) — 2026-11-17 천대현 9-1~2 «대표적인 곡물 메이저 회사 사진과 관련 내용을 말풍선으로».
   원고 :::개념 잇기의 보충 줄 끝에 «| 그림 | images/….webp | 캡션»이 있는 차시에만 실린다(gloss.js 뒤에 돈다).
   사진은 말풍선 글 위에 둔다. 말풍선을 열 때만 받도록 lazy로 둔다. */
(function(){
var GL=null; try{ GL=JSON.parse((document.getElementById('gl-data')||{}).textContent||'null'); }catch(e){ GL=null; }
if(!GL||!GL.forEach) return;
GL.forEach(function(g){
  if(!g.img) return;
  var pop=document.getElementById(g.id); if(!pop) return;
  var fig=document.createElement('figure'); fig.className='gl-img';
  var im=document.createElement('img'); im.src=g.img; im.loading='lazy';
  im.alt=g.img_cap||g.word||'';
  /* 2026-11-17 역사 5-1 «나폴레옹 법전 표지»: 세로 사진은 가로 틀(cover)에 잘려 제목이 사라진다 — 세로면 자르지 않고 줄여 넣는다. 가로 사진은 그대로 */
  /* 2026-11-18 역사 5-1 «7월 혁명»: 원고 «@15»(img_y) — 가로 틀에서 위아래 어디를 보여 줄지. 없으면 가운데(그대로) */
  if(g.img_y!=null) im.style.objectPosition='50% '+g.img_y+'%';
  im.onload=function(){ if(im.naturalHeight>im.naturalWidth) fig.classList.add('gl-img-tall'); };
  /* 2026-11-17 역사 5-1 «테니스코트의 서약» 스케치: 말풍선 틀에 잘린 구석(라켓·공)을 보려면 크게 봐야 한다 — 본문 그림과 같은 확대 창(zoom.js) 링크로 감싼다 */
  var a=document.createElement('a'); a.className='ws-fig-zoom'; a.href=g.img; a.target='_blank'; a.rel='noopener'; a.title='눌러서 크게 보기';
  a.appendChild(im); fig.appendChild(a);
  if(g.img_cap){ var c=document.createElement('figcaption'); c.textContent=g.img_cap; fig.appendChild(c); }
  var body=pop.querySelector('.gl-body'); if(body) body.insertAdjacentElement('beforebegin',fig); else pop.appendChild(fig);
});
})();
