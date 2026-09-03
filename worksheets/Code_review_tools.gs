/**
 * 제출 열람 도구 (통합판) — Code_review_sheet.gs + Code_essay_extract.gs
 * ────────────────────────────────────────────────────────────
 * 통증(천대현 2026-09-03): "단답은 그렇다 치더라도 **서술형까지 옆으로 길게 들어오면
 *   확인하기가 힘들다.** 들어오는 대로 반·번호별로 한눈에 파악할 방법."
 *
 * 🔴 왜 통합했나 — 두 파일이 각각 onOpen() 을 정의하고 있었다.
 *   Apps Script 는 동명 함수가 여러 파일에 있으면 하나만 살아남으므로
 *   **메뉴 하나가 조용히 사라진다.** 도구가 있는데도 못 쓰던 이유다.
 *   (시스템 세션 1차 파일 확인 2026-09-03)
 *
 * 🔴 열 이름은 탭마다 다르다 — 상수로 박지 말 것
 *   doPost v4 가 만드는 탭 = 시각·학습지·반·번호·이름·빈칸·OX·총점·답(JSON)
 *   v4 이전 옛 탭        = 제출시각·반·번호·이름·빈칸 점수·OX 점수·총점
 *   → 한쪽 문구로 고정하면 다른 쪽이 깨진다. ALIAS 로 찾는다.
 *   (Code_notify_v1.gs 가 같은 문제를 이미 이렇게 풀었다 — 그 테이블을 가져왔다)
 *
 * 설치: 제출 수합 스프레드시트 → 확장 프로그램 → Apps Script
 *   → 이 파일 추가 → **Code_review_sheet.gs · Code_essay_extract.gs 는 삭제**
 *   → 저장 → 스프레드시트 새로고침 → 상단 [📋 제출 보기] 메뉴
 *
 * 메뉴 2종:
 *   ① 이 탭 → 정리 시트   — 학생 1명 = 세로 블록. 한 학생을 통째로 읽을 때
 *   ② 서술형만 모아 보기  — essay-N 만 반·번호 순. 한 문항을 학생끼리 비교할 때
 *   ※ ①과 ②는 정반대 용도다. 목적에 따라 고른다.
 */

// ── 열 이름 별칭 (notify_v1 에서 흡수·2026-09-03) ─────────────
var ALIAS_ = {
  '시각':     ['시각', '제출시각', '제출 시각', '타임스탬프', 'Timestamp'],
  '학습지':   ['학습지', '제목'],
  '반':       ['반', '학급'],
  '번호':     ['번호', '출석번호'],
  '이름':     ['이름', '성명'],
  '빈칸':     ['빈칸', '빈칸 점수', '빈칸점수'],
  'OX':       ['OX', 'OX 점수', 'OX점수'],
  '총점':     ['총점', '합계'],
  '답(JSON)': ['답(JSON)', '답', 'answers', 'JSON']
};
var META_KEYS_ = ['시각', '학습지', '반', '번호', '이름', '빈칸', 'OX', '총점', '답(JSON)'];

/** 별칭까지 훑어 열 번호를 찾는다. 못 찾으면 -1. */
function col_(head, key) {
  var cands = ALIAS_[key] || [key];
  for (var i = 0; i < cands.length; i++) {
    var at = head.indexOf(cands[i]);
    if (at >= 0) { return at; }
  }
  return -1;
}

/**
 * 헤더 행이 어디인가 — 보통 1행이지만 정렬을 한 번 돌리면 밀린다
 * (2026-08-30 실측: 11차시 탭은 마지막 줄이 헤더였다). 앞 5줄·끝 3줄을 본다.
 */
function headerRow_(values) {
  var probe = [], i, j;
  for (i = 0; i < Math.min(5, values.length); i++) { probe.push(i); }
  for (j = Math.max(0, values.length - 3); j < values.length; j++) {
    if (probe.indexOf(j) < 0) { probe.push(j); }
  }
  for (var k = 0; k < probe.length; k++) {
    var row = values[probe[k]].map(function (v) { return String(v).trim(); });
    if (col_(row, '시각') >= 0 && col_(row, '번호') >= 0) { return probe[k]; }
  }
  return -1;
}

/**
 * 교과서 전용 칸인가 (2026-08-31 학습지 구조 전환).
 * 공란의 뜻이 다르다 — 일반칸 = 못 했다/시간 없었다 · 교과서칸 = **교과서를 안 폈다**.
 * 교사가 취할 행동이 정반대라 화면에서도 갈라 놓는다(역사 세션 판단·2026-09-03).
 * ⚠️ startswith('교과서 ') 로 하면 "교과서 설명과 비교해 보자" 같은 일반 문장이 걸린다.
 */
var TEXTBOOK_RE_ = /^\s*(교과서\s*\d+\s*쪽에서\s*찾기\s*—|원문에서\s*확인\s*—)/;
function isTextbook_(label) { return TEXTBOOK_RE_.test(String(label || '')); }

/** 반·번호 숫자 정렬용 */
function n_(v) { var x = parseInt(String(v).replace(/\D/g, ''), 10); return isNaN(x) ? 9999 : x; }

// ── 메뉴 (단 하나의 onOpen) ─────────────────────────────────
function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('📋 제출 보기')
    .addItem('① 이 탭 → 정리 시트 (학생별 세로)', 'buildReviewSheet')
    .addItem('② 서술형만 모아 보기 (문항별 비교)', 'extractEssays')
    .addToUi();
}

// ── ① 학생 1명 = 세로 블록 ──────────────────────────────────
function buildReviewSheet() {
  var ui = SpreadsheetApp.getUi();
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var src = ss.getActiveSheet();
  var srcName = src.getName();
  if (srcName.indexOf('📋 정리') === 0 || srcName.indexOf('📝 서술형') === 0) {
    ui.alert('제출 탭(원본)을 선택한 뒤 다시 실행하세요. 지금은 출력 시트입니다.');
    return;
  }

  var values = src.getDataRange().getValues();
  if (values.length < 2) { ui.alert('이 탭에 제출 데이터가 없습니다.'); return; }

  var hr = headerRow_(values);
  if (hr < 0) {
    ui.alert('이 탭에서 헤더를 찾지 못했습니다.\n\n제출 탭이 맞다면 1행에\n'
           + '시각 · 학습지 · 반 · 번호 · 이름 · 빈칸 · OX · 총점 · 답(JSON)\n'
           + '이 있어야 합니다. (헤더 없이 쌓인 탭이면 조용히 잘못 읽느니 멈춥니다)');
    return;
  }
  var head = values[hr].map(function (v) { return String(v).trim(); });
  var ix = {};
  META_KEYS_.forEach(function (k) { ix[k] = col_(head, k); });

  // 답 칸 = 메타로 잡히지 않은 나머지 컬럼(act-N 동적 컬럼 등)
  var metaIdx = META_KEYS_.map(function (k) { return ix[k]; });
  var answerCols = [];
  head.forEach(function (h, i) {
    if (h !== '' && metaIdx.indexOf(i) === -1) { answerCols.push({ name: h, i: i }); }
  });

  // 학생별 최신 제출만
  var byStudent = {};
  for (var r = 0; r < values.length; r++) {
    if (r === hr) { continue; }
    var row = values[r];
    var cls = ix['반'] >= 0 ? row[ix['반']] : '';
    var num = ix['번호'] >= 0 ? row[ix['번호']] : '';
    if (cls === '' && num === '') { continue; }
    var key = cls + '-' + num;
    var ts = ix['시각'] >= 0 ? new Date(row[ix['시각']]).getTime() : r;
    if (isNaN(ts)) { ts = r; }
    if (!byStudent[key] || ts >= byStudent[key]._ts) { row._ts = ts; byStudent[key] = row; }
  }
  var keys = Object.keys(byStudent).sort(function (a, b) {
    var pa = a.split('-'), pb = b.split('-');
    return n_(pa[0]) - n_(pb[0]) || n_(pa[1]) - n_(pb[1]);
  });
  if (!keys.length) { ui.alert('정리할 제출이 없습니다.'); return; }

  var outName = '📋 정리·' + srcName;
  var out = ss.getSheetByName(outName);
  if (out) { out.clear(); } else { out = ss.insertSheet(outName); }

  var block = [], hdrRows = [], tbRows = [], blankRows = [];
  keys.forEach(function (key) {
    var row = byStudent[key];
    var name  = ix['이름'] >= 0 ? row[ix['이름']] : '';
    var score = ix['총점'] >= 0 ? row[ix['총점']] : '';
    var blank = ix['빈칸'] >= 0 ? row[ix['빈칸']] : '';
    var ox    = ix['OX']   >= 0 ? row[ix['OX']]   : '';
    block.push(['▎' + key + '  ' + name, '총점 ' + score + '  (빈칸 ' + blank + ' · OX ' + ox + ')']);
    hdrRows.push(block.length);

    var ans = {};
    if (ix['답(JSON)'] >= 0 && row[ix['답(JSON)']]) {
      try { ans = JSON.parse(row[ix['답(JSON)']]); } catch (e) { ans = {}; }
    }
    var labels = ans['__labels'] || {};
    var ansKeys = Object.keys(ans).filter(function (k) { return k !== '__labels'; });

    // 📕 교과서 칸은 뒤로 몰아 별도 소구획 (일반 활동칸과 섞지 않는다)
    var normal = [], textbook = [];
    if (ansKeys.length) {
      ansKeys.forEach(function (k) {
        var v = ans[k];
        var label = labels[k] || k;
        var pair = [label, (v === '' || v == null) ? '(비어 있음)' : String(v)];
        if (isTextbook_(label)) { textbook.push(pair); } else if (v !== '' && v != null) { normal.push(pair); }
      });
    } else {
      answerCols.forEach(function (c) {
        var v = row[c.i];
        if (v === '' || v == null) { return; }
        normal.push([c.name, String(v)]);
      });
    }
    normal.forEach(function (p) { block.push(p); });
    if (textbook.length) {
      block.push(['📕 교과서에서 찾은 칸', '(비어 있으면 교과서를 안 편 것)']);
      tbRows.push(block.length);
      textbook.forEach(function (p) { block.push(p); });
    }
    block.push(['', '']);
    blankRows.push(block.length);
  });

  var rng = out.getRange(1, 1, block.length, 2);
  rng.setValues(block);
  out.setColumnWidth(1, 230);
  out.setColumnWidth(2, 560);
  out.getRange(1, 1, block.length, 2).setWrapStrategy(SpreadsheetApp.WrapStrategy.WRAP)
     .setVerticalAlignment('top');
  hdrRows.forEach(function (rn) {
    out.getRange(rn, 1, 1, 2).setFontWeight('bold').setBackground('#e8f0fe');
  });
  tbRows.forEach(function (rn) {
    out.getRange(rn, 1, 1, 2).setFontWeight('bold').setBackground('#fdf3e3');
  });
  out.autoResizeRows(1, block.length);
  out.activate();
  ui.alert('완료 — "' + outName + '" (' + keys.length + '명·최신 제출 기준)');
}

// ── ② 서술형만 모아 보기 ────────────────────────────────────
function extractEssays() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var ui = SpreadsheetApp.getUi();
  var OUT = '📝 서술형(세특)';

  var srcSheets = ss.getSheets().filter(function (sh) {
    var n = sh.getName();
    return n !== '진행' && n !== '명렬' && n !== OUT && n.indexOf('📋 정리') !== 0;
  });

  var rows = [], maxEssay = 0;
  srcSheets.forEach(function (sh) {
    var values = sh.getDataRange().getValues();
    if (values.length < 2) { return; }
    var hr = headerRow_(values);
    if (hr < 0) { return; }                       // 헤더 없는 탭은 조용히 skip
    var head = values[hr].map(function (v) { return String(v).trim(); });
    var iTime = col_(head, '시각'),  iWs  = col_(head, '학습지');
    var iCls  = col_(head, '반'),    iNum = col_(head, '번호');
    var iName = col_(head, '이름'),  iJson = col_(head, '답(JSON)');
    if (iJson < 0) { return; }

    for (var r = 0; r < values.length; r++) {
      if (r === hr) { continue; }
      var raw = values[r][iJson];
      if (!raw) { continue; }
      var obj;
      try { obj = JSON.parse(raw); } catch (e) { continue; }

      var essays = {}, has = false;
      Object.keys(obj).forEach(function (k) {
        var m = k.match(/^essay-(\d+)$/);
        if (m) {
          var i = parseInt(m[1], 10);
          essays[i] = obj[k];
          if (i > maxEssay) { maxEssay = i; }
          if (String(obj[k] || '').trim()) { has = true; }
        }
      });
      if (!has) { continue; }                     // 서술형이 전부 빈칸이면 제외

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
  if (!rows.length) { ui.alert('서술형(essay) 답안이 있는 제출이 없습니다.'); return; }

  var latest = {};
  rows.forEach(function (r) {
    var key = r.ws + '|' + r.cls + '|' + r.num;
    var t = (r.time instanceof Date) ? r.time.getTime() : new Date(r.time).getTime();
    r._t = isNaN(t) ? 0 : t;
    if (!latest[key] || r._t >= latest[key]._t) { latest[key] = r; }
  });
  var out = Object.keys(latest).map(function (k) { return latest[k]; });
  out.sort(function (a, b) {
    return String(a.ws).localeCompare(String(b.ws)) || n_(a.cls) - n_(b.cls) || n_(a.num) - n_(b.num);
  });

  var osh = ss.getSheetByName(OUT);
  if (osh) { osh.clear(); } else { osh = ss.insertSheet(OUT, 0); }

  var head2 = ['학습지', '반', '번호', '이름'];
  for (var i = 1; i <= maxEssay; i++) { head2.push('essay-' + i); }
  var table = [head2];
  out.forEach(function (r) {
    var row = [r.ws, r.cls, r.num, r.name];
    for (var j = 1; j <= maxEssay; j++) { row.push(r.essays[j] || ''); }
    table.push(row);
  });
  osh.getRange(1, 1, table.length, head2.length).setValues(table);
  osh.getRange(1, 1, 1, head2.length).setFontWeight('bold').setBackground('#fff2cc');
  osh.setFrozenRows(1);
  osh.setFrozenColumns(4);                        // 반·번호·이름 고정 — 가로 스크롤해도 누구인지 보인다
  osh.setColumnWidth(1, 200);
  for (var c = 2; c <= 4; c++) { osh.setColumnWidth(c, 56); }
  for (var c2 = 5; c2 <= head2.length; c2++) { osh.setColumnWidth(c2, 360); }
  if (table.length > 1 && maxEssay > 0) {
    osh.getRange(2, 5, table.length - 1, maxEssay).setWrap(true).setVerticalAlignment('top');
  }
  osh.activate();
  ui.alert('완료 — ' + out.length + '명 추출 (탭: ' + OUT + ')');
}
