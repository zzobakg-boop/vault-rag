// 도시 둘러보기 — 고르기 카드·그림에 «🌐 둘러보기» 단추를 붙이고, 누르면 학습지 안 창에서 360° 사진을 돌려 본다.
// 360° 사진은 학습지와 함께 올린 파일(images/pano/)이라 학교망에서도 열린다. 거리뷰·로드뷰는 새 창 바로가기만(막힐 수 있다).
// 카드 분류 답(무엇으로 이름났나)을 창에 쓰지 않는다 — 장소 이름과 보이는 것만 적는다.
// 자료: <script type="application/json" id="tv-data"> — [{card:"카드 이름", nth?:같은 이름 몇 번째, …} | {fig:"그림 파일 이름(확장자 빼고)", …}]
const items = JSON.parse(document.getElementById('tv-data').textContent);
const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

let box = null, view = null, back = null;
function ensureBox() {
  if (box) return box;
  box = document.createElement('div'); box.className = 'tv'; box.hidden = true;
  box.setAttribute('role', 'dialog'); box.setAttribute('aria-modal', 'true'); box.setAttribute('aria-labelledby', 'tv-h');
  box.innerHTML = `<div class="tv-box"><div class="tv-head"><h3 id="tv-h"></h3><button type="button" class="tv-x" aria-label="닫기">✕</button></div>
    <div class="tv-stage"><p class="tv-load">360° 사진을 불러오는 중…</p><p class="tv-hint">끌어서 둘러보기</p>
      <div class="tv-z"><button type="button" data-z=".85" aria-label="가까이">＋</button><button type="button" data-z="1.18" aria-label="멀리">－</button></div></div>
    <p class="tv-cap"></p><div class="tv-links"></div><p class="tv-note"></p></div>`;
  document.body.appendChild(box);
  box.querySelector('.tv-x').addEventListener('click', close);
  box.addEventListener('click', e => { if (e.target === box) close(); });
  box.querySelectorAll('.tv-z button').forEach(b => b.addEventListener('click', () => view && view.zoom(+b.dataset.z)));
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && !box.hidden) close(); });
  return box;
}
async function open(item, from) {
  ensureBox(); back = from;
  box.querySelector('#tv-h').innerHTML = `${esc(item.place)}<small>${esc(item.sub || '')}</small>`;
  box.classList.toggle('tv-nopano', !item.pano);
  const stage = box.querySelector('.tv-stage'); stage.classList.remove('pn-ready', 'pn-err');
  box.querySelector('.tv-cap').innerHTML = item.pano ? `${esc(item.pano.cap)} <small>· ${esc(item.pano.credit)}</small>` : '';
  box.querySelector('.tv-links').innerHTML = (item.links || []).map(l =>
    `<a href="${esc(l.url)}" target="_blank" rel="noopener">${esc(l.label)} ↗<small>${esc(l.see)}</small></a>`).join('');
  box.querySelector('.tv-note').textContent = (item.links || []).length ? '↗ 바깥 사이트는 새 창으로 열린다. 학교 인터넷에서는 막힐 수 있다.' : '';
  box.hidden = false; document.documentElement.classList.add('tv-lock');
  box.querySelector('.tv-x').focus();
  if (item.pano) {
    try {
      const { openPano } = await import('./pano.js');
      view = openPano(stage, { src: new URL('images/pano/' + item.pano.file, document.baseURI).href, u: item.pano.u });
      if (!view) stage.classList.add('pn-err');
    } catch (e) { stage.classList.add('pn-err'); }
  }
}
function close() {
  if (view) { view.close(); view = null; }
  box.hidden = true; document.documentElement.classList.remove('tv-lock');
  if (back) back.focus();
}
function spot(item) {
  if (item.fig) {   // 그림: 파일 이름이 같으면 확장자(.png·.webp·.jpg)는 따지지 않는다
    const img = [...document.querySelectorAll('figure img')].find(i => (i.getAttribute('src') || '').split('/').pop().replace(/\.[a-z]+$/i, '') === item.fig);
    return img && img.closest('figure');
  }
  const cards = [...document.querySelectorAll('.pk-card')].filter(c => (c.querySelector('.pk-name') || {}).textContent === item.card);
  const card = cards[(item.nth || 1) - 1];
  return card && card.querySelector('.pk-sit');
}
for (const item of items) {
  const sit = spot(item);
  if (!sit) { console.warn('[둘러보기] 자리를 못 찾음', item.card || item.fig); continue; }
  const b = document.createElement('button'); b.type = 'button'; b.className = 'tv-open';
  b.innerHTML = `🌐 둘러보기 <span class="tv-kind">${item.pano ? '360° 사진' : '거리뷰'}</span>`;
  b.addEventListener('click', e => { e.stopPropagation(); open(item, b); });
  sit.after(b);
}
