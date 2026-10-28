/* v2 사회 층 — 표지 제목 «사회② 단원 n차시 — 제목 (교과서 질문)»을 세 층으로 나눈다(글자는 그대로) */
(function(){var t=document.querySelector('.hero-title');if(!t||t.children.length)return;
var s=t.textContent.trim(),m=s.match(/^(.*?\d+-\d+차시)\s*—\s*(.*?)\s*(\(([^()]*)\))?$/);if(!m)return;
t.textContent='';var a=document.createElement('span');a.className='v2s-eyebrow';a.textContent=m[1];t.appendChild(a);
t.appendChild(document.createTextNode(m[2]));
if(m[4]){var q=document.createElement('span');q.className='v2s-q';q.textContent='교과서 질문 · '+m[4];t.appendChild(q);}})();
