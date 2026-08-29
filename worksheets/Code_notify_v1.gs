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

var WINDOW_MIN = 40;      // 되돌아볼 분
var NUM_MAX = 40;         // 정상 번호 상한 (이보다 크면 이상 신호)
var HDR = ['시각', '학습지', '반', '번호', '이름', '빈칸', 'OX', '총점', '답(JSON)'];

function _prop_(k) { return PropertiesService.getScriptProperties().getProperty(k); }

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

  var head = vals[0].map(function (v) { return String(v).trim(); });

  // ⚠️ 2026-08-29 오탐 수정 — 이 시트에는 제출 탭 말고도 교사가 손으로 만든
  //   정리 시트(「📋 정리·…」 등)가 섞여 있다. 예전엔 그것들까지 전부
  //   "헤더 없음"으로 경보해 20줄짜리 알림이 왔고, 진짜 신호가 그 속에 묻혔다.
  //   → 헤더가 없으면 기본은 *조용히 건너뛴다*. 단 A열이 '최근 날짜'로 읽히면
  //     그건 제출 탭인데 헤더만 날아간 것이므로 그때만 경보한다(8/21 사고 대비).
  if (head[0] !== '시각') {
    for (var j = 0; j < vals.length; j++) {
      if (_recentDate_(vals[j][0], since)) {
        out.issues.push('헤더 없음 — 제출이 들어오는데 열이 어긋난 채로 쌓이는 중');
        break;
      }
    }
    return out;
  }

  var ix = {};
  HDR.forEach(function (h) { ix[h] = head.indexOf(h); });

  var seen = {};
  for (var i = 1; i < vals.length; i++) {
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

    var essayBlank = true;
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
function _roster_() {
  var tab = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(ROSTER_TAB);
  if (!tab) { return null; }
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
  return { map: map, bad: bad };
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
  var ss = SpreadsheetApp.getActiveSpreadsheet();
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
      _tg_('✅ 알림 정상 작동 (' + stamp + ')\n\n'
        + '탭 ' + scanned + '개를 훑었고, 최근 ' + Math.round(WINDOW_MIN / 60) + '시간 안에 들어온 제출은 '
        + totalRows + '건입니다.\n'
        + '이상 신호도 없습니다.\n'
        + '「명렬」 탭: ' + (roster ? Object.keys(roster).length + '개 반 인식' : '없음(미제출 계산 안 함)') + '\n\n'
        + '→ 제출이 없어서 조용한 것이지 고장이 아닙니다.');
    }
    return;
  }

  var head = (anyIssue ? '🔴 학습지 제출 — 확인 필요' : '✅ 학습지 제출')
    + ' (' + stamp + ' 기준 ' + WINDOW_MIN + '분)';
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
