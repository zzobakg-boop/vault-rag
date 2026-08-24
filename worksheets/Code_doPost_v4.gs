/**
 * 학습지 제출 서버 v4 (2026-05-29)
 *
 * v3.2 → v4 변경: 제출을 *학습지별 탭*으로 분리
 *   - 기존: 모든 학습지가 '제출' 탭 1개에 섞임 → 2·3학년 여러 차시 같이 들어가면 확인 어려움
 *   - v4: 탭 이름 = data.worksheet(= 학습지 document.title) 정제본 → 학습지마다 개별 탭
 *   - 같은 학습지 안에서 학년/반은 '반' 컬럼으로 구분 (학생이 입력한 반 값)
 *   - act-N 동적 컬럼은 각 탭별로 유지 (학습지마다 활동 수 달라도 OK)
 *
 * v3.2 유지: data.type 없으면 'final' 취급(옛 학습지 호환)·'progress'만 skip
 *
 * ⚠️ 마이그레이션: 기존 '제출' 탭의 과거 데이터는 그대로 남음(건드리지 않음).
 *    v4 배포 후 *새 제출분*부터 학습지별 탭으로 들어감.
 */

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

    // v3.2: type 없으면 final (옛 학습지 호환) · progress만 skip
    var type = data.type || 'final';
    if (type === 'progress') {
      return ContentService.createTextOutput(JSON.stringify({ok: true, skipped: 'progress'}))
        .setMimeType(ContentService.MimeType.JSON);
    }

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
  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({ok: false, error: err.toString()}))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

function doGet(e) {
  return ContentService.createTextOutput(JSON.stringify({ok: true, msg: '학습지 제출 서버 v4 정상 (학습지별 탭)'}))
    .setMimeType(ContentService.MimeType.JSON);
}
