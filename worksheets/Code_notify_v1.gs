/**
 * 학습지 제출 요약 알림 v1 (2026-08-28)
 *
 * 왜: 지금까지 제출은 시트에 조용히 쌓이기만 했다. 교사가 열어볼 때까지 아무 신호가 없어서
 *     8/21 헤더 유실·8/18 버전 갈림 같은 사고를 *다음 반이 이미 겪은 뒤에야* 알았다.
 *     수업 직후에 알면 그 자리에서 손을 쓸 수 있다.
 *
 * 무엇을 보내나 (⚠️ 학생 이름은 절대 보내지 않는다 — 번호만):
 *   ① 학습지별 제출 건수·반별 분포
 *   ② 서술칸(essay) 결손 인원 — 8/18 실측상 여기가 진짜 변별 지점
 *   ③ 🔴 이상 신호 — 헤더 깨짐·같은 반번호 중복·번호 범위 이탈
 *
 * 설치:
 *   1) 이 파일 내용을 Apps Script 프로젝트에 새 파일로 추가 (Code.gs는 건드리지 않는다)
 *   2) 프로젝트 설정 → 스크립트 속성에 추가:
 *        TG_BOT_TOKEN = <봇 토큰>      (~/.claude/channels/telegram/.env 의 TELEGRAM_BOT_TOKEN)
 *        TG_CHAT_ID   = 8025017394
 *   3) 트리거 → notifyRecent 를 시간 기반 · 30분마다 로 추가
 *   ※ 토큰을 코드에 직접 쓰지 않는다(스크립트 공유 시 노출).
 *
 * 동작: 30분마다 깨어나 *직전 40분* 제출분만 본다(경계 걸침 여유 10분).
 *      제출이 없으면 아무것도 보내지 않는다 → 수업 없는 시간엔 조용하다.
 *      같은 배치를 두 번 보내지 않도록 마지막 발송 시각을 속성에 남긴다.
 */

var VERSION = 'v2.1';     // ⭐ 모든 메시지 머리에 찍힌다 — 코드가 실제로 교체됐는지 눈으로 확인하는 유일한 수단
var WINDOW_MIN = 40;      // 되돌아볼 분
var NUM_MAX = 40;         // 정상 번호 상한 (이보다 크면 이상 신호)
var HDR = ['시각','학습지','반','번호','이름','빈칸','OX','총점','답(JSON)'];

/**
 * 열 이름 별칭 — 2026-08-30.
 * 왜: 실제 시트 헤더는 '제출시각 · 반 · 번호 · 이름 · 빈칸 점수 · OX 점수 · 총점' 이었는데
 *     코드는 '시각 · 학습지 · … · 답(JSON)' 을 기다렸다. 이름이 안 맞으니 모든 탭이 조용히
 *     건너뛰어졌고, 헤더가 아예 없는 탭 하나만 통과해 indexOf=-1 → undefined 값으로
 *     '8명이 전부 3반 1번' 이라는 허깨비 집계를 만들어 냈다.
 *     앞으로 헤더 문구가 조금 달라져도 버티도록 별칭으로 찾는다.
 * '학습지'·'답(JSON)' 은 이 시트에 없다 — 학습지는 탭 이름이, 답안은 별도 탭이 갖고 있다.
 */
var ALIAS = {
  '시각':   ['시각','제출시각','제출 시각','타임스탬프','Timestamp'],
  '학습지': ['학습지','제목'],
  '반':     ['반','학급'],
  '번호':   ['번호','출석번호'],
  '이름':   ['이름','성명'],
  '빈칸':   ['빈칸','빈칸 점수','빈칸점수'],
  'OX':     ['OX','OX 점수','OX점수'],
  '총점':   ['총점','합계'],
  '답(JSON)': ['답(JSON)','답','answers','JSON']
};

/** 별칭까지 훑어 열 번호를 찾는다. 못 찾으면 -1. */
function _col_(head, key) {
  var cands = ALIAS[key] || [key];
  for (var i = 0; i < cands.length; i++) {
    var at = head.indexOf(cands[i]);
    if (at >= 0) { return at; }
  }
  return -1;
}

/**
 * 헤더 행이 어디인가 — 보통 1행이지만, 정렬을 한 번 돌리면 데이터 사이나 맨 끝으로 밀린다
 * (8/30 11차시 탭 실측: 1행이 데이터, 마지막 줄이 헤더였다). 앞 5줄과 끝 3줄을 본다.
 */
function _headerRow_(vals) {
  var probe = [];
  for (var i = 0; i < Math.min(5, vals.length); i++) { probe.push(i); }
  for (var j = Math.max(0, vals.length - 3); j < vals.length; j++) {
    if (probe.indexOf(j) < 0) { probe.push(j); }
  }
  for (var k = 0; k < probe.length; k++) {
    var row = vals[probe[k]].map(function (v) { return String(v).trim(); });
    if (_col_(row, '시각') >= 0 && _col_(row, '번호') >= 0) { return probe[k]; }
  }
  return -1;
}

function _prop_(k) { return PropertiesService.getScriptProperties().getProperty(k); }

/**
 * 어느 스프레드시트를 읽을지 결정한다.
 * 스크립트 속성 SHEET_ID 가 있으면 그 파일을, 없으면 이 스크립트가 붙어 있는 파일을 쓴다.
 * 왜: 8/30 — 알림 코드를 *제출을 받지 않는 옛 사본* 프로젝트에 붙여 넣는 바람에
 *     명렬 탭을 몇 번을 만들어도 영원히 못 찾는 일이 있었다. SHEET_ID 를 박아 두면
 *     스크립트가 어디에 붙어 있든 항상 같은 파일을 본다.
 */
function _ss_() {
  var id = _prop_('SHEET_ID');
  if (id) {
    id = String(id).trim();
    var m = id.match(/\/d\/([a-zA-Z0-9-_]+)/);   // URL 을 통째로 넣어도 받아준다
    if (m) id = m[1];
    return SpreadsheetApp.openById(id);
  }
  return SpreadsheetApp.getActiveSpreadsheet();
}

function _tg_(text) {
  var tok = _prop_('TG_BOT_TOKEN'), chat = _prop_('TG_CHAT_ID');
  if (!tok || !chat) { Logger.log('TG_BOT_TOKEN/TG_CHAT_ID 미설정'); return; }
  UrlFetchApp.fetch('https://api.telegram.org/bot' + tok + '/sendMessage', {
    method: 'post',
    payload: { chat_id: chat, text: text, disable_web_page_preview: 'true' },
    muteHttpExceptions: true
  });
}

/** 시트 한 탭을 훑어 최근 제출 + 이상 신호를 뽑는다. */
/** 값이 '최근'으로 읽히는 날짜인가 (헤더 없는 탭이 제출 탭인지 판별할 때 씀) */
function _recentDate_(v, since) {
  var d = (v instanceof Date) ? v : new Date(v);
  return (d instanceof Date) && !isNaN(d.getTime()) && d >= since;
}

function _scanTab_(tab, since) {
  var vals = tab.getDataRange().getValues();
  var out = { name: tab.getName(), rows: [], issues: [] };
  if (vals.length === 0) { return out; }

  var hr = _headerRow_(vals);

  // ⚠️ 2026-08-29/30 오탐 수정 — 이 시트에는 제출 탭 말고도 교사가 손으로 만든
  //   정리 시트(「📋 정리·…」 등)가 섞여 있다. 헤더를 못 찾으면 기본은 *조용히 건너뛴다*.
  //   단 A열이 '최근 날짜'로 읽히면 그건 제출 탭인데 헤더만 날아간 것이므로 그때만 경보한다.
  //   🔴 헤더를 못 찾은 탭은 절대 집계하지 않는다 — 8/30 '전원 3반 1번' 허깨비의 원인.
  if (hr < 0) {
    for (var j = 0; j < vals.length; j++) {
      if (_recentDate_(vals[j][0], since)) {
        out.issues.push('헤더 없음 — 제출이 들어오는데 열이 어긋난 채로 쌓이는 중');
        break;
      }
    }
    return out;
  }

  var head = vals[hr].map(function (v) { return String(v).trim(); });
  var ix = {};
  HDR.forEach(function (h) { ix[h] = _col_(head, h); });

  var seen = {};
  for (var i = 0; i < vals.length; i++) {
    if (i === hr) { continue; }                    // 헤더 행은 건너뛴다 (1행이 아닐 수 있다)
    var r = vals[i];
    var ts = r[ix['시각']];
    var when = (ts instanceof Date) ? ts : new Date(ts);

    // ⚠️ 2026-08-29 버그 수정 — 예전엔 번호 검사가 이 시간 필터 *앞*에 있었다.
    //   그래서 7월 데이터까지 매번 딸려 와 30분마다 같은 과거 경보가 반복됐다.
    //   모든 검사는 반드시 창 안으로 들어온 뒤에 한다.
    if (!(when instanceof Date) || isNaN(when.getTime()) || when < since) { continue; }

    var cls = String(r[ix['반']]).trim();
    var num = String(r[ix['번호']]).trim();

    // 🔴 이상 신호 B — 번호 범위 이탈 (드롭다운 이전 제출분·오기·열 밀림)
    var n = parseInt(num, 10);
    if (num && (isNaN(n) || String(n) !== num || n < 1 || n > NUM_MAX)) {
      out.issues.push('번호 이상: ' + cls + '반 "' + num.slice(0, 30) + '"');
    }

    var key = cls + '-' + num;
    // 🔴 이상 신호 C — 같은 반번호가 이 배치에 두 번 (재제출이 아니라 오기 의심)
    if (seen[key]) { seen[key].dup = true; } else { seen[key] = { dup: false }; }

    // 답안 JSON 열이 없는 시트도 있다(답안은 별도 탭). 그땐 서술 결손을 세지 않는다.
    var essayBlank = false;
    if (ix['답(JSON)'] >= 0) {
    try {
      var ans = JSON.parse(r[ix['답(JSON)']] || '{}');
      for (var k in ans) {
        if (k.indexOf('essay') === 0 && String(ans[k]).trim()) { essayBlank = false; }
      }
      // essay 키가 아예 없으면 그 학습지에 서술칸이 없는 것 — 결손 아님
      var hasEssayKey = Object.keys(ans).some(function (k) { return k.indexOf('essay') === 0; });
      if (!hasEssayKey) { essayBlank = false; }
    } catch (e) {
      // 🔴 이상 신호 D — 답안 JSON이 깨졌다. 조용히 넘기면 그 학생 답이 통째로 사라진다.
      out.issues.push('답안 JSON 파손: ' + cls + '반 ' + num + '번');
      essayBlank = false;   // 결손 집계에서는 빼고 이상 신호로만 올린다
    }
    }

    out.rows.push({ cls: cls, num: num, key: key, essayBlank: essayBlank });
  }

  Object.keys(seen).forEach(function (k) {
    if (seen[k].dup) { out.issues.push('같은 반·번호 중복 제출: ' + k + '번'); }
  });

  // ⚠️ 2026-08-29 — 같은 문구가 5번씩 반복돼 알림이 읽히지 않았다.
  //   중복은 접어서 "×N"으로, 종류가 많으면 잘라 낸다. 읽히지 않는 경보는 없는 것과 같다.
  var cnt = {}, order = [];
  out.issues.forEach(function (m) {
    if (cnt[m] === undefined) { cnt[m] = 0; order.push(m); }
    cnt[m]++;
  });
  out.issues = order.slice(0, 5).map(function (m) {
    return cnt[m] > 1 ? (m + ' ×' + cnt[m]) : m;
  });
  if (order.length > 5) { out.issues.push('… 외 ' + (order.length - 5) + '종'); }
  return out;
}

/** VERBOSE=true 면 결과가 0건이어도 "0건이었다"고 알려 준다 (notifyTest 전용). */
var VERBOSE = false;

var ROSTER_TAB = '명렬';   // 학년 | 반 | 번호(1-25,27 형식) — 없으면 미제출 계산을 건너뛴다

/**
 * '명렬' 탭 → { map: {'3-1': {1:true,...}}, bad: ['3-1 …'] }
 *
 * ⚠️ 2026-08-30 — 구글 시트가 '1-27' 을 **날짜(1월 27일)로 자동 변환**한다.
 *   그러면 셀 값이 Date 객체가 되어 파싱이 실패하고, 그 반 명렬이 비어
 *   *전원이 ❓ 명렬에 없는 번호* 로 뜬다. 조용히 깨지면 안 되므로 못 읽은 줄을 따로 모아 알린다.
 *   근본 해결은 C열을 '일반 텍스트' 서식으로 두는 것.
 */
/**
 * 명렬 탭 찾기 — 이름이 *눈에는 같은데* 안 잡히는 경우가 실제로 있다.
 *   ① 한글 자소 분리(NFD): 맥에서 타이핑한 '명렬'이 ㅁ+ㅕ+ㅇ… 으로 저장되면
 *      NFC로 쓰인 코드의 '명렬'과 문자열 비교가 실패한다.
 *   ② 앞뒤 공백·전각 공백
 *   ③ '명렬표' 처럼 뒤에 글자가 붙은 경우
 * 정확 일치 → 정규화 일치 → 부분 일치 순으로 내려가며 찾는다.
 */
function _findRosterTab_() {
  var ss = _ss_();
  var exact = ss.getSheetByName(ROSTER_TAB);
  if (exact) { return exact; }

  var want = ROSTER_TAB.normalize ? ROSTER_TAB.normalize('NFC') : ROSTER_TAB;
  var sheets = ss.getSheets();
  var loose = null;
  for (var i = 0; i < sheets.length; i++) {
    var raw = sheets[i].getName();
    var norm = (raw.normalize ? raw.normalize('NFC') : raw).replace(/[\s　]/g, '');
    if (norm === want) { return sheets[i]; }        // NFD·공백만 다른 경우
    if (!loose && norm.indexOf(want) === 0) { loose = sheets[i]; }  // '명렬표' 등
  }
  return loose;
}

function _roster_() {
  var tab = _findRosterTab_();
  if (!tab) { return null; }
  var tabName = tab.getName();
  var vals = tab.getDataRange().getValues();
  var map = {}, bad = [];
  for (var i = 1; i < vals.length; i++) {          // 1행은 머리글
    var g = String(vals[i][0]).trim();
    var c = String(vals[i][1]).trim();
    var raw = vals[i][2];
    if (!g || !c || raw === '' || raw === null) { continue; }
    var label = g + '학년 ' + c + '반';

    // 날짜로 변환된 셀은 아예 신뢰하지 않는다 — 복구를 시도하면 틀린 명렬로 조용히 굴러간다
    if (raw instanceof Date) {
      bad.push(label + ' (날짜로 변환됨)');
      continue;
    }
    var spec = String(raw).trim();
    var set = {}, n1, n2, count = 0;
    spec.split(',').forEach(function (part) {
      part = part.trim();
      var m = part.match(/^(\d+)\s*[-~]\s*(\d+)$/);
      if (m) {
        n1 = parseInt(m[1], 10); n2 = parseInt(m[2], 10);
        for (var n = n1; n <= n2; n++) { set[n] = true; count++; }
      } else if (/^\d+$/.test(part)) {
        set[parseInt(part, 10)] = true; count++;
      }
    });
    if (count === 0) { bad.push(label + ' ("' + spec.slice(0, 20) + '" 를 못 읽음)'); continue; }
    map[g + '-' + c] = set;
  }
  return { map: map, bad: bad, tabName: tabName };
}

/** 학습지 제목에서 학년을 읽는다. 단서가 없으면 null → 미제출 계산을 건너뛴다(추측하지 않는다). */
function _gradeOf_(title) {
  if (title.indexOf('사회') >= 0) { return '3'; }
  if (title.indexOf('역사') >= 0) { return '2'; }
  return null;
}

function notifyRecent() {
  var now = new Date();
  var since = new Date(now.getTime() - WINDOW_MIN * 60 * 1000);
  var ss = _ss_();
  var blocks = [], anyIssue = false;
  var scanned = 0, totalRows = 0;   // 진단용
  var rosterInfo = _roster_();      // '명렬' 탭 없으면 null → 미제출 계산 건너뜀
  var roster = rosterInfo ? rosterInfo.map : null;
  var rosterBad = rosterInfo ? rosterInfo.bad : [];
  var rosterUsed = false;

  ss.getSheets().forEach(function (tab) {
    var nm = tab.getName();
    if (nm === '진행' || nm === ROSTER_TAB) { return; }   // 중간저장·명렬 탭은 제출 탭이 아니다
    scanned++;
    var s = _scanTab_(tab, since);
    totalRows += s.rows.length;
    if (s.rows.length === 0 && s.issues.length === 0) { return; }

    // 반별 번호 목록 (이름 없음)
    var byCls = {};
    var essayGap = 0;
    s.rows.forEach(function (r) {
      byCls[r.cls] = byCls[r.cls] || [];
      byCls[r.cls].push(parseInt(r.num, 10) || r.num);
      if (r.essayBlank) { essayGap++; }
    });

    var lines = ['📥 ' + nm];
    var grade = _gradeOf_(nm);
    Object.keys(byCls).sort().forEach(function (c) {
      var ns = byCls[c].sort(function (a, b) { return a - b; });
      lines.push('  ' + c + '반 ' + ns.length + '명 · ' + ns.join(',') + '번');

      // ⛔ 미제출 — *제출이 들어온 반만* 대조한다.
      //   아직 수업 안 한 반까지 미제출로 잡으면 알림이 쓰레기가 된다.
      if (roster && grade) {
        var set = roster[grade + '-' + c];
        if (set) {
          var got = {};
          ns.forEach(function (n) { got[n] = true; });
          var miss = [], unreg = [];
          Object.keys(set).forEach(function (n) { if (!got[n]) { miss.push(parseInt(n, 10)); } });
          ns.forEach(function (n) { if (!set[n]) { unreg.push(n); } });
          miss.sort(function (a, b) { return a - b; });
          if (miss.length) { lines.push('  ⛔ 미제출 ' + miss.length + '명 · ' + miss.join(',') + '번'); }
          // 명렬에 없는 번호 = 전입생이거나 오기. 둘 다 사람이 봐야 한다.
          if (unreg.length) { lines.push('  ❓ 명렬에 없는 번호 · ' + unreg.join(',') + '번'); }
          rosterUsed = true;
        }
      }
    });
    if (essayGap > 0) {
      lines.push('  ✍️ 서술칸 빈 사람 ' + essayGap + '명 / ' + s.rows.length);
    }
    s.issues.forEach(function (m) { lines.push('  🔴 ' + m); anyIssue = true; });
    blocks.push(lines.join('\n'));
  });

  var stamp = Utilities.formatDate(now, 'Asia/Seoul', 'MM/dd HH:mm');

  // ⚠️ 2026-08-29 — 예전엔 여기서 그냥 return 했다. 그래서 *제출이 없어서 조용한 것*과
  //   *코드가 죽어서 조용한 것*을 구분할 수 없었다. 정기 알림은 조용한 게 맞지만,
  //   손으로 누르는 테스트는 반드시 답을 줘야 한다. 침묵은 답이 아니다.
  // 🔴 명렬을 못 읽었으면 제출 유무와 무관하게 알린다 — 조용히 틀린 명단으로 굴러가면 안 된다
  if (rosterBad.length) {
    blocks.unshift('🔴 「명렬」 탭을 못 읽은 반이 있습니다\n  ' + rosterBad.join('\n  ')
      + '\n  → C열을 「서식 → 숫자 → 일반 텍스트」로 바꾸고 다시 붙여넣으세요.');
    anyIssue = true;
  }

  if (blocks.length === 0) {
    if (VERBOSE) {
      var diag = '✅ 알림 정상 작동 · ' + VERSION + '  (' + stamp + ')\n\n'
        + '탭 ' + scanned + '개를 훑었고, 최근 ' + Math.round(WINDOW_MIN / 60) + '시간 안에 들어온 제출은 '
        + totalRows + '건입니다.\n'
        + '이상 신호도 없습니다.\n\n';
      // 명렬 상태를 자세히 — 여기서 대부분의 설치 문제가 드러난다
      if (!rosterInfo) {
        var all = _ss_().getSheets();
        var hint = [];
        all.forEach(function (t) {
          var nmx = t.getName();
          var nx = nmx.normalize ? nmx.normalize('NFC') : nmx;   // NFD면 indexOf('명')이 실패한다
          if (nx.indexOf('명') >= 0 || nx.indexOf('렬') >= 0) {
            hint.push('「' + nmx + '」(' + nmx.length + '자)');
          }
        });
        var ssx = _ss_();
        diag += '🔴 「' + ROSTER_TAB + '」 탭을 찾지 못했습니다 — 미제출 계산은 하지 않습니다.\n\n'
          + '   ▸ 이 스크립트가 읽고 있는 파일:\n'
          + '     「' + ssx.getName() + '」\n'
          + '     ' + ssx.getUrl() + '\n'
          + '   ▸ 이 링크를 열어 보세요. 「명렬」을 만든 그 파일이 맞습니까?\n'
          + '     다르면 그 파일에 명렬 탭을 만들어야 합니다.\n\n'
          + '   전체 탭 ' + all.length + '개.\n'
          + (hint.length
              ? '   비슷한 이름: ' + hint.join(', ') + '\n   → 이 탭 이름을 지우고 「명렬」 두 글자만 다시 입력해 보세요.'
              : '   「명」이나 「렬」이 든 탭이 하나도 없습니다. 다른 스프레드시트에 만드신 건 아닌지 확인하세요.');
      } else {
        var ks = Object.keys(roster);
        diag += '읽는 파일: 「' + _ss_().getName() + '」\n'
          + '「' + rosterInfo.tabName + '」 탭: ' + ks.length + '개 반 인식';
        if (rosterInfo.tabName !== ROSTER_TAB) { diag += ' ⚠️이름이 「' + ROSTER_TAB + '」과 다르지만 찾아서 씀'; }
        if (ks.length) { diag += ' (' + ks.sort().join(', ') + ')'; }
        if (rosterBad.length) { diag += '\n🔴 못 읽은 줄: ' + rosterBad.join(' / '); }
      }
      _tg_(diag);
    }
    return;
  }

  var head = (anyIssue ? '🔴 학습지 제출 — 확인 필요' : '✅ 학습지 제출')
    + ' (' + stamp + ' 기준 ' + WINDOW_MIN + '분 · ' + VERSION + ')';
  var foot = '';
  if (rosterUsed) {
    foot = '\n\n※ 미제출은 「명렬」 탭 기준입니다. 명렬이 오래됐으면 전출자가 미제출로, 전입생이 ❓로 뜹니다.';
  } else if (!roster) {
    foot = '\n\n※ 「명렬」 탭이 없어 미제출은 계산하지 않았습니다.';
  }
  _tg_(head + '\n\n' + blocks.join('\n\n') + foot);
  PropertiesService.getScriptProperties().setProperty('LAST_NOTIFY', now.toISOString());
}

/** 설치 직후 손으로 눌러 확인하는 용도 — 창을 24시간으로 늘리고, 0건이어도 반드시 회신한다. */
function notifyTest() {
  var keepW = WINDOW_MIN, keepV = VERBOSE;
  WINDOW_MIN = 60 * 24;
  VERBOSE = true;
  try { notifyRecent(); } finally { WINDOW_MIN = keepW; VERBOSE = keepV; }
}

/**
 * 배선만 확인하는 최소 테스트 — 시트를 아예 안 읽고 텔레그램만 쏜다.
 * notifyTest도 조용하면 이걸 눌러 본다. 이것마저 안 오면 원인은 토큰/권한이지 코드가 아니다.
 */
function pingTelegram() {
  _tg_('🔔 배선 확인 — 이 메시지가 보이면 토큰·권한·전송 경로는 정상입니다.\n('
    + Utilities.formatDate(new Date(), 'Asia/Seoul', 'MM/dd HH:mm') + ')');
}

/**
 * 진단 — 열이 어떻게 생겼는지 눈으로 본다. (2026-08-30)
 * 왜: 8/30 '8명이 전부 3반 1번'으로 읽히는 일이 있었다. 열 밀림이 의심되지만
 *     추측으로 코드를 고치면 또 헛다리다. 헤더와 실제 값을 그대로 찍어서 대조한다.
 * ⚠️ 이름은 보내지 않는다 — 글자수만.
 */
function dumpColumns() {
  var ss = _ss_();
  var out = ['🔬 열 구조 진단 · ' + VERSION, '읽는 파일: 「' + ss.getName() + '」', ''];
  var sheets = ss.getSheets(), shown = 0;

  for (var i = sheets.length - 1; i >= 0 && shown < 2; i--) {
    var tab = sheets[i], nm = tab.getName();
    if (nm === '진행' || nm === ROSTER_TAB) { continue; }
    var vals = tab.getDataRange().getValues();
    if (vals.length < 2) { continue; }

    out.push('📄 ' + nm);
    var hr = _headerRow_(vals);
    out.push('  헤더 행: ' + (hr < 0 ? '못 찾음 🔴' : (hr + 1) + '행'));
    var hrow = hr < 0 ? vals[0] : vals[hr];
    out.push('  헤더: ' + hrow.map(function (v, k) {
      return '[' + k + ']' + String(v).trim();
    }).join(' '));

    var di = (hr === vals.length - 1) ? 0 : vals.length - 1;   // 헤더가 끝에 있으면 첫 줄을 본다
    var last = vals[di];
    out.push('  마지막 줄: ' + last.map(function (v, k) {
      var t = (v instanceof Date) ? 'Date(' + Utilities.formatDate(v, 'Asia/Seoul', 'MM/dd HH:mm') + ')'
            : String(v).slice(0, 14);
      if (String(hrow[k]).trim() === '이름') { t = '<' + String(v).length + '자>'; }
      return '[' + k + ']' + t;
    }).join(' '));

    var hnorm = hrow.map(function (v) { return String(v).trim(); });
    out.push('  코드가 찾은 열 번호: ' + HDR.map(function (h) {
      return h + '=' + _col_(hnorm, h);
    }).join(' · '));
    out.push('  ※ -1 = 못 찾음. 학습지·답(JSON) 은 이 시트에 없는 게 정상이다.');
    out.push('');
    shown++;
  }
  _tg_(out.join('\n'));
}

/**
 * 진단 — *최근 제출이 잡힌 탭*의 원본 줄을 그대로 찍는다. (2026-08-30)
 * 왜: dumpColumns 는 탭 목록 끝 2개만 봤다. 정작 이상한 값이 나온 탭(5-4차시)은
 *     목록 중간에 있어서 한 번도 못 봤고, 나는 그 사이 "허깨비 값"이라는 틀린 진단을 했다.
 *     추측을 끝내려면 *그 탭의 그 줄* 을 봐야 한다.
 * ⚠️ 이름은 글자수만 보낸다.
 */
function dumpFlagged() {
  var ss = _ss_();
  var since = new Date(new Date().getTime() - 1440 * 60 * 1000);
  var out = ['🔬 최근 제출 탭 원본 · ' + VERSION, '읽는 파일: 「' + ss.getName() + '」', ''];
  var shown = 0;

  ss.getSheets().forEach(function (tab) {
    if (shown >= 2) { return; }
    var nm = tab.getName();
    if (nm === '진행' || nm === ROSTER_TAB) { return; }
    var vals = tab.getDataRange().getValues();
    if (vals.length < 2) { return; }

    var hr = _headerRow_(vals);
    if (hr < 0) { return; }
    var head = vals[hr].map(function (v) { return String(v).trim(); });
    var tcol = _col_(head, '시각');

    var hits = [];
    for (var i = 0; i < vals.length && hits.length < 4; i++) {
      if (i === hr) { continue; }
      if (_recentDate_(vals[i][tcol], since)) { hits.push(i); }
    }
    if (hits.length === 0) { return; }

    out.push('📄 ' + nm);
    out.push('  헤더(' + (hr + 1) + '행): ' + head.map(function (v, k) {
      return '[' + k + ']' + v;
    }).join(' '));
    out.push('  찾은 열: 시각=' + tcol + ' 반=' + _col_(head, '반') + ' 번호=' + _col_(head, '번호')
             + ' 이름=' + _col_(head, '이름'));
    hits.forEach(function (i) {
      out.push('  ' + (i + 1) + '행: ' + vals[i].map(function (v, k) {
        var t = (v instanceof Date) ? Utilities.formatDate(v, 'Asia/Seoul', 'MM/dd HH:mm') : String(v).slice(0, 12);
        if (head[k] === '이름' || _col_(head, '이름') === k) { t = '<' + String(v).length + '자>'; }
        return '[' + k + ']' + t;
      }).join(' '));
    });
    out.push('  총 ' + vals.length + '행 · 최근 ' + hits.length + '행 표시');
    out.push('');
    shown++;
  });

  if (shown === 0) { out.push('최근 24시간 안에 제출이 잡힌 탭이 없습니다.'); }
  _tg_(out.join('\n'));
}

/**
 * 진단 — 특정 학습지 탭의 *전 행*을 반·번호 분포로 요약한다. (2026-08-31 · 사회 중3)
 *
 * 왜 또 만드나: dumpFlagged 는 자기가 고치려던 버그를 그대로 갖고 있다.
 *   ① shown>=2 로 탭을 2개만 본다 (dumpColumns 의 '끝 2개'와 성질이 같다)
 *   ② since = 최근 24시간. 5-4 수업이 며칠 전이면 "최근 제출 없음"만 찍고 끝난다.
 *      정작 증거인 과거 행을 못 본다.
 * 그래서 이 함수는 *탭을 지정*하고 *전 행*을 센다. 개별 행이 아니라 분포를 본다 —
 * '전부 3반 1번'이 사실인지, 사실이면 몇 행부터인지가 한 번에 나온다.
 *
 * 사용: dumpTabProfile('5-4')  · 인자 없으면 탭 목록만 찍는다.
 * ⚠️ 이름은 글자수만 내보낸다(기존 진단 규약 준수).
 */
function dumpTabProfile(needle) {
  var ss = _ss_();
  var names = ss.getSheets().map(function (t) { return t.getName(); });
  if (!needle) {
    _tg_('📑 탭 목록 (' + names.length + ')\n' + names.join('\n')
         + '\n\n사용: dumpTabProfile(\'5-4\')');
    return;
  }
  var tab = null;
  for (var i = 0; i < names.length; i++) {
    if (names[i].indexOf(needle) >= 0) { tab = ss.getSheets()[i]; break; }
  }
  if (!tab) {
    _tg_('❌ \'' + needle + '\' 를 담은 탭 없음.\n탭 목록:\n' + names.join('\n'));
    return;
  }

  var vals = tab.getDataRange().getValues();
  var hr = _headerRow_(vals);
  var out = ['🔬 탭 프로파일 · ' + VERSION, '📄 ' + tab.getName(), '총 ' + vals.length + '행'];
  if (hr < 0) {
    out.push('🔴 헤더 행을 못 찾음 — 헤더 유실 사고 계열일 수 있다.');
    out.push('1행 원본: ' + vals[0].slice(0, 12).map(String).join(' | ').slice(0, 300));
    _tg_(out.join('\n'));
    return;
  }
  var head = vals[hr].map(function (v) { return String(v).trim(); });
  out.push('헤더 ' + (hr + 1) + '행 · 열 ' + head.length + '개');
  var cT = _col_(head, '시각'), cC = _col_(head, '반'), cN = _col_(head, '번호'), cM = _col_(head, '이름');
  out.push('찾은 열: 시각=' + cT + ' 반=' + cC + ' 번호=' + cN + ' 이름=' + cM);
  if (cC < 0 || cN < 0) {
    out.push('🔴 반/번호 열을 못 찾음. 헤더 전체: ' + head.join(' | ').slice(0, 400));
    _tg_(out.join('\n'));
    return;
  }

  var byCls = {}, byPair = {}, blankName = 0, rows = 0, first = null, last = null;
  for (var r = 0; r < vals.length; r++) {
    if (r === hr) { continue; }
    var c = String(vals[r][cC]).trim(), n = String(vals[r][cN]).trim();
    if (!c && !n) { continue; }
    rows++;
    byCls[c] = (byCls[c] || 0) + 1;
    var k = c + '-' + n;
    byPair[k] = (byPair[k] || 0) + 1;
    if (cM >= 0 && !String(vals[r][cM]).trim()) { blankName++; }
    if (cT >= 0) {
      var t = vals[r][cT];
      if (t instanceof Date) {
        if (!first || t < first) { first = t; }
        if (!last || t > last) { last = t; }
      }
    }
  }
  out.push('데이터 ' + rows + '행 · 이름 공란 ' + blankName + '행');
  if (first) {
    out.push('시각 범위: ' + Utilities.formatDate(first, 'Asia/Seoul', 'MM/dd HH:mm')
             + ' ~ ' + Utilities.formatDate(last, 'Asia/Seoul', 'MM/dd HH:mm'));
  }

  function top(o, n) {
    return Object.keys(o).sort(function (a, b) { return o[b] - o[a]; }).slice(0, n)
      .map(function (k) { return (k === '-' ? '(빈칸)' : k) + ':' + o[k]; }).join(' · ');
  }
  out.push('');
  out.push('■ 반별: ' + top(byCls, 10));
  out.push('■ 반-번호 상위: ' + top(byPair, 8));
  var pairs = Object.keys(byPair).length;
  out.push('■ 서로 다른 반-번호 조합: ' + pairs + '개');
  if (rows > 0 && pairs <= 2) {
    out.push('🔴 조합이 ' + pairs + '개뿐 — 신원이 고정돼 들어오고 있다.');
  } else if (rows > 0) {
    out.push('✅ 신원은 분산돼 있다 — \'전부 한 명\'은 아니다.');
  }

  // ── 중복 제출 (2026-08-31 추가)
  // 왜: dumpFlagged 표본에서 같은 반·번호·시각·점수의 행이 나란히 두 번 찍혔다
  //     (사회 125/126행 · 역사 21/23행). 집계 기준이 '제출 버튼 도달'이라
  //     중복이 그대로 인원으로 세어지면 제출률이 부푼다.
  var dupPairs = 0, dupRows = 0, dupList = [];
  Object.keys(byPair).forEach(function (k) {
    if (byPair[k] > 1) { dupPairs++; dupRows += byPair[k] - 1; dupList.push(k + '×' + byPair[k]); }
  });
  out.push('');
  out.push('■ 중복 제출 — 같은 반-번호가 2행 이상: ' + dupPairs + '명 · 잉여 ' + dupRows + '행');
  if (dupPairs > 0) {
    out.push('  ' + dupList.sort().slice(0, 12).join(' · '));
    out.push('  ⚠️ 실제 제출 인원 = ' + pairs + '명 (행 수 ' + rows + '이 아님)');
    out.push('  ※ 재제출(고쳐서 다시 냄)일 수도, 버튼 두 번일 수도 있다.');
    out.push('     구분은 시각·점수가 같은지로 — 같으면 버튼 두 번, 다르면 재제출.');
  }
  _tg_(out.join('\n'));
}
