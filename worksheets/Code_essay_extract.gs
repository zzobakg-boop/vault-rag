/**
 * 서술형(essay-N) 추출기 — 학생별로 펼쳐서 정렬 (세특용)
 * ────────────────────────────────────────────────────────────
 * 학습지 제출은 `답(JSON)` 한 칸에 빈칸·OX·act·essay가 다 섞여 들어온다.
 * 이 스크립트는 그중 essay-N(긴 서술/더생각 답)만 뽑아
 *   [학습지 · 반 · 번호 · 이름 · essay-1 · essay-2 …] 표로 만들어
 *   '📝 서술형(세특)' 탭에 반·번호 순으로 정렬해 출력한다.
 *
 * 설치: doPost 있는 Apps Script 프로젝트에 이 코드를 추가 저장
 *       → 시트 새로고침 → 상단 메뉴 [📋 세특 도구] → [서술형(essay) 추출]
 * (재제출이 쌓여도 학습지·반·번호별 *가장 최근 1건*만 보여줌)
 */

function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('📋 세특 도구')
    .addItem('서술형(essay) 추출', 'extractEssays')
    .addToUi();
}

function extractEssays() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const ui = SpreadsheetApp.getUi();
  const OUT = '📝 서술형(세특)';

  // 1) 제출 데이터가 든 탭만 (진행/출력탭 제외)
  const srcSheets = ss.getSheets().filter(sh => {
    const n = sh.getName();
    return n !== '진행' && n !== OUT;
  });

  const rows = [];
  let maxEssay = 0;

  srcSheets.forEach(sh => {
    const values = sh.getDataRange().getValues();
    if (values.length < 2) return;
    const header = values[0].map(h => String(h).replace(/\s/g, ''));
    const col = key => header.findIndex(h => h.indexOf(key) >= 0);

    const iTime = col('시각');
    const iWs   = col('학습지');
    const iCls  = col('반');
    const iNum  = col('번호');
    const iName = col('이름');
    const iJson = col('답');           // '답(JSON)'
    if (iJson < 0) return;             // 답 열 없으면 이 탭은 skip

    for (let r = 1; r < values.length; r++) {
      const raw = values[r][iJson];
      if (!raw) continue;
      let obj;
      try { obj = JSON.parse(raw); } catch (e) { continue; }

      const essays = {};
      let has = false;
      Object.keys(obj).forEach(k => {
        const m = k.match(/^essay-(\d+)$/);
        if (m) {
          const idx = parseInt(m[1], 10);
          essays[idx] = obj[k];
          if (idx > maxEssay) maxEssay = idx;
          if (String(obj[k] || '').trim()) has = true;
        }
      });
      if (!has) continue;             // 서술형이 전부 빈칸이면 제외

      rows.push({
        time: iTime >= 0 ? values[r][iTime] : '',
        ws:   iWs   >= 0 ? values[r][iWs]   : sh.getName(),
        cls:  iCls  >= 0 ? values[r][iCls]  : '',
        num:  iNum  >= 0 ? values[r][iNum]  : '',
        name: iName >= 0 ? values[r][iName] : '',
        essays: essays
      });
    }
  });

  if (rows.length === 0) { ui.alert('서술형(essay) 답안이 있는 제출이 없습니다.'); return; }

  // 2) 재제출 누적 → (학습지·반·번호)별 가장 최근 1건만
  const latest = {};
  rows.forEach(r => {
    const key = r.ws + '|' + r.cls + '|' + r.num;
    const t = (r.time instanceof Date) ? r.time.getTime() : new Date(r.time).getTime();
    r._t = isNaN(t) ? 0 : t;
    if (!latest[key] || r._t >= latest[key]._t) latest[key] = r;
  });
  const out = Object.keys(latest).map(k => latest[k]);

  // 3) 정렬 — 학습지 → 반(숫자) → 번호(숫자)
  const num = v => { const x = parseInt(String(v).replace(/\D/g, ''), 10); return isNaN(x) ? 9999 : x; };
  out.sort((a, b) =>
    String(a.ws).localeCompare(String(b.ws)) || num(a.cls) - num(b.cls) || num(a.num) - num(b.num)
  );

  // 4) 출력 탭 만들기/비우기
  let osh = ss.getSheetByName(OUT);
  if (osh) osh.clear(); else osh = ss.insertSheet(OUT, 0);

  const head = ['학습지', '반', '번호', '이름'];
  for (let i = 1; i <= maxEssay; i++) head.push('essay-' + i);
  const table = [head];
  out.forEach(r => {
    const row = [r.ws, r.cls, r.num, r.name];
    for (let i = 1; i <= maxEssay; i++) row.push(r.essays[i] || '');
    table.push(row);
  });
  osh.getRange(1, 1, table.length, head.length).setValues(table);

  // 5) 보기 좋게 — 헤더 고정·굵게, essay 열 넓게+줄바꿈
  osh.getRange(1, 1, 1, head.length).setFontWeight('bold').setBackground('#fff2cc');
  osh.setFrozenRows(1);
  osh.setColumnWidth(1, 200);                       // 학습지
  for (let c = 2; c <= 4; c++) osh.setColumnWidth(c, 56);  // 반·번호·이름
  for (let c = 5; c <= head.length; c++) osh.setColumnWidth(c, 360); // essay
  if (table.length > 1 && maxEssay > 0) {
    osh.getRange(2, 5, table.length - 1, maxEssay).setWrap(true).setVerticalAlignment('top');
  }
  osh.activate();
  ui.alert('완료 — ' + out.length + '명 추출 (탭: ' + OUT + ')');
}
