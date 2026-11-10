// 홀로그램 도시 — 단추·정보 창·그래프. 3D(holo.js)는 «켜기»를 누를 때만 불러온다(학교 노트북·폰 배려).
const esc = (s) => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const SVGNS = 'http://www.w3.org/2000/svg';

function fig(p) { return `<figure><img src="${esc(p.src)}" alt="${esc(p.cap)}" loading="lazy"><figcaption>${esc(p.cap)}${p.credit ? ` · ${esc(p.credit)}` : ''}</figcaption></figure>`; }

// 단면 그래프: 지가(선·면)와 그 자리의 건물 높이(막대). 거리 축은 도심에서 바깥으로.
function profileSVG(prof, opt = {}) {
  const W = 340, H = 190, l = 30, r = 8, t = 14, b = 34, iw = W - l - r, ih = H - t - b;
  const maxL = 1.08, maxH = 10;
  const X = (d) => l + d / 12.5 * iw, YL = (v) => t + ih - v / maxL * ih, YH = (v) => t + ih - v / maxH * ih;
  const bands = [[0, 3.7, '도심', '#6fe7ff'], [5.1, 8.1, '부도심', '#b5a3ff'], [9.3, 11.6, '개발 제한', '#6fe39c']];
  let s = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(opt.label || '도심에서 바깥으로 가며 본 지가와 건물 높이')}">`;
  for (const [a, z, n, c] of bands) s += `<rect x="${X(a)}" y="${t}" width="${X(z) - X(a)}" height="${ih}" fill="${c}" opacity=".08"/><text x="${(X(a) + X(z)) / 2}" y="${H - 6}" fill="${c}" font-size="10" text-anchor="middle" font-weight="700">${n}</text>`;
  s += `<text x="${(X(3.7) + X(5.1)) / 2}" y="${H - 6}" fill="#ffd27a" font-size="9" text-anchor="middle">주거</text><text x="${(X(8.1) + X(9.3)) / 2}" y="${H - 6}" fill="#ffd27a" font-size="9" text-anchor="middle">주거</text>`;
  for (let i = 0; i <= 4; i++) { const y = t + ih * i / 4; s += `<line x1="${l}" x2="${W - r}" y1="${y}" y2="${y}" stroke="#8fd9ef" stroke-opacity=".12"/>`; }
  for (const p of prof) { if (p.h <= 0) continue; const x = X(p.r); s += `<rect x="${x - 2.2}" y="${YH(p.h)}" width="4.4" height="${t + ih - YH(p.h)}" fill="#b9f6ff" opacity=".35"/>`; }
  let d = '', a = `M${X(0)} ${t + ih}`;
  prof.forEach((p, i) => { const pt = `${X(p.r).toFixed(1)} ${YL(p.L).toFixed(1)}`; d += (i ? 'L' : 'M') + pt; a += 'L' + pt; });
  a += `L${X(12.5)} ${t + ih}Z`;
  s += `<path d="${a}" fill="url(#hgG)" opacity=".55"/><path d="${d}" fill="none" stroke="#fff4b8" stroke-width="2.2"/>`;
  s += `<defs><linearGradient id="hgG" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff4b8" stop-opacity=".7"/><stop offset="1" stop-color="#1fa6d6" stop-opacity="0"/></linearGradient></defs>`;
  s += `<line x1="${l}" x2="${W - r}" y1="${t + ih}" y2="${t + ih}" stroke="#8fd9ef" stroke-opacity=".5"/>`;
  s += `<text x="${l}" y="${t - 3}" fill="#fff4b8" font-size="10" font-weight="700">― 지가</text><text x="${l + 50}" y="${t - 3}" fill="#b9f6ff" font-size="10" font-weight="700">▮ 가장 높은 건물</text>`;
  s += `<text x="${W - r}" y="${t + ih + 12}" fill="#86b3c4" font-size="9" text-anchor="end">도심에서 멀어짐 →</text></svg>`;
  return s;
}

// 막대 그래프(가로). rows: [{name, v, color?}]
function barsSVG(rows, opt) {
  const W = 340, rowH = 24, l = opt.left || 92, r = 46, H = rows.length * rowH + 8, max = opt.max || Math.max(...rows.map(x => x.v));
  let s = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(opt.label)}">`;
  rows.forEach((x, i) => {
    const y = 4 + i * rowH, w = (W - l - r) * x.v / max;
    s += `<text x="${l - 6}" y="${y + 15}" fill="#cbeefb" font-size="11" text-anchor="end">${esc(x.name)}</text>`;
    s += `<rect x="${l}" y="${y + 4}" width="${Math.max(w, 1)}" height="14" rx="3" fill="${x.color || '#6fe7ff'}" opacity=".85"/>`;
    s += `<text x="${l + w + 5}" y="${y + 15}" fill="#eaffff" font-size="11" font-weight="700">${esc(x.label || x.v)}</text>`;
  });
  return s + '</svg>';
}

// 흩어진 점(서울 구별 거리–지가)
function scatterSVG(pts, opt) {
  const W = 340, H = 210, l = 40, r = 10, t = 12, b = 30, iw = W - l - r, ih = H - t - b;
  const mx = opt.maxX, my = opt.maxY, X = v => l + v / mx * iw, Y = v => t + ih - v / my * ih;
  let s = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(opt.label)}">`;
  for (let i = 0; i <= 4; i++) { const y = t + ih * i / 4; s += `<line x1="${l}" x2="${W - r}" y1="${y}" y2="${y}" stroke="#8fd9ef" stroke-opacity=".12"/><text x="${l - 4}" y="${y + 3}" fill="#86b3c4" font-size="9" text-anchor="end">${Math.round(my * (1 - i / 4)).toLocaleString()}</text>`; }
  for (let i = 0; i <= mx; i += opt.stepX || 5) s += `<text x="${X(i)}" y="${H - 14}" fill="#86b3c4" font-size="9" text-anchor="middle">${i}</text>`;
  s += `<text x="${W - r}" y="${H - 2}" fill="#86b3c4" font-size="9" text-anchor="end">${esc(opt.xLabel)}</text><text x="${l}" y="${t - 2}" fill="#86b3c4" font-size="9">${esc(opt.yLabel)}</text>`;
  for (const p of pts) { const c = p.hl || '#6fe7ff'; s += `<circle cx="${X(p.x)}" cy="${Y(p.y)}" r="${p.hl ? 4.5 : 3.2}" fill="${c}" opacity="${p.hl ? 1 : .65}"/>`; if (p.tag) s += `<text x="${X(p.x) + 6}" y="${Y(p.y) + 3}" fill="${c}" font-size="10" font-weight="700">${esc(p.tag)}</text>`; }
  return s + '</svg>';
}

// 실제 단면(1km 구간마다 가운데 값). rows: [[시작km, 끝km, 원/㎡]]
function binsSVG(rows, opt) {
  const W = 340, H = 214, l = 44, r = 10, t = 34, b = 30, iw = W - l - r, ih = H - t - b;
  const maxX = rows[rows.length - 1][1], maxY = Math.max(...rows.map(x => x[2]));
  const X = v => l + v / maxX * iw, Y = v => t + ih - v / maxY * ih, man = v => Math.round(v / 10000).toLocaleString() + '만';
  let s = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(opt.label)}">`;
  [0, .25, .5, .75, 1].forEach(f => { const y = t + ih * (1 - f); s += `<line x1="${l}" x2="${W - r}" y1="${y}" y2="${y}" stroke="#8fd9ef" stroke-opacity=".12"/><text x="${l - 4}" y="${y + 3}" fill="#86b3c4" font-size="9" text-anchor="end">${man(maxY * f)}</text>`; });
  const minI = rows.reduce((m, x, i) => x[2] < rows[m][2] ? i : m, 0);
  const bumpI = rows.reduce((m, x, i) => i > minI && x[2] > (m < 0 ? 0 : rows[m][2]) ? i : m, -1);
  rows.forEach(([a, z, v], i) => {
    const hl = i === 0 ? '#6fe7ff' : i === bumpI ? '#b5a3ff' : '#ffd27a';
    s += `<rect x="${X(a) + 1}" y="${Y(v)}" width="${Math.max(X(z) - X(a) - 2, 1)}" height="${t + ih - Y(v)}" rx="2" fill="${hl}" opacity=".85"/>`;
    if (i === 0 || i === minI || i === bumpI) s += `<text x="${(X(a) + X(z)) / 2}" y="${Y(v) - 4}" fill="${hl}" font-size="10" font-weight="700" text-anchor="middle">${man(v)}</text>`;
  });
  for (let k = 0; k <= maxX - 1; k += 2) s += `<text x="${X(k)}" y="${H - 16}" fill="#86b3c4" font-size="9" text-anchor="middle">${k}</text>`;
  s += `<text x="${X(0)}" y="${H - 4}" fill="#6fe7ff" font-size="10" font-weight="700">명동</text>`;
  if (bumpI > 0) s += `<text x="${(X(rows[bumpI][0]) + X(rows[bumpI][1])) / 2}" y="${H - 4}" fill="#b5a3ff" font-size="10" font-weight="700" text-anchor="middle">노원역 근처</text>`;
  s += `<text x="${W - r}" y="${H - 16}" fill="#86b3c4" font-size="9" text-anchor="end">km</text><text x="${l - 38}" y="10" fill="#86b3c4" font-size="9">원/㎡ · 1km마다 가운데 값</text></svg>`;
  return s;
}

function chartBlock(c, api, t) {
  if (!c) return '';
  let svg = '';
  if (c.type === 'profile') { if (!api) return ''; svg = profileSVG(api.profile(t), { label: c.title }); }   // 단면은 3D 모형에서 재므로 대체 화면에선 뺀다
  else if (c.type === 'bars') svg = barsSVG(c.rows, { label: c.title, max: c.max, left: c.left });
  else if (c.type === 'scatter') svg = scatterSVG(c.pts, c);
  else if (c.type === 'bins') svg = binsSVG(c.rows, { label: c.title });
  return `<div class="hg-chart" data-kind="${c.type}"><div class="hg-ct">${esc(c.title)}</div>${svg}${c.src ? `<div class="hg-src">${esc(c.src)}</div>` : ''}</div>`;
}

export function initHolo(root) {
  const data = JSON.parse(root.querySelector('script.hg-data').textContent);
  const panel = root.querySelector('.hg-panel');
  const btnStart = root.querySelector('.hg-start');
  const modeBtns = [...root.querySelectorAll('.hg-modes button')];
  const range = root.querySelector('.hg-ctl input');
  const out = root.querySelector('.hg-ctl output');
  let api = null, openId = null;

  function render(id) {
    openId = id;
    const z = (data.zones || []).find(x => x.id === id) || (data.views || {})[id];
    if (!z) return;
    const t = api && root.dataset.mode === 'change' ? +range.value / 100 : 1;
    let h = `<button class="hg-close" type="button" aria-label="닫기">✕</button>`;
    h += `<h4 style="--pc:${z.color || '#bff3ff'};color:${z.color || '#bff3ff'}">${esc(z.name)}</h4>`;
    if (z.kick) h += `<p class="hg-kick">${esc(z.kick)}</p>`;
    if (z.ask) h += `<div class="hg-ask">💬 ${esc(z.ask)}</div>`;
    (z.lines || []).forEach(x => h += `<p>${esc(x)}</p>`);
    (z.charts || []).forEach(c => h += chartBlock(c, api, t));
    if (z.pair) h += `<div class="hg-pair">${z.pair.map(fig).join('')}</div>`;
    (z.photos || []).forEach(p => h += fig(p));
    panel.innerHTML = h; panel.classList.add('open'); panel.scrollTop = 0; shiftFor(true);
    if (root.clientWidth <= 760) panel.scrollIntoView({ block: 'nearest', behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
    panel.style.setProperty('--pc', z.color || '#bff3ff');
    panel.querySelector('.hg-close').addEventListener('click', close);
    root.querySelectorAll('.hg-pin').forEach(b => b.setAttribute('aria-expanded', String(b.textContent.endsWith(z.name))));
  }
  function shiftFor(open) { if (api) api.setShift(open && root.clientWidth > 760 ? panel.offsetWidth / 2 + 6 : 0); }
  function close() { panel.classList.remove('open'); openId = null; shiftFor(false); root.querySelectorAll('.hg-pin').forEach(b => b.setAttribute('aria-expanded', 'false')); }

  function setMode(m) {
    modeBtns.forEach(b => b.setAttribute('aria-pressed', String(b.dataset.mode === m)));
    root.dataset.mode = m;
    if (api) api.setMode(m);
    if (m === 'price') { if (api) api.stopSpin(); render('price'); }
    else if (m === 'change') { if (api) api.stopSpin(); range.value = 0; onRange(); render('change'); }
    else close();
  }
  function onRange() {
    const v = +range.value / 100; if (api) api.setT(v);
    out.textContent = v < .05 ? '지하철이 놓이기 전' : v < .95 ? '역이 생기고 사람이 몰린다' : '부도심이 되었다';
    if (openId === 'change') { const box = panel.querySelector('.hg-chart[data-kind="profile"]'); if (box && api) box.querySelector('svg').outerHTML = profileSVG(api.profile(v)); }
  }

  modeBtns.forEach(b => b.addEventListener('click', () => setMode(b.dataset.mode)));
  range.addEventListener('input', onRange);
  root.addEventListener('hg-zone', e => { if (root.dataset.mode !== 'scape') setMode('scape'); render(e.detail); });
  root.querySelector('.hg-zin').addEventListener('click', () => api && api.zoom(.82));
  root.querySelector('.hg-zout').addEventListener('click', () => api && api.zoom(1.22));

  btnStart.addEventListener('click', async () => {
    btnStart.disabled = true; btnStart.firstChild.textContent = '불러오는 중…';
    try {
      const { mountHolo } = await import('./holo.js');
      api = mountHolo(root, data);
      if (!api) throw new Error('webgl');
      root.querySelector('.hg-poster').remove(); root.classList.add('hg-on');
      root.querySelector('.hg-stage').classList.add('hg-live');
      setMode('scape');
    } catch (e) {
      fallback();
    }
  });
  root.addEventListener('hg-fail', fallback);
  function fallback() {
    // 3D를 못 그리는 기기: 정지 그림 + 핀 대신 지역 단추 (holo.js의 hg-fail과 import 실패가 겹쳐 두 번 불릴 수 있다)
    if (root.classList.contains('hg-fallback')) return;
    root.classList.add('hg-fallback');
    const poster = root.querySelector('.hg-poster');
    if (poster) poster.innerHTML = '<p class="hg-nogl">이 기기에서는 3D를 그릴 수 없어 그림으로 보여 준다. 아래 단추로 지역을 열어 보자.</p>';
    const bar = document.createElement('div'); bar.className = 'hg-top';
    (data.zones || []).forEach(z => { const b = document.createElement('button'); b.className = 'hg-pin'; b.style.position = 'static'; b.style.transform = 'none'; b.style.setProperty('--pc', z.color); b.textContent = z.name; b.addEventListener('click', () => render(z.id)); bar.appendChild(b); });
    root.querySelector('.hg-stage').after(bar);
  }
}

document.querySelectorAll('.hg').forEach(initHolo);
