/**
 * 학습지 제출 서버 v5 (2026-10-20) — 🪦 배포 안 함(10/20 천대현이 gcloud Sheets 읽기 권한 쪽을 골랐다. ~/scripts/fetch_submissions.py)
 *
 * v4 → v5 변경: 교사용 «내보내기» 갈래 하나만 더한다. 학생 제출 경로는 v4와 한 줄도 다르지 않다.
 *   - 왜: 제출 답을 맥미니로 가져오는 길이 «천대현이 탭을 손으로 내보내기»뿐이었다.
 *     드라이브 커넥터는 앞 몇 명에서 잘리고, 로컬 gcloud에는 Sheets 권한이 없다(10/20 개인별 피드백 시험).
 *   - POST {action:'export', token, list:true}      → 탭 이름·행 수 목록
 *   - POST {action:'export', token, tab:'<탭 이름>'} → 그 탭의 모든 행(첫 행 = 헤더)
 *   - token은 코드에 적지 않는다. 스크립트 속성 EXPORT_TOKEN과 맥미니 키체인(worksheet-export)에만 둔다.
 *     속성이 비어 있으면 내보내기는 항상 거절된다. URL 쿼리가 아니라 POST 본문으로 받는다.
 *   - 학생 제출에는 action 필드가 없으므로 이 갈래에 들어오지 않는다.
 */

function exportTab_(data) {
  var want = PropertiesService.getScriptProperties().getProperty('EXPORT_TOKEN');
  if (!want || !data.token || data.token !== want) {
    return ContentService.createTextOutput(JSON.stringify({ok: false, error: 'denied'}))
      .setMimeType(ContentService.MimeType.JSON);
  }
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  if (data.list) {
    var tabs = ss.getSheets().map(function (s) { return {name: s.getName(), rows: s.getLastRow()}; });
    return ContentService.createTextOutput(JSON.stringify({ok: true, tabs: tabs}))
      .setMimeType(ContentService.MimeType.JSON);
  }
  var tab = ss.getSheetByName(String(data.tab || ''));
  if (!tab) {
    return ContentService.createTextOutput(JSON.stringify({ok: false, error: 'no such tab'}))
      .setMimeType(ContentService.MimeType.JSON);
  }
  var rows = tab.getDataRange().getValues().map(function (r) {
    return r.map(function (v) { return (v instanceof Date) ? v.toISOString() : v; });
  });
  return ContentService.createTextOutput(JSON.stringify({ok: true, tab: tab.getName(), rows: rows}))
    .setMimeType(ContentService.MimeType.JSON);
}

function sanitizeTabName_(name) {
  // Google Sheet 탭 이름 제약: [ ] : \ / ? * 금지 · 100자 이하 · 빈값 불가
  var t = String(name || '제출').replace(/[\[\]:\\\/?*]/g, ' ').replace(/\s+/g, ' ').trim();
  if (!t) t = '제출';
  if (t.length > 80) t = t.slice(0, 80);   // 여유 두고 80자 cap
  return t;
}

function doPost(e) {
  try {
    var data = JSON.parse(e.postData.contents);

    // v5: 교사용 내보내기 — 학생 제출에는 action이 없다
    if (data.action === 'export') return exportTab_(data);

    // v3.2: type 없으면 final (옛 학습지 호환) · progress만 skip
    var type = data.type || 'final';
    if (type === 'progress') {
      return ContentService.createTextOutput(JSON.stringify({ok: true, skipped: 'progress'}))
        .setMimeType(ContentService.MimeType.JSON);
    }

    // ⚠️ 2026-08-25 근본 픽스: 동시 제출 경쟁 상태(race) 방어.
    // 잠금이 없으면 두 학생이 거의 동시에 제출할 때 둘 다 '탭 없음'을 보고,
    // 뒤 요청이 앞 요청이 만든 탭을 발견해 헤더 생성을 건너뛴다 →
    // 헤더 없는 탭에 데이터만 쌓인다(사회② 5-2 8/21 · 역사① 3-2-5 동일 증상).
    // 5-1이 멀쩡했던 것은 코드가 달라서가 아니라 제출이 몰리지 않았기 때문이다.
    var lock = LockService.getScriptLock();
    try {
      lock.waitLock(20000);
    } catch (lockErr) {
      return ContentService.createTextOutput(JSON.stringify({ok: false, error: 'busy'}))
        .setMimeType(ContentService.MimeType.JSON);
    }

    try {

    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var ws = data.worksheet || '제출';
    var tabName = sanitizeTabName_(ws);            // ⭐ v4: 학습지별 탭
    var tab = ss.getSheetByName(tabName);
    if (!tab) {
      tab = ss.insertSheet(tabName);
      tab.appendRow(['시각', '학습지', '반', '번호', '이름', '빈칸', 'OX', '총점', '답(JSON)']);
    } else if (tab.getLastRow() === 0 || String(tab.getRange(1, 1).getValue()) !== '시각') {
      // ⚠️ 2026-08-24 버그 픽스: 탭이 '이미 존재'하지만 헤더가 없는 경우
      // (예: 빈 탭이 사전에 만들어져 있던 경우) — 예전엔 header 생성 자체를 건너뛰어
      // act-N 동적 컬럼이 헤더 없는 시트의 2번째 열부터 붙으면서 헤더-데이터가
      // 완전히 어긋났다(역사① 3-2-5 사고). 헤더가 없거나 첫 칸이 '시각'이 아니면
      // 무조건 맨 위에 표준 헤더 행을 삽입한다.
      tab.insertRowBefore(1);
      tab.getRange(1, 1, 1, 9).setValues([['시각', '학습지', '반', '번호', '이름', '빈칸', 'OX', '총점', '답(JSON)']]);
    }

    var ts = new Date();
    var cls = String(data.studentClass || '');
    var num = String(data.studentNumber || '');
    var answers = data.answers || {};
    var answersJson = JSON.stringify(answers);

    // act-N 키 추출·번호 순 정렬
    var actEntries = Object.keys(answers)
      .filter(function (k) { return k.indexOf('act-') === 0; })
      .sort(function (a, b) { return parseInt(a.split('-')[1]) - parseInt(b.split('-')[1]); });

    // header 읽기 + 새 act-N 컬럼을 *답(JSON) 뒤*에 동적 추가 (탭별)
    var headers = tab.getRange(1, 1, 1, tab.getLastColumn()).getValues()[0];
    actEntries.forEach(function (k) {
      if (headers.indexOf(k) === -1) {
        tab.getRange(1, headers.length + 1).setValue(k);
        headers.push(k);
      }
    });

    // row: 9 기본 컬럼 + headers[9..]의 act-N 값
    var baseRow = [ts, ws, cls, num, data.studentName || '',
                   data.blankScore, data.oxScore, data.totalScore, answersJson];
    var actRow = headers.slice(9).map(function (h) { return answers[h] || ''; });
    tab.appendRow(baseRow.concat(actRow));

    return ContentService.createTextOutput(JSON.stringify({ok: true, tab: tabName}))
      .setMimeType(ContentService.MimeType.JSON);
    } finally {
      lock.releaseLock();
    }

  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({ok: false, error: err.toString()}))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

function doGet(e) {
  return ContentService.createTextOutput(JSON.stringify({ok: true, msg: '학습지 제출 서버 v5 정상 (학습지별 탭·내보내기)'}))
    .setMimeType(ContentService.MimeType.JSON);
}
