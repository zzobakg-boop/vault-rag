/**
 * 학습지 제출 서버 v3 (2026-05-27)
 *
 * v2 → v3 변경:
 *   - progress 분기 제거 — *제출* 시점만 처리 (제출 학생만 누적)
 *   - *활동* 탭 제거 — *제출* 탭 1개에 act-N 컬럼 동적 추가로 통합
 *   - 단일 view: 시각·학습지·반·번호·이름·빈칸·OX·총점·답(JSON)·act-1·act-2·…
 *
 * 사용자 의도: "제출 버튼 누른 학생들 결과만 들어오도록·활동 답도 한눈에"
 */
function doPost(e) {
  try {
    const data = JSON.parse(e.postData.contents);

    // 5/27 v3: progress 비활성 — 학생이 *제출* 클릭한 경우만 누적
    if (data.type !== 'final') {
      return ContentService.createTextOutput(JSON.stringify({ok: true, skipped: 'non-final'}))
        .setMimeType(ContentService.MimeType.JSON);
    }

    const ss = SpreadsheetApp.getActiveSpreadsheet();
    let tab = ss.getSheetByName('제출');
    if (!tab) {
      tab = ss.insertSheet('제출');
      tab.appendRow(['시각', '학습지', '반', '번호', '이름', '빈칸', 'OX', '총점', '답(JSON)']);
    }

    const ts = new Date();
    const ws = data.worksheet || '';
    const cls = String(data.studentClass || '');
    const num = String(data.studentNumber || '');
    const answers = data.answers || {};
    const answersJson = JSON.stringify(answers);

    // act-N 키 추출·번호 순 정렬
    const actEntries = Object.keys(answers)
      .filter(k => k.indexOf('act-') === 0)
      .sort((a, b) => parseInt(a.split('-')[1]) - parseInt(b.split('-')[1]));

    // header 읽기 + 새 act-N 컬럼을 *답(JSON) 뒤*에 동적 추가
    let headers = tab.getRange(1, 1, 1, tab.getLastColumn()).getValues()[0];
    actEntries.forEach(k => {
      if (headers.indexOf(k) === -1) {
        tab.getRange(1, headers.length + 1).setValue(k);
        headers.push(k);
      }
    });

    // row 구성: 9 기본 컬럼 + headers[9..]의 act-N 값
    const baseRow = [ts, ws, cls, num, data.studentName || '',
                     data.blankScore, data.oxScore, data.totalScore, answersJson];
    const actRow = headers.slice(9).map(h => answers[h] || '');
    const fullRow = baseRow.concat(actRow);

    tab.appendRow(fullRow);

    return ContentService.createTextOutput(JSON.stringify({ok: true}))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({ok: false, error: err.toString()}))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

function doGet(e) {
  return ContentService.createTextOutput(JSON.stringify({ok: true, msg: '학습지 제출 서버 v3 정상'}))
    .setMimeType(ContentService.MimeType.JSON);
}
